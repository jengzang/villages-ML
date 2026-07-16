"""Find near-duplicate village names inside the same administrative village.

The audit is exhaustive at the pair level within each
``市级 + 区县级 + 乡镇级 + 行政村`` group. It does not modify the database.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DB_PATH = Path("data/villages.db")
RAW_TABLE = "广东省自然村"
OUTPUT_DIR = Path("results/intra_admin_near_duplicates")

CHINESE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002EBEF]")
PARENS_RE = re.compile(r"[（(].*?[）)]")

ADMIN_SUFFIXES = [
    "村民委员会", "居民委员会", "村委会", "居委会", "委员会",
    "社区", "管区", "管理区", "行政村", "自然村", "村", "寨", "片", "区",
]
TRAILING_NUMERAL_RE = re.compile(r"^(.+?)([一二三四五六七八九十]+村?|[0-9]+)$")


@dataclass(frozen=True)
class VillageRow:
    rowid: int
    city: str
    county: str
    township: str
    admin: str
    name: str
    pinyin: str
    lon: str
    lat: str
    norm: str
    admin_base: str
    prefix_removed: str
    numbered_base: str
    numbered_changed: bool
    pinyin_key: str
    prefix_pinyin_key: str
    lon_f: float | None
    lat_f: float | None


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def chinese_only(value: str) -> str:
    return "".join(CHINESE_RE.findall(PARENS_RE.sub("", value)))


def strip_admin_suffixes(value: str) -> str:
    result = value
    changed = True
    while changed:
        changed = False
        for suffix in ADMIN_SUFFIXES:
            if result.endswith(suffix) and len(result) > len(suffix):
                result = result[: -len(suffix)]
                changed = True
                break
    return result


def remove_admin_prefix(name: str, admin: str, min_remaining_chars: int = 2) -> str:
    if not name:
        return ""

    candidates = []
    admin_norm = chinese_only(admin)
    admin_base = strip_admin_suffixes(admin_norm)
    if name == admin_norm:
        return name
    if admin_norm:
        candidates.append(admin_norm)
    if admin_base and admin_base != admin_norm:
        candidates.append(admin_base)

    for prefix in sorted(set(candidates), key=len, reverse=True):
        remaining = name[len(prefix) :] if name.startswith(prefix) else ""
        if len(prefix) >= 2 and len(remaining) >= min_remaining_chars:
            return remaining
    return name


def normalize_numbered(value: str) -> tuple[str, bool]:
    match = TRAILING_NUMERAL_RE.match(value)
    if match and len(match.group(1)) >= 1:
        return match.group(1), True
    return value, False


def pinyin_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", without_marks)


def to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def edit_distance(a: str, b: str, max_distance: int | None = None) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if max_distance is not None and abs(len(a) - len(b)) > max_distance:
        return max_distance + 1

    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            current.append(value)
            row_min = min(row_min, value)
        if max_distance is not None and row_min > max_distance:
            return max_distance + 1
        previous = current
    return previous[-1]


def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 1 - edit_distance(a, b) / max(len(a), len(b))


def shared_char_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ca = Counter(a)
    cb = Counter(b)
    shared = sum((ca & cb).values())
    return shared / max(len(a), len(b))


def pair_rules(a: VillageRow, b: VillageRow) -> tuple[list[str], float | None, float, float]:
    rules: list[str] = []

    if a.norm and a.norm == b.norm:
        rules.append("exact_normalized_name")
    if a.prefix_removed and a.prefix_removed == b.prefix_removed and a.prefix_removed != a.norm:
        rules.append("same_after_admin_prefix_removed")
    if a.numbered_base and a.numbered_base == b.numbered_base and (a.numbered_changed or b.numbered_changed):
        rules.append("same_after_trailing_number_removed")

    name_sim = similarity(a.norm, b.norm)
    shared_ratio = shared_char_ratio(a.norm, b.norm)
    if min(len(a.norm), len(b.norm)) >= 2 and edit_distance(a.norm, b.norm, 1) <= 1:
        rules.append("chinese_edit_distance_le_1")
    elif min(len(a.norm), len(b.norm)) >= 4 and edit_distance(a.norm, b.norm, 2) <= 2:
        rules.append("chinese_edit_distance_le_2")
    elif min(len(a.norm), len(b.norm)) >= 3 and shared_ratio >= 0.80:
        rules.append("high_shared_chinese_chars")

    if a.pinyin_key and b.pinyin_key and a.pinyin_key == b.pinyin_key and a.norm != b.norm:
        rules.append("same_pinyin_different_chars")
    if (
        a.prefix_pinyin_key
        and b.prefix_pinyin_key
        and a.prefix_pinyin_key == b.prefix_pinyin_key
        and a.prefix_removed != b.prefix_removed
    ):
        rules.append("same_prefix_removed_pinyin")
    if (
        a.pinyin_key
        and b.pinyin_key
        and a.pinyin_key != b.pinyin_key
        and min(len(a.pinyin_key), len(b.pinyin_key)) >= 4
        and edit_distance(a.pinyin_key, b.pinyin_key, 2) <= 2
    ):
        rules.append("pinyin_edit_distance_le_2")

    distance_m = None
    if None not in (a.lon_f, a.lat_f, b.lon_f, b.lat_f):
        distance_m = haversine_m(a.lon_f, a.lat_f, b.lon_f, b.lat_f)  # type: ignore[arg-type]
        if distance_m == 0:
            rules.append("same_coordinate")
        elif distance_m <= 20:
            rules.append("coordinate_within_20m")
        elif distance_m <= 50 and (
            "exact_normalized_name" in rules
            or "same_after_admin_prefix_removed" in rules
            or "same_pinyin_different_chars" in rules
            or "chinese_edit_distance_le_1" in rules
        ):
            rules.append("coordinate_within_50m_with_name_similarity")

    return rules, distance_m, name_sim, shared_ratio


def merge_review_severity(rules: list[str], distance_m: float | None) -> str:
    """Classify pairs that are plausible merge-review candidates.

    Wide fuzzy rules such as edit distance are useful for exploration, but by
    themselves they over-match normal village pairs like 龙屋基/黄屋基.
    """
    if "exact_normalized_name" in rules:
        return "high"
    if "same_after_admin_prefix_removed" in rules:
        return "high"
    if "same_after_trailing_number_removed" in rules:
        return "medium"
    if "same_coordinate" in rules:
        return "high"
    if "same_pinyin_different_chars" in rules and (
        "chinese_edit_distance_le_1" in rules
        or "same_prefix_removed_pinyin" in rules
        or (distance_m is not None and distance_m <= 100)
    ):
        return "high"
    if "coordinate_within_20m" in rules and (
        "same_pinyin_different_chars" in rules
        or "same_after_admin_prefix_removed" in rules
        or "exact_normalized_name" in rules
    ):
        return "high"
    if "coordinate_within_50m_with_name_similarity" in rules and (
        "same_pinyin_different_chars" in rules
        or "same_after_admin_prefix_removed" in rules
        or "exact_normalized_name" in rules
    ):
        return "medium"
    return "none"


def fuzzy_signal_severity(rules: list[str], distance_m: float | None) -> str:
    strong_rules = {
        "exact_normalized_name",
        "same_after_admin_prefix_removed",
        "same_after_trailing_number_removed",
        "same_pinyin_different_chars",
        "same_coordinate",
    }
    if any(rule in strong_rules for rule in rules):
        return "high"
    if "coordinate_within_20m" in rules and (
        "chinese_edit_distance_le_1" in rules
        or "pinyin_edit_distance_le_2" in rules
        or "high_shared_chinese_chars" in rules
    ):
        return "high"
    if rules:
        return "medium"
    return "none"


def load_groups(conn: sqlite3.Connection) -> dict[tuple[str, str, str, str], list[VillageRow]]:
    groups: dict[tuple[str, str, str, str], list[VillageRow]] = defaultdict(list)
    rows = conn.execute(
        f"""
        SELECT rowid, 市级, 区县级, 乡镇级, 行政村, 自然村, 拼音, longitude, latitude
        FROM "{RAW_TABLE}"
        ORDER BY 市级, 区县级, 乡镇级, 行政村, rowid
        """
    )
    for row in rows:
        rowid, city, county, township, admin, name, pinyin, lon, lat = map(clean, row)
        rowid_int = int(rowid)
        norm = chinese_only(name)
        admin_base = strip_admin_suffixes(chinese_only(admin))
        prefix_removed = remove_admin_prefix(norm, admin)
        numbered_base, numbered_changed = normalize_numbered(prefix_removed)
        groups[(city, county, township, admin)].append(
            VillageRow(
                rowid=rowid_int,
                city=city,
                county=county,
                township=township,
                admin=admin,
                name=name,
                pinyin=pinyin,
                lon=lon,
                lat=lat,
                norm=norm,
                admin_base=admin_base,
                prefix_removed=prefix_removed,
                numbered_base=numbered_base,
                numbered_changed=numbered_changed,
                pinyin_key=pinyin_key(pinyin),
                prefix_pinyin_key="",
                lon_f=to_float(lon),
                lat_f=to_float(lat),
            )
        )

    # Use database pinyin for raw names, but compare prefix-removed pinyin by
    # stripping the pinyin prefix when the Chinese prefix was stripped.
    rebuilt: dict[tuple[str, str, str, str], list[VillageRow]] = defaultdict(list)
    for key, items in groups.items():
        for item in items:
            prefix_key = item.pinyin_key
            if item.prefix_removed != item.norm and item.norm.endswith(item.prefix_removed):
                removed_len = len(item.norm) - len(item.prefix_removed)
                ratio = removed_len / len(item.norm) if item.norm else 0
                cut = round(len(item.pinyin_key) * ratio)
                prefix_key = item.pinyin_key[cut:]
            rebuilt[key].append(
                VillageRow(
                    **{**item.__dict__, "prefix_pinyin_key": prefix_key}
                )
            )
    return rebuilt


def audit(db_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    groups = load_groups(conn)

    pair_path = output_dir / "merge_review_pairs.csv"
    fuzzy_path = output_dir / "fuzzy_signals.csv"
    row_path = output_dir / "row_candidate_coverage.csv"
    summary_path = output_dir / "SUMMARY.md"

    total_rows = 0
    total_groups = len(groups)
    comparable_pairs = 0
    candidate_pairs = 0
    fuzzy_pairs = 0
    severity_counts: Counter[str] = Counter()
    fuzzy_severity_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    fuzzy_rule_counts: Counter[str] = Counter()
    row_hits: dict[int, dict[str, object]] = {}
    group_hit_counts: Counter[tuple[str, str, str, str]] = Counter()

    pair_header = [
            "severity", "rules", "distance_m", "name_similarity", "shared_char_ratio",
            "市级", "区县级", "乡镇级", "行政村",
            "rowid_a", "自然村_a", "prefix_removed_a", "拼音_a", "lon_a", "lat_a",
            "rowid_b", "自然村_b", "prefix_removed_b", "拼音_b", "lon_b", "lat_b",
    ]

    with pair_path.open("w", encoding="utf-8", newline="") as pair_f, fuzzy_path.open(
        "w", encoding="utf-8", newline=""
    ) as fuzzy_f:
        writer = csv.writer(pair_f)
        fuzzy_writer = csv.writer(fuzzy_f)
        writer.writerow(pair_header)
        fuzzy_writer.writerow(pair_header)

        for key, items in groups.items():
            total_rows += len(items)
            if len(items) < 2:
                continue
            for i, a in enumerate(items):
                for b in items[i + 1 :]:
                    comparable_pairs += 1
                    rules, distance_m, name_sim, shared_ratio = pair_rules(a, b)
                    if not rules:
                        continue
                    row_data = [
                        "",
                        ";".join(rules),
                        "" if distance_m is None else f"{distance_m:.2f}",
                        f"{name_sim:.3f}",
                        f"{shared_ratio:.3f}",
                        *key,
                        a.rowid, a.name, a.prefix_removed, a.pinyin, a.lon, a.lat,
                        b.rowid, b.name, b.prefix_removed, b.pinyin, b.lon, b.lat,
                    ]

                    fuzzy_severity = fuzzy_signal_severity(rules, distance_m)
                    fuzzy_pairs += 1
                    fuzzy_severity_counts[fuzzy_severity] += 1
                    fuzzy_rule_counts.update(rules)
                    fuzzy_writer.writerow([fuzzy_severity, *row_data[1:]])

                    severity = merge_review_severity(rules, distance_m)
                    if severity == "none":
                        continue

                    candidate_pairs += 1
                    severity_counts[severity] += 1
                    rule_counts.update(rules)
                    group_hit_counts[key] += 1
                    for item in (a, b):
                        hit = row_hits.setdefault(
                            item.rowid,
                            {
                                "row": item,
                                "pair_count": 0,
                                "high_pair_count": 0,
                                "rules": Counter(),
                            },
                        )
                        hit["pair_count"] = int(hit["pair_count"]) + 1
                        if severity == "high":
                            hit["high_pair_count"] = int(hit["high_pair_count"]) + 1
                        hit["rules"].update(rules)  # type: ignore[union-attr]

                    writer.writerow([
                        severity,
                        *row_data[1:],
                    ])

    with row_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rowid", "市级", "区县级", "乡镇级", "行政村", "自然村",
            "prefix_removed", "拼音", "candidate_pair_count", "high_pair_count", "rule_counts",
        ])
        for rowid, hit in sorted(row_hits.items()):
            item: VillageRow = hit["row"]  # type: ignore[assignment]
            rules: Counter[str] = hit["rules"]  # type: ignore[assignment]
            writer.writerow([
                rowid, item.city, item.county, item.township, item.admin, item.name,
                item.prefix_removed, item.pinyin, hit["pair_count"], hit["high_pair_count"],
                ";".join(f"{rule}:{count}" for rule, count in rules.most_common()),
            ])

    top_groups = group_hit_counts.most_common(30)
    lines = [
        "# Intra-Administrative-Village Near Duplicate Audit",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Database: `{db_path}`",
        f"- Table: `{RAW_TABLE}`",
        f"- Group key: `市级 + 区县级 + 乡镇级 + 行政村`",
        f"- Rows covered: **{total_rows:,}**",
        f"- Groups covered: **{total_groups:,}**",
        f"- Exhaustive within-group pairs compared: **{comparable_pairs:,}**",
        f"- Merge-review candidate pairs emitted: **{candidate_pairs:,}**",
        f"- Broader fuzzy signal pairs emitted: **{fuzzy_pairs:,}**",
        f"- Rows involved in at least one candidate pair: **{len(row_hits):,}**",
        "",
        "## Merge-Review Pair Severity",
        "",
        "| severity | pairs |",
        "|---|---:|",
    ]
    for severity in ["high", "medium"]:
        lines.append(f"| {severity} | {severity_counts.get(severity, 0):,} |")

    lines.extend([
        "",
        "## Rule Counts",
        "",
        "| rule | pairs |",
        "|---|---:|",
    ])
    for rule, count in rule_counts.most_common(40):
        lines.append(f"| `{rule}` | {count:,} |")

    lines.extend([
        "",
        "## Broader Fuzzy Signal Counts",
        "",
        "| fuzzy severity | pairs |",
        "|---|---:|",
    ])
    for severity, count in fuzzy_severity_counts.most_common():
        lines.append(f"| {severity} | {count:,} |")
    lines.extend([
        "",
        "| fuzzy rule | pairs |",
        "|---|---:|",
    ])
    for rule, count in fuzzy_rule_counts.most_common(20):
        lines.append(f"| `{rule}` | {count:,} |")

    lines.extend([
        "",
        "## Top Groups By Candidate Pair Count",
        "",
        "| candidate pairs | 市级 | 区县级 | 乡镇级 | 行政村 |",
        "|---:|---|---|---|---|",
    ])
    for key, count in top_groups:
        lines.append(f"| {count:,} | {key[0]} | {key[1]} | {key[2]} | {key[3]} |")

    lines.extend([
        "",
        "## Output Files",
        "",
        "- `merge_review_pairs.csv`: stricter pairs suitable for manual merge review.",
        "- `row_candidate_coverage.csv`: rows that participate in one or more merge-review pairs.",
        "- `fuzzy_signals.csv`: broad fuzzy matches for research only; do not use directly for merging.",
        "",
        "Merge-review candidates deliberately exclude edit-distance-only pairs, because shared generic place-name morphemes can make distinct villages look similar.",
        "",
    ])
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit(args.db, args.output_dir)
    print(f"Audit complete: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
