"""Audit raw village names for POI-like non-natural-village terms.

This is a full-table scan of the raw table. It does not modify the database.
The result is a candidate list, not a deletion list.
"""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


DB_PATH = Path("data/villages.db")
OUTPUT_DIR = Path("results/non_village_audit")
RAW_TABLE = "广东省自然村"


CATEGORIES: dict[str, list[str]] = {
    "residential_property": [
        "小区", "住宅区", "生活区", "宿舍区", "公寓", "别墅", "楼盘", "商住",
        "大厦", "豪庭", "华庭", "雅苑", "名苑", "御景", "花园", "家园",
        "安置区", "安置点", "安置房", "家属房", "家属区", "新村小区",
    ],
    "school_education": [
        "学校", "小学", "中学", "大学", "学院", "幼儿园", "中心校", "教学点",
        "职校", "技校",
    ],
    "transport_station": [
        "火车站", "高铁站", "动车站", "汽车站", "客运站", "车站", "地铁站",
        "站场", "机场", "码头", "渡口", "港口", "收费站", "服务区", "停车场",
    ],
    "medical_health": [
        "医院", "卫生院", "卫生站", "卫生室", "诊所", "疗养院", "疾控", "保健院",
    ],
    "government_admin": [
        "政府", "镇府", "街道办", "办事处", "派出所", "公安", "法院", "检察院",
        "司法所", "税务", "财政所", "国土所", "村委", "居委", "委员会",
        "管理处", "管理区", "管理局", "管养所", "管理所", "工程管理",
    ],
    "commercial_market": [
        "市场", "商场", "超市", "商城", "商贸城", "批发", "酒店", "宾馆",
        "饭店", "农贸", "商业街",
    ],
    "industrial_enterprise": [
        "工业园", "产业园", "开发区", "园区", "工厂", "公司", "企业", "基地",
        "仓库", "矿场", "采石场", "砖厂", "电厂", "变电站", "电站", "泵站",
    ],
    "farm_forest_field": [
        "农场", "林场", "茶场", "果场", "牧场", "渔场", "盐场", "养殖场",
        "种养场", "良种场", "园艺场", "畜牧场", "华侨农场",
    ],
    "water_scenic_facility": [
        "水库", "景区", "旅游区", "公园", "森林公园", "保护区", "度假区",
        "游乐园", "纪念馆", "博物馆", "水库管养所", "水库工程",
    ],
    "religion_cemetery": [
        "寺", "庙", "庵", "宫", "观", "教堂", "祠", "墓", "陵园", "公墓",
        "殡仪馆", "骨灰楼",
    ],
    "road_infrastructure": [
        "大道", "公路", "高速", "铁路", "隧道", "大桥", "桥梁", "立交",
        "路口", "路段",
    ],
    "migration_resettlement": [
        "移民", "移民村", "移民新村", "三峡移民", "水库移民", "移民小区",
        "移民队", "安置",
    ],
}


# These characters/short words are common natural-village morphemes too. They
# are still useful review signals, but should not be counted as strong evidence.
WEAK_TERMS = {"寺", "庙", "庵", "祠", "墓", "宫", "观"}
VILLAGE_FORM_SUFFIXES = (
    "村", "新村", "旧村", "片", "屋", "围", "寨", "坑", "岭", "岺", "垄",
    "垅", "岗", "冈", "埔", "厝", "楼", "社", "里", "坊", "巷", "园",
    "田", "塘", "垌", "洞", "坪", "坳", "凹", "埇", "寮", "塱", "角",
)
VILLAGE_FORM_PROTECTED_TERMS = {
    "大桥", "桥梁", "寺", "庙", "庵", "宫", "观", "教堂", "祠", "墓",
}
MEDIUM_TERMS = {
    "公路", "大道", "水库", "农场", "林场", "茶场", "果场", "牧场",
    "渔场", "移民", "移民村", "移民新村", "三峡移民", "水库移民",
    "移民队", "安置",
}
HIGH_PATTERNS = [
    ("residential_property", "小区"),
    ("residential_property", "生活区"),
    ("residential_property", "住宅区"),
    ("residential_property", "宿舍区"),
    ("residential_property", "家属房"),
    ("residential_property", "家属区"),
    ("government_admin", "管理处"),
    ("government_admin", "管理局"),
    ("government_admin", "管养所"),
    ("government_admin", "管理所"),
    ("government_admin", "派出所"),
    ("school_education", "学校"),
    ("school_education", "小学"),
    ("school_education", "中学"),
    ("medical_health", "医院"),
    ("transport_station", "火车站"),
    ("transport_station", "高铁站"),
    ("transport_station", "收费站"),
    ("industrial_enterprise", "工业园"),
    ("industrial_enterprise", "开发区"),
    ("industrial_enterprise", "公司"),
    ("commercial_market", "市场"),
]


