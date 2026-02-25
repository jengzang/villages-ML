#!/usr/bin/env python3
"""
监控空间聚类重新生成进度

Usage:
    python scripts/utils/monitor_spatial_clustering.py
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path


def check_progress(db_path: str = "data/villages.db"):
    """检查空间聚类生成进度"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取总村庄数
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村_预处理")
    total_villages = cursor.fetchone()[0]

    print("\n" + "=" * 80)
    print(f"Spatial Clustering Progress Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"Total villages in database: {total_villages:,}\n")

    # 检查目标 run_ids
    target_runs = ['spatial_eps_05', 'spatial_eps_10', 'spatial_eps_20']

    print("Target Run IDs Status:")
    print("-" * 80)
    print("Run ID          | Status    | Clusters | Villages | Coverage | Last Update")
    print("-" * 80)

    for run_id in target_runs:
        cursor.execute("""
            SELECT COUNT(*) as num_clusters,
                   SUM(cluster_size) as total_villages,
                   MAX(created_at) as last_update
            FROM spatial_clusters
            WHERE run_id = ?
        """, (run_id,))

        result = cursor.fetchone()

        if result and result[0] > 0:
            clusters, villages, last_update = result
            coverage = villages / total_villages * 100 if villages else 0

            if last_update:
                update_time = datetime.fromtimestamp(last_update).strftime('%H:%M:%S')
            else:
                update_time = 'N/A'

            # 检查是否是最近更新的（5分钟内）
            is_recent = last_update and (time.time() - last_update) < 300
            status = "Updating" if is_recent else "Complete"

            print(f"{run_id:15s} | {status:9s} | {clusters:>8,} | {villages:>8,} | {coverage:>6.1f}% | {update_time}")
        else:
            print(f"{run_id:15s} | Pending   |        - |        - |      - | -")

    # 检查所有 run_ids
    print("\n" + "=" * 80)
    print("All Spatial Clusters in Database:")
    print("-" * 80)

    cursor.execute("""
        SELECT run_id,
               COUNT(*) as num_clusters,
               SUM(cluster_size) as total_villages,
               AVG(avg_distance_km) as avg_distance,
               MAX(created_at) as last_update
        FROM spatial_clusters
        GROUP BY run_id
        ORDER BY last_update DESC
    """)

    print("Run ID          | Clusters | Villages | Coverage | Avg Dist | Last Update")
    print("-" * 80)

    for row in cursor.fetchall():
        run_id, clusters, villages, avg_dist, last_update = row
        coverage = villages / total_villages * 100

        if last_update:
            update_time = datetime.fromtimestamp(last_update).strftime('%m-%d %H:%M')
        else:
            update_time = 'N/A'

        print(f"{run_id:15s} | {clusters:>8,} | {villages:>8,} | {coverage:>6.1f}% | {avg_dist:>6.2f} km | {update_time}")

    conn.close()

    print("=" * 80)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor spatial clustering progress")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch mode (refresh every 30s)")
    parser.add_argument("--interval", "-i", type=int, default=30, help="Refresh interval in seconds (default: 30)")

    args = parser.parse_args()

    if args.watch:
        print("Watch mode enabled. Press Ctrl+C to exit.")
        try:
            while True:
                check_progress()
                print(f"\nRefreshing in {args.interval} seconds...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
    else:
        check_progress()


if __name__ == "__main__":
    main()
