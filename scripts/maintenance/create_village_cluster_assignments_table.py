#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建 village_cluster_assignments 表

用于存储多个版本的村庄-聚类分配
"""

import sqlite3
import time

def create_table():
    """创建 village_cluster_assignments 表"""

    conn = sqlite3.connect('data/villages.db')
    cursor = conn.cursor()

    print("=" * 70)
    print("创建 village_cluster_assignments 表")
    print("=" * 70)

    # 1. 创建表
    print("\n1. 创建表结构...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS village_cluster_assignments (
            run_id TEXT NOT NULL,
            village_id TEXT NOT NULL,
            cluster_id INTEGER NOT NULL,
            cluster_size INTEGER,
            cluster_probability REAL,
            created_at REAL NOT NULL,
            PRIMARY KEY (run_id, village_id)
        )
    ''')
    print("[OK] 表结构创建完成")

    # 2. 创建索引
    print("\n2. 创建索引...")
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_vca_run_id
        ON village_cluster_assignments(run_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_vca_cluster_id
        ON village_cluster_assignments(run_id, cluster_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_vca_village_id
        ON village_cluster_assignments(village_id)
    ''')
    print("[OK] 索引创建完成")

    # 3. 从 village_spatial_features 迁移当前数据
    print("\n3. 迁移当前数据...")

    # 检查当前 village_spatial_features 中的聚类分配
    cursor.execute('''
        SELECT COUNT(DISTINCT spatial_cluster_id)
        FROM village_spatial_features
        WHERE spatial_cluster_id >= 0
    ''')
    n_clusters = cursor.fetchone()[0]

    # 判断当前是哪个版本（根据聚类数）
    if n_clusters == 253:
        current_run_id = 'spatial_eps_20'
    elif n_clusters > 7000:
        current_run_id = 'spatial_hdbscan_v1'
    elif n_clusters > 4000:
        current_run_id = 'spatial_eps_10'
    elif n_clusters > 8000:
        current_run_id = 'spatial_eps_03'
    else:
        current_run_id = 'unknown'

    print(f"   检测到当前版本: {current_run_id} ({n_clusters} 个聚类)")

    # 迁移数据
    cursor.execute(f'''
        INSERT OR REPLACE INTO village_cluster_assignments
            (run_id, village_id, cluster_id, cluster_size, created_at)
        SELECT
            '{current_run_id}' as run_id,
            village_id,
            spatial_cluster_id as cluster_id,
            cluster_size,
            {time.time()} as created_at
        FROM village_spatial_features
        WHERE spatial_cluster_id >= 0
    ''')

    migrated = cursor.rowcount
    print(f"[OK] 迁移了 {migrated} 条记录")

    conn.commit()

    # 4. 验证
    print("\n4. 验证...")
    cursor.execute('''
        SELECT run_id, COUNT(*) as count
        FROM village_cluster_assignments
        GROUP BY run_id
    ''')
    for run_id, count in cursor.fetchall():
        print(f"   {run_id}: {count} 条记录")

    conn.close()

    print("\n" + "=" * 70)
    print("完成！")
    print("=" * 70)
    print("\n说明:")
    print("- village_spatial_features 表保持不变（后端API继续使用）")
    print("- village_cluster_assignments 表存储所有版本的聚类分配")
    print("- 分析脚本可以使用 village_cluster_assignments 表获取特定版本")

if __name__ == "__main__":
    create_table()
