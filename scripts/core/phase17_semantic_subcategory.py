#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 17: 语义子类别细化

试点实施：细化 mountain 和 water 两个类别为 16 个子类别

LEXICON VERSION: v4_hybrid (76 subcategories)
- Uses LLM + expert hybrid classification
- Path: data/semantic_lexicon_v4_hybrid.json
- Generates: semantic_subcategory_* tables

功能：
1. 基于 v3_expanded 创建 v4_pilot 词典
2. 创建子类别数据表
3. 计算子类别虚拟词频（VTF）
4. 生成区域子类别分布统计
5. 验证数据质量

作者：Claude Code
日期：2026-02-25
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
LEXICON_V1_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v1.json"
LEXICON_V3_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v3_expanded.json"
LEXICON_V4_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v4_pilot.json"
LEXICON_V4_HYBRID_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v4_hybrid.json"


def load_lexicon(path: Path) -> Dict:
    """加载语义词典"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_v4_pilot_lexicon():
    """
    创建 v4_pilot 词典

    策略：
    - 保留 v1 的 9 大类别结构
    - 从 v3_expanded 提取 mountain 和 water 的子类别
    - 其他 7 个类别保持不变
    """
    print("=" * 60)
    print("Step 1: 创建 v4_pilot 词典")
    print("=" * 60)

    v1 = load_lexicon(LEXICON_V1_PATH)
    v3 = load_lexicon(LEXICON_V3_PATH)

    # 创建 v4 词典结构
    v4 = {
        "version": "4.0.0-pilot",
        "created_at": time.strftime("%Y-%m-%d"),
        "description": "Pilot semantic lexicon with refined mountain and water subcategories",
        "parent_categories": {},  # 9 大类别（保持向后兼容）
        "subcategories": {}       # 16 个子类别（新增）
    }

    # 复制 v1 的 9 大类别
    v4["parent_categories"] = v1["categories"].copy()

    # 提取 mountain 子类别
    mountain_subcats = [
        "mountain_peak", "mountain_slope", "mountain_valley",
        "mountain_ridge", "mountain_rock", "mountain_plateau"
    ]

    # 提取 water 子类别
    water_subcats = [
        "water_river", "water_stream", "water_port", "water_pond",
        "water_lake", "water_bay", "water_shore", "water_island",
        "water_beach", "water_spring"
    ]

    # 从 v3 复制子类别
    for subcat in mountain_subcats + water_subcats:
        if subcat in v3["categories"]:
            v4["subcategories"][subcat] = v3["categories"][subcat]
        else:
            print(f"⚠️  警告：v3 中未找到子类别 {subcat}")

    # 保存 v4 词典
    with open(LEXICON_V4_PATH, 'w', encoding='utf-8') as f:
        json.dump(v4, f, ensure_ascii=False, indent=2)

    print(f"[OK] v4_pilot 词典已创建：{LEXICON_V4_PATH}")
    print(f"   - 9 大类别（parent_categories）")
    print(f"   - {len(v4['subcategories'])} 个子类别（subcategories）")

    # 统计字符数
    total_chars = sum(len(chars) for chars in v4["subcategories"].values())
    print(f"   - 共 {total_chars} 个字符被细化")

    return v4


def create_subcategory_tables(conn: sqlite3.Connection):
    """创建子类别相关数据表"""
    print("\n" + "=" * 60)
    print("Step 2: 创建子类别数据表")
    print("=" * 60)

    cursor = conn.cursor()

    # 1. semantic_subcategory_labels - 字符到子类别映射
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_subcategory_labels (
            char TEXT PRIMARY KEY,
            parent_category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            labeling_method TEXT DEFAULT 'manual',
            created_at REAL DEFAULT (julianday('now'))
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_subcategory_vtf_regional (
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
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

    # 插入子类别标签
    labels = []
    for subcategory, chars in v4["subcategories"].items():
        # 确定父类别（从子类别名称推断）
        if "_" in subcategory:
            parent = subcategory.split("_")[0]
        else:
            parent = "other"

        for char in chars:
            labels.append((char, parent, subcategory, 1.0, 'hybrid'))

    cursor.executemany("""
        INSERT INTO semantic_subcategory_labels
        (char, parent_category, subcategory, confidence, labeling_method)
        VALUES (?, ?, ?, ?, ?)
    """, labels)

    conn.commit()
    print(f"[OK] 已插入 {len(labels)} 条子类别标签")

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
    # VTF = 包含该子类别任一字符的村庄数
    cursor.execute("""
        WITH subcategory_chars AS (
            SELECT subcategory, parent_category, GROUP_CONCAT(char, '') as chars
            FROM semantic_subcategory_labels
            GROUP BY subcategory, parent_category
        ),
        village_subcategory AS (
            SELECT
                sc.subcategory,
                sc.parent_category,
                COUNT(DISTINCT v.自然村_规范名) as village_count,
                COUNT(DISTINCT sl.char) as char_count
            FROM subcategory_chars sc
            CROSS JOIN 广东省自然村_预处理 v
            JOIN semantic_subcategory_labels sl ON sc.subcategory = sl.subcategory
            WHERE INSTR(v.字符集, sl.char) > 0
            GROUP BY sc.subcategory, sc.parent_category
        ),
        total_villages AS (
            SELECT COUNT(*) as total FROM 广东省自然村_预处理
        )
        INSERT INTO semantic_subcategory_vtf_global
        (subcategory, parent_category, char_count, village_count, vtf, percentage)
        SELECT
            vs.subcategory,
            vs.parent_category,
            vs.char_count,
            vs.village_count,
            CAST(vs.village_count AS REAL) as vtf,
            CAST(vs.village_count AS REAL) / tv.total * 100 as percentage
        FROM village_subcategory vs
        CROSS JOIN total_villages tv
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
    print(f"{'子类别':<25} {'父类别':<12} {'字符数':<8} {'村庄数':<10} {'VTF':<10} {'占比%':<8}")
    print("-" * 85)

    for row in cursor.fetchall():
        subcat, parent, char_count, village_count, vtf, pct = row
        print(f"{subcat:<25} {parent:<12} {char_count:<8} {village_count:<10} {vtf:<10.0f} {pct:<8.2f}")

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

    # 计算市级区域的子类别 VTF
    print("计算市级区域...")
    cursor.execute("""
        WITH subcategory_chars AS (
            SELECT subcategory, parent_category, GROUP_CONCAT(char, '') as chars
            FROM semantic_subcategory_labels
            GROUP BY subcategory, parent_category
        ),
        regional_subcategory AS (
            SELECT
                '市级' as region_level,
                v.市级 as region_name,
                sc.subcategory,
                sc.parent_category,
                COUNT(DISTINCT sl.char) as char_count,
                COUNT(DISTINCT v.自然村_规范名) as village_count
            FROM subcategory_chars sc
            CROSS JOIN 广东省自然村_预处理 v
            JOIN semantic_subcategory_labels sl ON sc.subcategory = sl.subcategory
            WHERE INSTR(v.字符集, sl.char) > 0
            GROUP BY v.市级, sc.subcategory, sc.parent_category
        ),
        regional_total AS (
            SELECT 市级 as region_name, COUNT(*) as total
            FROM 广东省自然村_预处理
            GROUP BY 市级
        ),
        global_vtf AS (
            SELECT subcategory, vtf as global_vtf, percentage as global_pct
            FROM semantic_subcategory_vtf_global
        )
        INSERT INTO semantic_subcategory_vtf_regional
        (region_level, region_name, subcategory, parent_category,
         char_count, village_count, vtf, percentage, tendency)
        SELECT
            rs.region_level,
            rs.region_name,
            rs.subcategory,
            rs.parent_category,
            rs.char_count,
            rs.village_count,
            CAST(rs.village_count AS REAL) as vtf,
            CAST(rs.village_count AS REAL) / rt.total * 100 as percentage,
            (CAST(rs.village_count AS REAL) / rt.total * 100) - gv.global_pct as tendency
        FROM regional_subcategory rs
        JOIN regional_total rt ON rs.region_name = rt.region_name
        JOIN global_vtf gv ON rs.subcategory = gv.subcategory
    """)

    conn.commit()

    # 计算区县级区域的子类别 VTF
    print("计算区县级区域...")
    cursor.execute("""
        WITH regional_subcategory AS (
            SELECT
                '区县级' as region_level,
                v.区县级 as region_name,
                sl.subcategory,
                sl.parent_category,
                COUNT(DISTINCT sl.char) as char_count,
                COUNT(DISTINCT v.自然村_规范名) as village_count
            FROM 广东省自然村_预处理 v
            JOIN semantic_subcategory_labels sl
            WHERE INSTR(v.字符集, sl.char) > 0
            GROUP BY v.区县级, sl.subcategory, sl.parent_category
        ),
        regional_total AS (
            SELECT 区县级 as region_name, COUNT(*) as total
            FROM 广东省自然村_预处理
            GROUP BY 区县级
        ),
        global_vtf AS (
            SELECT subcategory, percentage as global_pct
            FROM semantic_subcategory_vtf_global
        )
        INSERT INTO semantic_subcategory_vtf_regional
        (region_level, region_name, subcategory, parent_category,
         char_count, village_count, vtf, percentage, tendency)
        SELECT
            rs.region_level,
            rs.region_name,
            rs.subcategory,
            rs.parent_category,
            rs.char_count,
            rs.village_count,
            CAST(rs.village_count AS REAL) as vtf,
            CAST(rs.village_count AS REAL) / rt.total * 100 as percentage,
            (CAST(rs.village_count AS REAL) / rt.total * 100) - gv.global_pct as tendency
        FROM regional_subcategory rs
        JOIN regional_total rt ON rs.region_name = rt.region_name
        JOIN global_vtf gv ON rs.subcategory = gv.subcategory
    """)
    conn.commit()

    # 计算乡镇级区域的子类别 VTF
    print("计算乡镇级区域...")
    cursor.execute("""
        WITH regional_subcategory AS (
            SELECT
                '乡镇级' as region_level,
                v.乡镇级 as region_name,
                sl.subcategory,
                sl.parent_category,
                COUNT(DISTINCT sl.char) as char_count,
                COUNT(DISTINCT v.自然村_规范名) as village_count
            FROM 广东省自然村_预处理 v
            JOIN semantic_subcategory_labels sl
            WHERE INSTR(v.字符集, sl.char) > 0
            GROUP BY v.乡镇级, sl.subcategory, sl.parent_category
        ),
        regional_total AS (
            SELECT 乡镇级 as region_name, COUNT(*) as total
            FROM 广东省自然村_预处理
            GROUP BY 乡镇级
        ),
        global_vtf AS (
            SELECT subcategory, percentage as global_pct
            FROM semantic_subcategory_vtf_global
        )
        INSERT INTO semantic_subcategory_vtf_regional
        (region_level, region_name, subcategory, parent_category,
         char_count, village_count, vtf, percentage, tendency)
        SELECT
            rs.region_level,
            rs.region_name,
            rs.subcategory,
            rs.parent_category,
            rs.char_count,
            rs.village_count,
            CAST(rs.village_count AS REAL) as vtf,
            CAST(rs.village_count AS REAL) / rt.total * 100 as percentage,
            (CAST(rs.village_count AS REAL) / rt.total * 100) - gv.global_pct as tendency
        FROM regional_subcategory rs
        JOIN regional_total rt ON rs.region_name = rt.region_name
        JOIN global_vtf gv ON rs.subcategory = gv.subcategory
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
    print("Phase 17: 语义子类别细化（使用混合词典）")
    print("=" * 60)
    print(f"数据库：{DB_PATH}")
    print(f"混合词典：{LEXICON_V4_HYBRID_PATH}")
    print("=" * 60)

    start_time = time.time()

    # Step 1: 加载混合词典（跳过创建步骤）
    print("\n" + "=" * 60)
    print("Step 1: 加载混合词典")
    print("=" * 60)

    if not LEXICON_V4_HYBRID_PATH.exists():
        print(f"[ERROR] 混合词典不存在：{LEXICON_V4_HYBRID_PATH}")
        print("请先运行 phase17_create_hybrid.py 创建混合词典")
        return

    v4 = load_lexicon(LEXICON_V4_HYBRID_PATH)
    print(f"[OK] 已加载混合词典：{LEXICON_V4_HYBRID_PATH}")
    print(f"   - 版本：{v4.get('version', 'unknown')}")
    print(f"   - {len(v4['subcategories'])} 个子类别")
    print(f"   - {sum(len(chars) for chars in v4['subcategories'].values())} 个字符")

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
    print("1. 查看 v4_pilot 词典：data/semantic_lexicon_v4_pilot.json")
    print("2. 查询子类别数据：semantic_subcategory_* 表")
    print("3. 开发 API 端点：api/semantic/subcategories.py")
    print("4. 产出评估报告：docs/reports/PHASE_17_PILOT_EVALUATION.md")


if __name__ == "__main__":
    main()
