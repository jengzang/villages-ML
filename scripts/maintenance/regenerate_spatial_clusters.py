#!/usr/bin/env python3
"""
重新生成空间聚类 - 优化的 eps 参数

新的参数配置:
- spatial_eps_05: 0.5 km (超密集核心聚类)
- spatial_eps_10: 1.0 km (标准密度聚类) ⭐ 推荐
- spatial_eps_20: 2.0 km (全域覆盖聚类)

旧参数问题:
- eps_03 (0.3 km): 覆盖率太低 (24.2%)
- eps_05 (0.5 km): 还算合理 (58.8%)
- eps_10 (1.0 km): 聚类太粗 (92.0%)

新参数优势:
- 更合理的参数间隔 (0.5 → 1.0 → 2.0)
- 更好的覆盖率分布 (~60% → ~90% → ~98%)
- 更清晰的使用场景定位
"""

import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_spatial_clustering(run_id: str, eps_km: float, min_samples: int = 5):
    """
    运行空间聚类分析

    Args:
        run_id: 运行标识
        eps_km: DBSCAN epsilon 参数（公里）
        min_samples: DBSCAN min_samples 参数
    """
    logger.info("=" * 70)
    logger.info(f"Running spatial clustering: {run_id}")
    logger.info(f"Parameters: eps={eps_km} km, min_samples={min_samples}")
    logger.info("=" * 70)

    cmd = [
        "python",
        "scripts/core/run_spatial_analysis.py",
        "--run-id", run_id,
        "--eps-km", str(eps_km),
        "--min-samples", str(min_samples),
        "--db-path", "data/villages.db"
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"✓ {run_id} completed successfully")
        logger.info(result.stdout)

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ {run_id} failed")
        logger.error(f"Error: {e.stderr}")
        return False


def verify_results(db_path: str = "data/villages.db"):
    """验证生成的聚类结果"""
    import sqlite3

    logger.info("\n" + "=" * 70)
    logger.info("Verifying Results")
    logger.info("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询新生成的聚类
    cursor.execute("""
        SELECT run_id,
               COUNT(*) as num_clusters,
               SUM(cluster_size) as total_villages,
               AVG(cluster_size) as avg_size,
               MIN(cluster_size) as min_size,
               MAX(cluster_size) as max_size,
               AVG(avg_distance_km) as avg_distance
        FROM spatial_clusters
        WHERE run_id IN ('spatial_eps_05', 'spatial_eps_10', 'spatial_eps_20')
        GROUP BY run_id
        ORDER BY run_id
    """)

    results = cursor.fetchall()

    if not results:
        logger.warning("No results found for new run_ids")
        conn.close()
        return False

    # 获取总村庄数
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村_预处理")
    total_villages = cursor.fetchone()[0]

    logger.info(f"\nTotal villages in database: {total_villages:,}\n")
    logger.info("Run ID          | Clusters | Villages | Coverage | Avg Size | Avg Dist")
    logger.info("-" * 80)

    for row in results:
        run_id, num_clusters, villages, avg_size, min_size, max_size, avg_dist = row
        coverage = villages / total_villages * 100
        logger.info(
            f"{run_id:15s} | {num_clusters:>8,} | {villages:>8,} | {coverage:>6.1f}% | "
            f"{avg_size:>8.1f} | {avg_dist:>6.2f} km"
        )

    conn.close()
    return True


def cleanup_old_runs(db_path: str = "data/villages.db"):
    """
    清理旧的聚类结果（可选）

    删除 spatial_eps_03 的数据，因为它覆盖率太低不实用
    """
    import sqlite3

    logger.info("\n" + "=" * 70)
    logger.info("Cleanup Old Runs (Optional)")
    logger.info("=" * 70)

    response = input("\nDo you want to delete old spatial_eps_03 data? (y/N): ")

    if response.lower() != 'y':
        logger.info("Skipping cleanup")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 删除 spatial_eps_03
    cursor.execute("DELETE FROM spatial_clusters WHERE run_id = 'spatial_eps_03'")
    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    logger.info(f"✓ Deleted {deleted} clusters from spatial_eps_03")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Regenerate spatial clusters with optimized parameters")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old spatial_eps_03 data")
    args = parser.parse_args()

    logger.info("\n" + "=" * 70)
    logger.info("Regenerate Spatial Clusters with Optimized Parameters")
    logger.info("=" * 70)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    # 配置参数
    configs = [
        {
            "run_id": "spatial_eps_05",
            "eps_km": 0.5,
            "min_samples": 5,
            "description": "超密集核心聚类 (Ultra-dense Core Clusters)"
        },
        {
            "run_id": "spatial_eps_10",
            "eps_km": 1.0,
            "min_samples": 5,
            "description": "标准密度聚类 (Standard Density Clusters) ⭐"
        },
        {
            "run_id": "spatial_eps_20",
            "eps_km": 2.0,
            "min_samples": 5,
            "description": "全域覆盖聚类 (Full Coverage Clusters)"
        }
    ]

    logger.info("\nConfigurations:")
    for config in configs:
        logger.info(f"  {config['run_id']:20s} - eps={config['eps_km']} km - {config['description']}")

    # 确认执行
    if not args.yes:
        response = input("\nProceed with clustering? (y/N): ")
        if response.lower() != 'y':
            logger.info("Aborted by user")
            return

    # 运行聚类
    success_count = 0
    for config in configs:
        success = run_spatial_clustering(
            run_id=config["run_id"],
            eps_km=config["eps_km"],
            min_samples=config["min_samples"]
        )

        if success:
            success_count += 1

    # 验证结果
    if success_count > 0:
        verify_results()

    # 清理旧数据（可选）
    if args.cleanup:
        cleanup_old_runs()

    # 完成
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("\n" + "=" * 70)
    logger.info("Regeneration Complete!")
    logger.info("=" * 70)
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logger.info(f"Successful runs: {success_count}/{len(configs)}")

    if success_count == len(configs):
        logger.info("\n✓ All clustering runs completed successfully!")
        logger.info("\nNext steps:")
        logger.info("  1. Update API documentation with new parameters")
        logger.info("  2. Update active_run_ids if needed")
        logger.info("  3. Test API endpoints with new run_ids")
    else:
        logger.warning(f"\n⚠ Only {success_count}/{len(configs)} runs succeeded")
        logger.warning("Please check the logs for errors")


if __name__ == "__main__":
    main()
