#!/usr/bin/env python3
"""
数据库验证脚本
Database Verification Script

检查数据库文件、表结构和基本统计信息
"""
import sqlite3
import os
from pathlib import Path

def format_size(bytes_size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def verify_database():
    """验证数据库"""
    db_path = "data/villages.db"

    print("=" * 60)
    print("数据库验证报告")
    print("Database Verification Report")
    print("=" * 60)
    print()

    # 检查文件是否存在
    if not os.path.exists(db_path):
        print(f"❌ 错误: 数据库文件不存在")
        print(f"   路径: {os.path.abspath(db_path)}")
        return False

    # 文件大小
    file_size = os.path.getsize(db_path)
    print(f"✓ 数据库文件: {db_path}")
    print(f"  大小: {format_size(file_size)}")
    print()

    # 连接数据库
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"✓ 数据库表数量: {len(tables)}")
        print()

        # 显示每个表的行数
        print("表统计信息:")
        print("-" * 60)
        print(f"{'表名':<40} {'行数':>15}")
        print("-" * 60)

        total_rows = 0
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                total_rows += count
                print(f"{table:<40} {count:>15,}")
            except Exception as e:
                print(f"{table:<40} {'错误':>15}")

        print("-" * 60)
        print(f"{'总计':<40} {total_rows:>15,}")
        print()

        # 检查关键表
        key_tables = [
            "广东省自然村",
            "character_frequency",
            "village_features",
            "cluster_assignments",
            "semantic_labels"
        ]

        print("关键表检查:")
        print("-" * 60)
        for table in key_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                print(f"✓ {table}: {count:,} 行")
            else:
                print(f"❌ {table}: 不存在")

        print()
        print("=" * 60)
        print("✓ 数据库验证完成")
        print("=" * 60)

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        return False

if __name__ == "__main__":
    verify_database()
