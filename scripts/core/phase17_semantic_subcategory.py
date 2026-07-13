#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 17: 语义子类别细化

LEXICON VERSION: v4 (9 parents, 53 subcategories)
- Hierarchical format: {parent: {sub: [chars]}}
- Path: data/semantic_lexicon_v4.json
- Generates: semantic_subcategory_* tables

功能：
1. 加载 v4 词典
2. 创建子类别数据表
3. 计算子类别虚拟词频（VTF）
4. 生成区域子类别分布统计
5. 验证数据质量

作者：Claude Code
日期：2026-02-25 / 更新：2026-07-13（切到 v4）
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "villages.db"
LEXICON_V4_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v4.json"


def load_lexicon(path: Path) -> Dict:
    """加载语义词典"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def flatten_v4_subcategories(v4: Dict) -> List[Tuple[str, str, str]]:
    """Flatten nested v4 format {parent: {sub: [chars]}} into (parent_sub, parent, char) tuples.

    Within a parent, a char in multiple subcategories gets ALL entries
    (e.g. 关 → both clan_cantonese and clan_teochew).
    Cross-parent duplicates: first parent wins, then multi_label entries
    add secondary parent subcategory mappings (e.g. 坑 → terrain_valley + water_stream).
    """
    seen_parent: set = set()
    char_first_parent: dict = {}
    result = []
    categories = v4.get("categories", {})

    for parent, children in categories.items():
        if isinstance(children, dict):
            char_subs: dict = {}
            for sub, chars in children.items():
                for char in chars:
                    char_subs.setdefault(char, []).append(sub)
            for char, subs in char_subs.items():
                if char in seen_parent:
                    continue
                seen_parent.add(char)
                char_first_parent[char] = parent
                for sub in subs:
                    result.append((f'{parent}_{sub}', parent, char))
        else:
            for char in children:
                if char in seen_parent:
                    continue
                seen_parent.add(char)
                char_first_parent[char] = parent
                result.append((parent, parent, char))

    # Add secondary parent entries from multi_label
    multi = v4.get('multi_label', {})
    for char, parents in multi.items():
        first = char_first_parent.get(char)
        if first is None:
            continue
        for parent in parents:
            if parent == first:
                continue
            children = categories.get(parent, {})
            if isinstance(children, dict):
                for sub, chars in children.items():
                    if char in chars:
                        result.append((f'{parent}_{sub}', parent, char))

    return result


def create_subcategory_tables(conn: sqlite3.Connection):
    """创建子类别相关数据表"""
    print("\n" + "=" * 60)
    print("Step 2: 创建子类别数据表")
    print("=" * 60)

    cursor = conn.cursor()

    # 1. semantic_subcategory_labels - 字符到子类别映射
    cursor.execute("DROP TABLE IF EXISTS semantic_subcategory_labels")
    cursor.execute("""
        CREATE TABLE semantic_subcategory_labels (
            char TEXT NOT NULL,
            parent_category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            labeling_method TEXT DEFAULT 'manual',
            created_at REAL DEFAULT (julianday('now')),
            PRIMARY KEY (char, subcategory)
        )
    """)
    print("[OK] 创建表：semantic_subcategory_labels")

    # 2. semantic_subcategory_vtf_global - 全局子类别 VTF
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_subcategory_vtf_global (
            subcategory TEXT PRIMARY KEY,
            parent_category TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            village_count INTEGER NOT NULL,
            vtf REAL NOT NULL,
            percentage REAL NOT NULL,
            created_at REAL DEFAULT (julianday('now'))
        )
    """)
    print("[OK] 创建表：semantic_subcategory_vtf_global")

    # 3. semantic_subcategory_vtf_regional - 区域子类别 VTF
    cursor.execute("DROP TABLE IF EXISTS semantic_subcategory_vtf_regional")
    cursor.execute("""
        CREATE TABLE semantic_subcategory_vtf_regional (
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            subcategory TEXT NOT NULL,
            parent_category TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            village_count INTEGER NOT NULL,
            vtf REAL NOT NULL,
            percentage REAL NOT NULL,
            tendency REAL,
            created_at REAL DEFAULT (julianday('now')),
            PRIMARY KEY (region_level, region_name, subcategory)
        )
    """)
    print("[OK] 创建表：semantic_subcategory_vtf_regional")

    conn.commit()
    print("[OK] 所有表创建完成")


def populate_subcategory_labels(conn: sqlite3.Connection, v4: Dict):
    """填充子类别标签表"""
    print("\n" + "=" * 60)
    print("Step 3: 填充子类别标签")
    print("=" * 60)

    cursor = conn.cursor()

    # 清空旧数据
    cursor.execute("DELETE FROM semantic_subcategory_labels")

    # Flatten nested v4 format {parent: {sub: [chars]}} → (parent_sub, parent, char)
    flat = flatten_v4_subcategories(v4)

    labels = [(char, parent, subcategory, 1.0, 'v4') for subcategory, parent, char in flat]

    cursor.executemany("""
        INSERT INTO semantic_subcategory_labels
        (char, parent_category, subcategory, confidence, labeling_method)
        VALUES (?, ?, ?, ?, ?)
    """, labels)

    conn.commit()
    print(f"[OK] 已插入 {len(labels)} 条子类别标签")
    print(f"   - {len(set(p for _, p, _ in flat))} 个父类别")
    print(f"   - {len(set(s for s, _, _ in flat))} 个子类别")

    # 验证覆盖率（按父类别统计）
    cursor.execute("""
        SELECT parent_category, COUNT(DISTINCT char) as char_count
        FROM semantic_subcategory_labels
        GROUP BY parent_category
        ORDER BY parent_category
    """)

    print("\n子类别覆盖情况：")
    for parent, count in cursor.fetchall():
        print(f"  {parent}: {count} 个字符")


