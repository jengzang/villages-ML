"""Audit the raw Guangdong natural village table.

This script performs a full-table, row-level audit of ``广东省自然村`` without
modifying the database. It writes reproducible CSV/Markdown artifacts under
``results/raw_village_audit``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DB_PATH = Path("data/villages.db")
RAW_TABLE = "广东省自然村"
OUTPUT_DIR = Path("results/raw_village_audit")

CITY_COL = "市级"
COUNTY_COL = "区县级"
TOWNSHIP_COL = "乡镇级"
ADMIN_COL = "行政村"
NAME_COL = "自然村"
PINYIN_COL = "拼音"
LANG_COL = "方言分布"
LON_COL = "longitude"
LAT_COL = "latitude"

CHINESE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002EBEF]")
NON_CHINESE_RE = re.compile(r"[^\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002EBEF\s]")

STRONG_FACILITY_TERMS = [
    "学校", "小学", "中学", "大学", "学院", "幼儿园", "卫生院", "卫生站", "医院", "诊所",
    "派出所", "公安", "政府", "镇府", "村委", "居委", "委员会", "办公室",
    "电站", "变电站", "泵站", "收费站", "车站", "机场",
    "市场", "商场", "超市", "广场", "公园", "景区", "旅游区", "工业园", "开发区",
    "种养场", "养殖场", "采石场", "砖厂", "电厂", "工厂", "公司", "企业", "基地", "园区",
    "教堂", "陵园", "烈士", "纪念",
]

WEAK_OBJECT_TERMS = [
    "水库", "码头", "港口", "林场", "农场", "牧场", "渔场", "茶场", "果场", "盐场",
    "矿场", "寺", "庙", "祠", "墓",
]

ADMIN_TERMS = [
    "社区", "居委", "居委会", "村委", "村委会", "委员会", "管区", "管理区",
    "街道", "办事处", "镇", "乡",
]

STRONG_ROAD_INFRA_TERMS = [
    "大道", "公路", "高速", "铁路", "隧道", "路口", "路段",
]

WEAK_ROAD_INFRA_TERMS = [
    "桥", "大桥",
]

VILLAGE_FORMANTS = [
    "村", "庄", "寨", "围", "屋", "厝", "寮", "坑", "岭", "岗", "墩", "角",
    "塘", "田", "垌", "洞", "塱", "朗", "陂", "坝", "埠", "洲", "湾", "滩",
    "圩", "坊", "巷", "里", "社", "楼", "园", "径", "坪", "坳", "排", "片",
    "围仔", "新村", "老村", "上村", "下村",
]

GENERIC_SINGLETONS = set("上下东南西北中前后新老大小内外")


@dataclass(frozen=True)
class AuditRow:
    rowid: int
    city: str
    county: str
    township: str
    admin: str
    name: str
    pinyin: str
    language: str
    lon: str
    lat: str


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def chinese_only(text: str) -> str:
    return "".join(CHINESE_RE.findall(text))


def coord_key(lon: str, lat: str, precision: int = 6) -> tuple[str, str]:
    try:
        lon_f = round(float(lon), precision)
        lat_f = round(float(lat), precision)
    except (TypeError, ValueError):
        return clean(lon), clean(lat)
    return f"{lon_f:.{precision}f}", f"{lat_f:.{precision}f}"


def in_guangdong_bounds(lon: str, lat: str) -> bool | None:
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except (TypeError, ValueError):
        return None
    return 109.0 <= lon_f <= 118.0 and 20.0 <= lat_f <= 26.5


def classify_name(name: str, admin: str) -> tuple[str, list[str], str]:
    """Return risk level, rule codes, and normalized Chinese name."""
    rules: list[str] = []
    norm = chinese_only(name)

    if not name:
        rules.append("empty_name")
    if not norm:
        rules.append("no_chinese_name")
    if NON_CHINESE_RE.search(name):
        rules.append("contains_non_chinese_symbol")
    if len(norm) == 1:
        rules.append("single_chinese_char")
        if norm in GENERIC_SINGLETONS:
            rules.append("generic_direction_or_size_singleton")

    if admin and norm and norm == chinese_only(admin):
        rules.append("same_as_administrative_village")

    strong_facility_hits = [term for term in STRONG_FACILITY_TERMS if term in norm]
    weak_object_hits = [term for term in WEAK_OBJECT_TERMS if term in norm]
    admin_hits = [term for term in ADMIN_TERMS if term in norm]
    strong_road_hits = [term for term in STRONG_ROAD_INFRA_TERMS if term in norm]
    weak_road_hits = [term for term in WEAK_ROAD_INFRA_TERMS if term in norm]

    if strong_facility_hits:
        rules.extend(f"strong_facility_term:{term}" for term in strong_facility_hits[:3])
    if weak_object_hits:
        rules.extend(f"weak_object_term:{term}" for term in weak_object_hits[:3])
    if admin_hits:
        rules.extend(f"administrative_term:{term}" for term in admin_hits[:3])
    if strong_road_hits:
        rules.extend(f"strong_infrastructure_term:{term}" for term in strong_road_hits[:3])
    if weak_road_hits:
        rules.extend(f"weak_infrastructure_term:{term}" for term in weak_road_hits[:3])

    if norm and not any(formant in norm for formant in VILLAGE_FORMANTS):
        rules.append("no_common_village_formant")

    strong_non_village = (
        "empty_name",
        "no_chinese_name",
        "same_as_administrative_village",
    )
    if any(rule in rules for rule in strong_non_village) or strong_facility_hits or strong_road_hits:
        risk = "high"
    elif (
        len(norm) == 1
        or admin_hits
        or weak_object_hits
        or weak_road_hits
        or "no_common_village_formant" in rules
    ):
        risk = "medium"
    else:
        risk = "low"

    return risk, rules, norm


def iter_rows(conn: sqlite3.Connection) -> Iterable[AuditRow]:
    cur = conn.execute(
        f"""
        SELECT rowid, "{CITY_COL}", "{COUNTY_COL}", "{TOWNSHIP_COL}", "{ADMIN_COL}",
               "{NAME_COL}", "{PINYIN_COL}", "{LANG_COL}", "{LON_COL}", "{LAT_COL}"
        FROM "{RAW_TABLE}"
        ORDER BY rowid
        """
    )
    for row in cur:
        yield AuditRow(
            rowid=row[0],
            city=clean(row[1]),
            county=clean(row[2]),
            township=clean(row[3]),
            admin=clean(row[4]),
            name=clean(row[5]),
            pinyin=clean(row[6]),
            language=clean(row[7]),
            lon=clean(row[8]),
            lat=clean(row[9]),
        )


def write_duplicate_groups(
    path: Path,
    title: str,
    groups: dict[tuple[str, ...], list[int]],
    sample_limit: int,
) -> tuple[int, int, int]:
    duplicate_groups = [(key, ids) for key, ids in groups.items() if len(ids) > 1]
    duplicate_groups.sort(key=lambda item: (-len(item[1]), item[0]))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([title, "duplicate_count", "row_count", "rowids_sample"])
        for key, ids in duplicate_groups:
            writer.writerow([" | ".join(key), len(ids) - 1, len(ids), " ".join(map(str, ids[:sample_limit]))])
    rows_in_groups = sum(len(ids) for _, ids in duplicate_groups)
    extra_rows = sum(len(ids) - 1 for _, ids in duplicate_groups)
    return len(duplicate_groups), rows_in_groups, extra_rows


def audit(db_path: Path, output_dir: Path, sample_limit: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    total = conn.execute(f'SELECT COUNT(*) FROM "{RAW_TABLE}"').fetchone()[0]
    schema = conn.execute(f'PRAGMA table_info("{RAW_TABLE}")').fetchall()

    risk_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    city_counts: Counter[str] = Counter()
    high_by_city: Counter[str] = Counter()
    medium_by_city: Counter[str] = Counter()
    coord_status: Counter[str] = Counter()

    exact_key_groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    full_location_groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    coord_groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    name_coord_groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    name_groups: dict[tuple[str, ...], list[int]] = defaultdict(list)

    row_path = output_dir / "row_level_audit.csv"
    with row_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rowid", "市级", "区县级", "乡镇级", "行政村", "自然村",
            "normalized_chinese_name", "longitude", "latitude", "coord_status",
            "risk_level", "rule_codes",
        ])

        for row in iter_rows(conn):
            risk, rules, norm = classify_name(row.name, row.admin)
            risk_counts[risk] += 1
            rule_counts.update(rules)
            city_counts[row.city] += 1
            if risk == "high":
                high_by_city[row.city] += 1
            elif risk == "medium":
                medium_by_city[row.city] += 1

            bounds = in_guangdong_bounds(row.lon, row.lat)
            if bounds is True:
                cstatus = "valid_guangdong_bounds"
            elif bounds is False:
                cstatus = "outside_guangdong_bounds"
            else:
                cstatus = "missing_or_invalid_coord"
            coord_status[cstatus] += 1

            ck = coord_key(row.lon, row.lat)
            exact_key_groups[(row.city, row.county, row.township, row.admin, row.name, ck[0], ck[1])].append(row.rowid)
            full_location_groups[(row.city, row.county, row.township, row.admin, row.name)].append(row.rowid)
            if ck != ("", ""):
                coord_groups[(ck[0], ck[1])].append(row.rowid)
                name_coord_groups[(norm, ck[0], ck[1])].append(row.rowid)
            name_groups[(norm,)].append(row.rowid)

            writer.writerow([
                row.rowid, row.city, row.county, row.township, row.admin, row.name,
                norm, row.lon, row.lat, cstatus, risk, ";".join(rules),
            ])

    duplicates = {}
    duplicates["exact_admin_name_coord"] = write_duplicate_groups(
        output_dir / "duplicates_exact_admin_name_coord.csv",
        "市|区县|乡镇|行政村|自然村|lon|lat",
        exact_key_groups,
        sample_limit,
    )
    duplicates["same_admin_name"] = write_duplicate_groups(
        output_dir / "duplicates_same_admin_name.csv",
        "市|区县|乡镇|行政村|自然村",
        full_location_groups,
        sample_limit,
    )
    duplicates["same_coordinate"] = write_duplicate_groups(
        output_dir / "duplicates_same_coordinate.csv",
        "lon|lat",
        coord_groups,
        sample_limit,
    )
    duplicates["same_name_coordinate"] = write_duplicate_groups(
        output_dir / "duplicates_same_name_coordinate.csv",
        "normalized_name|lon|lat",
        name_coord_groups,
        sample_limit,
    )
    duplicates["same_normalized_name"] = write_duplicate_groups(
        output_dir / "duplicates_same_normalized_name.csv",
        "normalized_name",
        name_groups,
        sample_limit,
    )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "database": str(db_path),
        "table": RAW_TABLE,
        "total_rows": total,
        "schema": [{"cid": s[0], "name": s[1], "type": s[2]} for s in schema],
        "risk_counts": dict(risk_counts),
        "rule_counts": dict(rule_counts.most_common()),
        "coord_status": dict(coord_status),
        "duplicate_metrics": {
            key: {
                "duplicate_groups": value[0],
                "rows_in_duplicate_groups": value[1],
                "extra_duplicate_rows": value[2],
            }
            for key, value in duplicates.items()
        },
        "city_counts": dict(city_counts),
        "high_risk_by_city": dict(high_by_city),
        "medium_risk_by_city": dict(medium_by_city),
    }

    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_markdown_summary(output_dir / "SUMMARY.md", summary)


def pct(value: int, total: int) -> str:
    return f"{value / total * 100:.2f}%" if total else "0.00%"


def write_markdown_summary(path: Path, summary: dict) -> None:
    total = summary["total_rows"]
    risk_counts = summary["risk_counts"]
    duplicate_metrics = summary["duplicate_metrics"]

    lines = [
        "# Raw Village Table Audit",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Database: `{summary['database']}`",
        f"- Table: `{summary['table']}`",
        f"- Total rows audited: **{total:,}**",
        "",
        "## Actual Raw Schema",
        "",
        "| cid | column | type |",
        "|---:|---|---|",
    ]
    for col in summary["schema"]:
        lines.append(f"| {col['cid']} | {col['name']} | {col['type']} |")

    lines.extend([
        "",
        "## Row-Level Name Risk",
        "",
        "| risk | rows | percent |",
        "|---|---:|---:|",
    ])
    for risk in ["high", "medium", "low"]:
        count = risk_counts.get(risk, 0)
        lines.append(f"| {risk} | {count:,} | {pct(count, total)} |")

    lines.extend([
        "",
        "High risk means strong evidence of non-natural-village content, including empty/non-Chinese names, exact administrative-village names, facility/institution terms, or road/infrastructure terms. Medium risk means the name needs review, such as one-character generic names, administrative terms, or no common village-name formant.",
        "",
        "## Coordinate Status",
        "",
        "| status | rows | percent |",
        "|---|---:|---:|",
    ])
    for status, count in summary["coord_status"].items():
        lines.append(f"| {status} | {count:,} | {pct(count, total)} |")

    lines.extend([
        "",
        "## Duplicate Metrics",
        "",
        "| duplicate definition | groups | rows in groups | extra rows |",
        "|---|---:|---:|---:|",
    ])
    labels = {
        "exact_admin_name_coord": "same city/county/township/admin/name/coordinate",
        "same_admin_name": "same city/county/township/admin/name",
        "same_coordinate": "same coordinate",
        "same_name_coordinate": "same normalized name + coordinate",
        "same_normalized_name": "same normalized name",
    }
    for key, label in labels.items():
        data = duplicate_metrics[key]
        lines.append(
            f"| {label} | {data['duplicate_groups']:,} | "
            f"{data['rows_in_duplicate_groups']:,} | {data['extra_duplicate_rows']:,} |"
        )

    lines.extend([
        "",
        "## Top Rule Hits",
        "",
        "| rule | rows |",
        "|---|---:|",
    ])
    for rule, count in list(summary["rule_counts"].items())[:40]:
        lines.append(f"| `{rule}` | {count:,} |")

    lines.extend([
        "",
        "## Output Files",
        "",
        "- `row_level_audit.csv`: every raw row with risk level and rule codes.",
        "- `duplicates_exact_admin_name_coord.csv`: strongest duplicate candidates.",
        "- `duplicates_same_admin_name.csv`: repeated names in the same admin hierarchy.",
        "- `duplicates_same_coordinate.csv`: multiple rows sharing the same coordinate.",
        "- `duplicates_same_name_coordinate.csv`: same normalized name at the same coordinate.",
        "- `duplicates_same_normalized_name.csv`: repeated normalized names anywhere in the province.",
        "- `summary.json`: machine-readable metrics for follow-up cleaning.",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--sample-limit", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit(args.db, args.output_dir, args.sample_limit)
    print(f"Audit complete: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
