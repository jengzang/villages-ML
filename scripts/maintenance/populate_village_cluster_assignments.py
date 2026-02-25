#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
填充所有聚类版本的数据到 village_cluster_assignments 表
"""

import sqlite3
import numpy as np
from sklearn.cluster import DBSCAN
import time

def populate_all_clustering_versions():
    """填充所有聚类版本的数据"""

    conn = sqlite3.connect('data/villages.db')
    cursor = conn.cursor()

    print("=" * 70)
    print("填充所有聚类版本的数据")
    print("=" * 70)

    # 1. 加载村庄坐标
    print("\n1. 加载村庄坐标...")
    cursor.execute('''
        SELECT ROWID, longitude, latitude
        FROM 广东省自然村_预处理
        WHERE longitude IS NOT NULL AND latitude IS NOT NULL
    ''')
    villages = cursor.fetchall()
    village_ids = ['v_' + str(v[0]) for v in villages]
    coords = np.array([[float(v[1]), float(v[2])] for v in villages])
    coords_rad = np.radians(coords)
    print(f"[OK] 加载了 {len(villages)} 个村庄")

    # 2. 为每个聚类版本生成数据
    clustering_configs = [
        ('spatial_eps_03', 0.03 / 6371.0, 5),
        ('spatial_eps_05', 0.05 / 6371.0, 5),
        ('spatial_eps_10', 0.10 / 6371.0, 5),
        ('spatial_eps_20', 20.0 / 6371.0, 5),
    ]

    for run_id, eps, min_samples in clustering_configs:
        print(f"\n处理 {run_id}...")

        # 运行 DBSCAN
        print(f"  运行 DBSCAN (eps={eps*6371:.2f}km, min_samples={min_samples})...")
        dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='haversine', n_jobs=-1)
        labels = dbscan.fit_predict(coords_rad)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        print(f"  聚类数: {n_clusters}, 噪声点: {n_noise}")

        # 删除旧数据
        cursor.execute('DELETE FROM village_cluster_assignments WHERE run_id = ?', (run_id,))

        # 插入新数据
        created_at = time.time()
        records = []
        for village_id, cluster_id in zip(village_ids, labels):
            if cluster_id >= 0:  # 只存储非噪声点
                records.append((run_id, village_id, int(cluster_id), created_at))

        cursor.executemany('''
            INSERT INTO village_cluster_assignments (run_id, village_id, cluster_id, created_at)
            VALUES (?, ?, ?, ?)
        ''', records)

        print(f"  [OK] 插入了 {len(records)} 条记录")

    # 3. HDBSCAN 版本（从现有数据读取）
    print(f"\n处理 spatial_hdbscan_v1...")
    print(f"  注意: HDBSCAN 数据需要单独运行脚本生成")
    print(f"  跳过...")

    conn.commit()
    conn.close()

    print("\n" + "=" * 70)
    print("完成！")
    print("=" * 70)

if __name__ == "__main__":
    populate_all_clustering_versions()