def calculate_subcategory_vtf_global(conn: sqlite3.Connection):
    """计算全局子类别虚拟词频"""
    print("\n" + "=" * 60)
    print("Step 4: 计算全局子类别 VTF")
    print("=" * 60)

    cursor = conn.cursor()

    # 清空旧数据
    cursor.execute("DELETE FROM semantic_subcategory_vtf_global")

    # 计算每个子类别的 VTF
    # VTF = 子类别各字符 village_count 之和（与父类 VTF 同口径）
    cursor.execute("""
        INSERT INTO semantic_subcategory_vtf_global
        (subcategory, parent_category, char_count, village_count, vtf, percentage)
        SELECT
            sl.subcategory,
            sl.parent_category,
            COUNT(DISTINCT sl.char) as char_count,
            SUM(cf.village_count) as village_count,
            CAST(SUM(cf.village_count) AS REAL) /
                (SELECT COUNT(*) FROM 广东省自然村_预处理) as vtf,
            CAST(SUM(cf.village_count) AS REAL) /
                (SELECT COUNT(*) FROM 广东省自然村_预处理) as percentage
        FROM semantic_subcategory_labels sl
        JOIN char_frequency_global cf ON sl.char = cf.char
        GROUP BY sl.subcategory, sl.parent_category
    """)

    conn.commit()

    # 显示结果
    cursor.execute("""
        SELECT subcategory, parent_category, char_count, village_count,
               vtf, percentage
        FROM semantic_subcategory_vtf_global
        ORDER BY parent_category, vtf DESC
    """)

    print("\n全局子类别 VTF 统计：")
    print(f"{'子类别':<25} {'父类别':<12} {'字符数':<8} {'村庄数':<10} {'VTF':<10} {'频率':<10}")
    print("-" * 85)

    for row in cursor.fetchall():
        subcat, parent, char_count, village_count, vtf, pct = row
        print(f"{subcat:<25} {parent:<12} {char_count:<8} {village_count:<10} {vtf:<10.4f} {pct:<10.4f}")

    # 统计总数
    cursor.execute("SELECT COUNT(*) FROM semantic_subcategory_vtf_global")
    total = cursor.fetchone()[0]
    print(f"\n[OK] 已计算 {total} 个子类别的全局 VTF")


def calculate_subcategory_vtf_regional(conn: sqlite3.Connection):
    """计算区域子类别虚拟词频"""
    print("\n" + "=" * 60)
    print("Step 5: 计算区域子类别 VTF")
    print("=" * 60)

    cursor = conn.cursor()

    # 清空旧数据
    cursor.execute("DELETE FROM semantic_subcategory_vtf_regional")

    # 基于 char_regional_analysis 统一计算三级区域子类别 VTF
    # 与父类 VTF 同口径：SUM(per-char village_count) 而非 COUNT(DISTINCT village)
    print("计算市级/区县级/乡镇级区域...")
    cursor.execute("""
        INSERT INTO semantic_subcategory_vtf_regional
        (region_level, region_name, city, county, township,
         subcategory, parent_category, char_count, village_count,
         vtf, percentage, tendency)
        SELECT
            cra.region_level,
            cra.region_name,
            MAX(cra.city) as city,
            MAX(cra.county) as county,
            MAX(cra.township) as township,
            sl.subcategory,
            sl.parent_category,
            COUNT(DISTINCT sl.char) as char_count,
            SUM(cra.village_count) as village_count,
            CAST(SUM(cra.village_count) AS REAL) / MAX(cra.total_villages) as vtf,
            CAST(SUM(cra.village_count) AS REAL) / MAX(cra.total_villages) as percentage,
            (CAST(SUM(cra.village_count) AS REAL) / MAX(cra.total_villages)) - gv.global_pct as tendency
        FROM semantic_subcategory_labels sl
        JOIN char_regional_analysis cra ON sl.char = cra.char
        JOIN (
            SELECT subcategory, percentage as global_pct
            FROM semantic_subcategory_vtf_global
        ) gv ON sl.subcategory = gv.subcategory
        GROUP BY cra.region_level, cra.region_name, sl.subcategory, sl.parent_category
    """)

    conn.commit()

    # 统计结果
    cursor.execute("""
        SELECT region_level, COUNT(DISTINCT region_name) as region_count,
               COUNT(*) as record_count
        FROM semantic_subcategory_vtf_regional
        GROUP BY region_level
    """)

    print("\n区域子类别 VTF 统计：")
    for region_level, region_count, record_count in cursor.fetchall():
        print(f"  {region_level}: {region_count} 个区域, {record_count} 条记录")

    print("[OK] 区域子类别 VTF 计算完成")


