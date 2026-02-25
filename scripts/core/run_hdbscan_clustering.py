"""
生成 HDBSCAN 空间聚类

使用 HDBSCAN (Hierarchical DBSCAN) 对村庄进行空间聚类。
HDBSCAN 的优势是自动选择密度参数，可以同时处理不同密度的聚类。
"""

import sys
from pathlib import Path
import logging
import argparse
import numpy as np
import pandas as pd
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.spatial.coordinate_loader import CoordinateLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def delete_optimized_kde_v1(db_path: str):
    """删除重复的 optimized_kde_v1 数据"""
    logger.info("删除 optimized_kde_v1 重复数据...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ['spatial_clusters', 'village_spatial_features', 'spatial_hotspots', 'regional_aggregates']
    total_deleted = 0

    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table} WHERE run_id = 'optimized_kde_v1'")
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f'  {table}: 删除 {deleted} 条记录')
                total_deleted += deleted
        except Exception as e:
            logger.warning(f'  {table}: {e}')

    conn.commit()
    conn.close()

    logger.info(f"总计删除: {total_deleted} 条记录")


def run_hdbscan_clustering(
    coords: np.ndarray,
    coords_df: pd.DataFrame,
    min_cluster_size: int = 10,
    min_samples: int = 5
):
    """
    运行 HDBSCAN 聚类

    Args:
        coords: 坐标数组 (n_points, 2) [latitude, longitude]
        coords_df: 包含村庄信息的 DataFrame
        min_cluster_size: 最小聚类大小
        min_samples: 最小样本数

    Returns:
        labels: 聚类标签
        probabilities: 聚类概率
        clusterer: HDBSCAN 聚类器对象
    """
    try:
        import hdbscan
    except ImportError:
        logger.error("hdbscan 未安装。请运行: pip install hdbscan")
        sys.exit(1)

    logger.info(f"运行 HDBSCAN 聚类...")
    logger.info(f"  min_cluster_size: {min_cluster_size}")
    logger.info(f"  min_samples: {min_samples}")
    logger.info(f"  输入: {len(coords)} 个村庄")

    # 转换为弧度（用于球面距离计算）
    coords_rad = np.radians(coords)

    # HDBSCAN 聚类
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='haversine',  # 球面距离
        cluster_selection_method='eom',  # Excess of Mass
        core_dist_n_jobs=-1  # 使用所有 CPU 核心
    )

    labels = clusterer.fit_predict(coords_rad)
    probabilities = clusterer.probabilities_

    # 统计结果
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)

    logger.info(f"聚类完成:")
    logger.info(f"  - {n_clusters} 个聚类")
    logger.info(f"  - {n_noise} 个噪声点 ({n_noise/len(labels)*100:.1f}%)")

    return labels, probabilities, clusterer


def calculate_cluster_profiles(coords: np.ndarray, coords_df: pd.DataFrame, labels: np.ndarray):
    """计算聚类画像"""
    logger.info("计算聚类画像...")

    cluster_profiles = []

    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue  # 跳过噪声点

        mask = labels == cluster_id
        cluster_coords = coords[mask]
        cluster_df = coords_df[mask]

        # 计算中心点
        center_lat = cluster_coords[:, 0].mean()
        center_lon = cluster_coords[:, 1].mean()

        # 计算平均距离（到中心点）
        distances = np.sqrt(
            (cluster_coords[:, 0] - center_lat)**2 +
            (cluster_coords[:, 1] - center_lon)**2
        )
        avg_distance_deg = distances.mean()
        avg_distance_km = avg_distance_deg * 111  # 粗略转换

        # 获取主要区域
        city_mode = cluster_df['city'].mode()
        city = city_mode.iloc[0] if len(city_mode) > 0 else None

        county_mode = cluster_df['county'].mode()
        county = county_mode.iloc[0] if len(county_mode) > 0 else None

        cluster_profiles.append({
            'cluster_id': int(cluster_id),
            'cluster_size': int(mask.sum()),
            'centroid_lat': float(center_lat),
            'centroid_lon': float(center_lon),
            'avg_distance_km': float(avg_distance_km),
            'dominant_city': city,
            'dominant_county': county
        })

    logger.info(f"生成 {len(cluster_profiles)} 个聚类画像")

    return pd.DataFrame(cluster_profiles)