def term_strength(name: str, term: str) -> str:
    if term in VILLAGE_FORM_PROTECTED_TERMS and name.endswith(VILLAGE_FORM_SUFFIXES):
        return "weak"
    if term in WEAK_TERMS and name != term:
        return "weak"
    if term in MEDIUM_TERMS:
        return "medium"
    return "strong"


def risk_level(hits: list[tuple[str, str, str]]) -> str:
    if any((category, term) in HIGH_PATTERNS for category, term, _ in hits):
        return "high"
    if any(strength == "strong" for _, _, strength in hits):
        return "high"
    if any(strength == "medium" for _, _, strength in hits):
        return "medium"
    return "weak"


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"""
        SELECT rowid, 市级, 区县级, 乡镇级, 行政村, 自然村, 拼音, 方言分布,
               longitude, latitude
        FROM "{RAW_TABLE}"
        ORDER BY rowid
        """
    ).fetchall()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    row_hits = []
    category_rows: dict[str, set[int]] = defaultdict(set)
    category_strong_rows: dict[str, set[int]] = defaultdict(set)
    category_medium_rows: dict[str, set[int]] = defaultdict(set)
    term_counts: Counter[tuple[str, str, str]] = Counter()
    strength_counts: Counter[str] = Counter()

    for row in rows:
        name = (row["自然村"] or "").strip()
        hits = []
        for category, terms in CATEGORIES.items():
            for term in terms:
                if term in name:
                    strength = term_strength(name, term)
                    hits.append((category, term, strength))
                    category_rows[category].add(row["rowid"])
                    term_counts[(category, term, strength)] += 1
                    if strength == "strong":
                        category_strong_rows[category].add(row["rowid"])
                    elif strength == "medium":
                        category_medium_rows[category].add(row["rowid"])
        if not hits:
            continue
        overall = risk_level(hits)
        strength_counts[overall] += 1
        row_hits.append((row, hits, overall))

    with (OUTPUT_DIR / "poi_like_rows.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rowid", "市级", "区县级", "乡镇级", "行政村", "自然村", "拼音",
            "risk_level", "hits", "longitude", "latitude",
        ])
        for row, hits, overall in row_hits:
            writer.writerow([
                row["rowid"], row["市级"], row["区县级"], row["乡镇级"],
                row["行政村"], row["自然村"], row["拼音"], overall,
                ";".join(":".join(hit) for hit in hits),
                row["longitude"], row["latitude"],
            ])

    with (OUTPUT_DIR / "possible_non_village_all.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rowid", "市级", "区县级", "乡镇级", "行政村", "自然村", "拼音",
            "方言分布", "risk_level", "hits", "longitude", "latitude",
            "review_note",
        ])
        note_map = {
            "high": "明显POI/设施/机构/住宅/管理类，优先复核",
            "medium": "可能已地名化，也可能是设施/安置/道路/水库类，需复核",
            "weak": "弱信号，宗教/墓/庙祠等常见地名化成分",
        }
        for row, hits, overall in row_hits:
            writer.writerow([
                row["rowid"], row["市级"], row["区县级"], row["乡镇级"],
                row["行政村"], row["自然村"], row["拼音"], row["方言分布"],
                overall, ";".join(":".join(hit) for hit in hits),
                row["longitude"], row["latitude"], note_map[overall],
            ])

    with (OUTPUT_DIR / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "rows_any", "rows_high_or_strong", "rows_medium"])
        for category in CATEGORIES:
            writer.writerow([
                category,
                len(category_rows[category]),
                len(category_strong_rows[category]),
                len(category_medium_rows[category]),
            ])

    print(f"total_rows={len(rows)}")
    print(f"poi_like_rows_any={len(row_hits)}")
    print(f"poi_like_rows_high={strength_counts['high']}")
    print(f"poi_like_rows_medium={strength_counts['medium']}")
    print(f"poi_like_rows_weak={strength_counts['weak']}")
    print("categories:")
    for category in CATEGORIES:
        print(
            category,
            len(category_rows[category]),
            len(category_strong_rows[category]),
            len(category_medium_rows[category]),
        )
    print("top_terms:")
    for (category, term, strength), count in term_counts.most_common(60):
        print(category, term, strength, count)
    print(f"output={OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