def validate_subcategory_data(conn: sqlite3.Connection):
    """验证子类别数据质量"""
    print("\n" + "=" * 60)
    print("Step 6: 验证数据质量")
    print("=" * 60)

    cursor = conn.cursor()

    # 1. 检查覆盖率
    cursor.execute("""
        SELECT parent_category, COUNT(DISTINCT char) as labeled_count
        FROM semantic_subcategory_labels
        GROUP BY parent_category
    """)

    print("\n1. 子类别覆盖率：")
    for parent, count in cursor.fetchall():
        print(f"   {parent}: {count} 个字符已标注")

    # 2. 检查子类别分布
    cursor.execute("""
        SELECT subcategory, COUNT(*) as char_count
        FROM semantic_subcategory_labels
        GROUP BY subcategory
        ORDER BY char_count DESC
    """)

    print("\n2. 子类别字符分布：")
    for subcat, count in cursor.fetchall():
        print(f"   {subcat}: {count} 个字符")

    # 3. 检查 VTF 数据完整性
    cursor.execute("SELECT COUNT(*) FROM semantic_subcategory_vtf_global")
    global_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT subcategory) FROM semantic_subcategory_labels")
    expected_count = cursor.fetchone()[0]

    print(f"\n3. VTF 数据完整性：")
    print(f"   全局 VTF: {global_count}/{expected_count} 个子类别")

    if global_count == expected_count:
        print("   [OK] 全局 VTF 数据完整")
    else:
        print("   [WARNING] 全局 VTF 数据不完整")

    # 4. 检查区域 VTF 数据
    cursor.execute("""
        SELECT COUNT(DISTINCT region_name) as region_count,
               COUNT(*) as record_count
        FROM semantic_subcategory_vtf_regional
    """)

    region_count, record_count = cursor.fetchone()
    print(f"\n4. 区域 VTF 数据：")
    print(f"   {region_count} 个区域, {record_count} 条记录")

    # 5. 检查倾向值分布
    cursor.execute("""
        SELECT
            subcategory,
            MAX(tendency) as max_tendency,
            MIN(tendency) as min_tendency,
            AVG(tendency) as avg_tendency
        FROM semantic_subcategory_vtf_regional
        GROUP BY subcategory
        ORDER BY max_tendency DESC
        LIMIT 5
    """)

    print(f"\n5. 倾向值最高的 5 个子类别：")
    print(f"{'子类别':<25} {'最大倾向':<12} {'最小倾向':<12} {'平均倾向':<12}")
    print("-" * 65)

    for row in cursor.fetchall():
        subcat, max_t, min_t, avg_t = row
        print(f"{subcat:<25} {max_t:>11.2f} {min_t:>11.2f} {avg_t:>11.2f}")

    print("\n[OK] 数据验证完成")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Phase 17: 语义子类别细化（v4 词典：9 父类, 53 子类）")
    print("=" * 60)
    print(f"数据库：{DB_PATH}")
    print(f"v4 词典：{LEXICON_V4_PATH}")
    print("=" * 60)

    start_time = time.time()

    # Step 1: 加载 v4 词典
    print("\n" + "=" * 60)
    print("Step 1: 加载 v4 词典")
    print("=" * 60)

    if not LEXICON_V4_PATH.exists():
        print(f"[ERROR] v4 词典不存在：{LEXICON_V4_PATH}")
        return

    v4 = load_lexicon(LEXICON_V4_PATH)
    flat = flatten_v4_subcategories(v4)
    print(f"[OK] 已加载 v4 词典：{LEXICON_V4_PATH}")
    print(f"   - 版本：{v4.get('version', 'unknown')}")
    print(f"   - {len(set(s for s, _, _ in flat))} 个子类别")
    print(f"   - {len(flat)} 个字符映射")

    # 连接数据库
    conn = sqlite3.connect(DB_PATH)

    try:
        # Step 2: 创建数据表
        create_subcategory_tables(conn)

        # Step 3: 填充子类别标签
        populate_subcategory_labels(conn, v4)

        # Step 4: 计算全局 VTF
        calculate_subcategory_vtf_global(conn)

        # Step 5: 计算区域 VTF
        calculate_subcategory_vtf_regional(conn)

        # Step 6: 验证数据质量
        validate_subcategory_data(conn)

    finally:
        conn.close()

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[OK] Phase 17 试点实施完成！")
    print(f"[TIME] 总耗时：{elapsed:.2f} 秒")
    print("=" * 60)

    print("\n下一步：")
    print("1. 验证数据：SELECT COUNT(*) FROM semantic_subcategory_vtf_global（预期 53 行）")
    print("2. 查询子类别数据：semantic_subcategory_* 表")
    print("3. 对比 v4_hybrid 旧数据：76→53 子类别，确保无遗漏")


if __name__ == "__main__":
    main()
