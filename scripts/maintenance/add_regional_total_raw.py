#!/usr/bin/env python3
"""
计算并添加 regional_total_raw 和 total_before_filter 字段

这个脚本用于在重新生成 n-gram 数据时，计算每个区域的原始 n-gram 总数（清理前）。

使用方法：
1. 在 phase12_ngram_analysis.py 的 Step 3 之后调用此脚本
2. 在 Step 4 和 Step 5 中使用计算出的原始总数
"""

import sqlite3
from collections import defaultdict


def calculate_regional_total_raw(db_path: str = 'data/villages.db'):
    """
    计算每个区域的原始 n-gram 总数（清理前）

    返回一个字典：
    {
        (level, city, county, township, n, position): total_raw
    }
    """
    print("\n" + "="*70)
    print("计算区域原始 n-gram 总数（清理前）")
    print("="*70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 统计每个区域的原始 n-gram 总数
    regional_totals_raw = {}

    # 查询所有区域的 n-gram 数据
    cursor.execute("""
        SELECT level, city, county, township, n, position, COUNT(*) as ngram_count
        FROM regional_ngram_frequency
        GROUP BY level, city, county, township, n, position
    """)

    for row in cursor.fetchall():
        level, city, county, township, n, position, count = row
        key = (level, city, county, township, n, position)
        regional_totals_raw[key] = count

    print(f"  计算了 {len(regional_totals_raw):,} 个区域-位置组合的原始总数")

    conn.close()

    return regional_totals_raw


def save_regional_totals_to_temp_table(db_path: str, regional_totals_raw: dict):
    """
    将原始总数保存到临时表中，供后续步骤使用
    """
    print("\n保存原始总数到临时表...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建临时表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_regional_totals_raw (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            total_raw INTEGER NOT NULL,
            PRIMARY KEY (level, city, county, township, n, position)
        )
    """)

    # 清空旧数据
    cursor.execute("DELETE FROM temp_regional_totals_raw")

    # 插入新数据
    for key, total_raw in regional_totals_raw.items():
        level, city, county, township, n, position = key
        cursor.execute("""
            INSERT INTO temp_regional_totals_raw
            (level, city, county, township, n, position, total_raw)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (level, city, county, township, n, position, total_raw))

    conn.commit()
    conn.close()

    print(f"  保存了 {len(regional_totals_raw):,} 条记录")


def get_regional_total_raw(db_path: str, level: str, city: str, county: str,
                           township: str, n: int, position: str) -> int:
    """
    从临时表中获取指定区域的原始 n-gram 总数
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT total_raw
        FROM temp_regional_totals_raw
        WHERE level = ? AND city IS ? AND county IS ? AND township IS ?
          AND n = ? AND position = ?
    """, (level, city, county, township, n, position))

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


if __name__ == '__main__':
    # 测试
    db_path = 'data/villages.db'

    # 计算原始总数
    regional_totals_raw = calculate_regional_total_raw(db_path)

    # 保存到临时表
    save_regional_totals_to_temp_table(db_path, regional_totals_raw)

    print("\n" + "="*70)
    print("完成！")
    print("="*70)
    print("\n临时表 temp_regional_totals_raw 已创建")
    print("可以在 Step 4 和 Step 5 中使用 get_regional_total_raw() 函数获取原始总数")