def write_results_to_db(
    db_path: str,
    run_id: str,
    coords_df: pd.DataFrame,
    labels: np.ndarray,
    probabilities: np.ndarray,
    cluster_profiles: pd.DataFrame
):
    """将结果写入数据库"""
    import time
    logger.info("写入结果到数据库...")

    conn = sqlite3.connect(db_path)

    # 1. 写入聚类画像
    cluster_profiles['run_id'] = run_id
    cluster_profiles['created_at'] = time.time()
    cluster_profiles.to_sql('spatial_clusters', conn, if_exists='append', index=False)
    logger.info(f"  写入 {len(cluster_profiles)} 个聚类画像")

    # 2. 写入村庄聚类分配到 village_cluster_assignments 表
    logger.info(f"  写入村庄聚类分配...")

    # 准备数据
    village_assignments = []
    created_at = time.time()

    for idx, (village_id, cluster_id, prob) in enumerate(zip(coords_df['village_id'], labels, probabilities)):
        if cluster_id >= 0:  # 只存储非噪声点
            # 获取聚类大小
            cluster_size = cluster_profiles[cluster_profiles['cluster_id'] == cluster_id]['cluster_size'].values
            cluster_size = int(cluster_size[0]) if len(cluster_size) > 0 else None

            village_assignments.append({
                'run_id': run_id,
                'village_id': village_id,
                'cluster_id': int(cluster_id),
                'cluster_size': cluster_size,
                'cluster_probability': float(prob),
                'created_at': created_at
            })

    # 删除旧数据（如果存在）
    cursor = conn.cursor()
    cursor.execute('DELETE FROM village_cluster_assignments WHERE run_id = ?', (run_id,))

    # 写入新数据
    if village_assignments:
        assignments_df = pd.DataFrame(village_assignments)
        assignments_df.to_sql('village_cluster_assignments', conn, if_exists='append', index=False)
        logger.info(f"  写入 {len(village_assignments)} 条村庄聚类分配")

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='运行 HDBSCAN 空间聚类',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--db-path',
        default='data/villages.db',
        help='数据库路径 (default: data/villages.db)'
    )
    parser.add_argument(
        '--run-id',
        default='spatial_hdbscan_v1',
        help='Run ID (default: spatial_hdbscan_v1)'
    )
    parser.add_argument(
        '--min-cluster-size',
        type=int,
        default=10,
        help='最小聚类大小 (default: 10)'
    )
    parser.add_argument(
        '--min-samples',
        type=int,
        default=5,
        help='最小样本数 (default: 5)'
    )
    parser.add_argument(
        '--delete-optimized-kde',
        action='store_true',
        help='删除 optimized_kde_v1 重复数据'
    )

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("HDBSCAN 空间聚类")
    logger.info("="*80)
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"min_cluster_size: {args.min_cluster_size}")
    logger.info(f"min_samples: {args.min_samples}")

    # 删除 optimized_kde_v1（如果指定）
    if args.delete_optimized_kde:
        delete_optimized_kde_v1(args.db_path)

    # 1. 加载坐标
    logger.info("\n" + "="*80)
    logger.info("Step 1: 加载坐标")
    logger.info("="*80)

    import sqlite3
    conn = sqlite3.connect(args.db_path)
    loader = CoordinateLoader()
    coords_df = loader.load_coordinates(conn)
    conn.close()

    coords = coords_df[['latitude', 'longitude']].values
    logger.info(f"加载 {len(coords)} 个村庄坐标")

    # 2. 运行 HDBSCAN 聚类
    logger.info("\n" + "="*80)
    logger.info("Step 2: 运行 HDBSCAN 聚类")
    logger.info("="*80)
    labels, probabilities, clusterer = run_hdbscan_clustering(
        coords, coords_df,
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples
    )

    # 3. 计算聚类画像
    logger.info("\n" + "="*80)
    logger.info("Step 3: 计算聚类画像")
    logger.info("="*80)
    cluster_profiles = calculate_cluster_profiles(coords, coords_df, labels)

    # 4. 写入数据库
    logger.info("\n" + "="*80)
    logger.info("Step 4: 写入数据库")
    logger.info("="*80)
    write_results_to_db(
        args.db_path,
        args.run_id,
        coords_df,
        labels,
        probabilities,
        cluster_profiles
    )

    # 5. 总结
    logger.info("\n" + "="*80)
    logger.info("完成")
    logger.info("="*80)
    n_clusters = len(cluster_profiles)
    n_noise = list(labels).count(-1)
    coverage = (len(labels) - n_noise) / len(labels) * 100

    logger.info(f"聚类数: {n_clusters}")
    logger.info(f"噪声点: {n_noise} ({n_noise/len(labels)*100:.1f}%)")
    logger.info(f"覆盖率: {coverage:.1f}%")
    logger.info(f"平均聚类大小: {cluster_profiles['cluster_size'].mean():.1f}")
    logger.info(f"最大聚类: {cluster_profiles['cluster_size'].max()}")
    logger.info(f"平均距离: {cluster_profiles['avg_distance_km'].mean():.2f} km")


if __name__ == '__main__':
    main()
