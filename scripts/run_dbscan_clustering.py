#!/usr/bin/env python3
"""
DBSCAN村级聚类分析

使用DBSCAN（Density-Based Spatial Clustering of Applications with Noise）
进行村级聚类，主要优势：
1. 自动识别噪声点（异常村名）
2. 无需预先指定聚类数量
3. 可以发现任意形状的聚类
4. 基于密度的聚类，更符合地理分布特征

特征：
- 村名长度
- 后缀模式（suffix_1, suffix_2）
- 语义类别（山、水、方位、聚落、姓氏）
"""

import argparse
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import time
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_villages(db_path: str, limit: int = None) -> pd.DataFrame:
    """从数据库加载村庄数据"""
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM `广东省自然村`"

    if limit:
        query += f" LIMIT {limit}"

    df = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"Loaded {len(df)} villages")
    return df


def extract_village_features(df: pd.DataFrame) -> tuple:
    """提取村级特征

    特征包括：
    1. 村名长度
    2. 后缀特征（suffix_1, suffix_2）
    3. 语义特征（基于关键字匹配）

    Returns:
        (features_array, feature_names, valid_indices)
    """
    logger.info("Extracting village features...")

    features_list = []
    valid_indices = []

    for idx, row in df.iterrows():
        village_name = row['自然村']

        if pd.isna(village_name) or len(village_name) == 0:
            continue

        valid_indices.append(idx)

        # 基础特征
        features = {
            'name_length': len(village_name),
        }

        # 后缀特征
        if len(village_name) >= 1:
            features['suffix_1'] = village_name[-1]
        if len(village_name) >= 2:
            features['suffix_2'] = village_name[-2:]

        # 语义特征（关键字匹配）
        semantic_keywords = {
            'mountain': ['山', '岭', '坑', '岗', '峰', '坳'],
            'water': ['水', '河', '江', '湖', '塘', '涌', '沙', '洲'],
            'direction': ['东', '西', '南', '北', '中', '上', '下', '前', '后'],
            'settlement': ['村', '庄', '寨', '围', '堡', '屯'],
            'clan': ['陈', '李', '王', '张', '刘', '黄', '林', '吴', '周', '郑'],
        }

        for category, keywords in semantic_keywords.items():
            features[f'sem_{category}'] = int(any(kw in village_name for kw in keywords))

        features_list.append(features)

        if len(features_list) % 10000 == 0:
            logger.info(f"Processed {len(features_list)} villages...")

    logger.info(f"Extracted features for {len(features_list)} villages")

    # 转换为DataFrame
    features_df = pd.DataFrame(features_list)

    # 处理分类特征（后缀）- 使用独热编码
    suffix1_dummies = pd.get_dummies(features_df['suffix_1'], prefix='suf1')
    suffix2_dummies = pd.get_dummies(features_df['suffix_2'], prefix='suf2')

    # 只保留前50个最常见的后缀
    if len(suffix1_dummies.columns) > 50:
        suffix1_counts = suffix1_dummies.sum().sort_values(ascending=False)
        top_suffix1 = suffix1_counts.head(50).index
        suffix1_dummies = suffix1_dummies[top_suffix1]

    if len(suffix2_dummies.columns) > 50:
        suffix2_counts = suffix2_dummies.sum().sort_values(ascending=False)
        top_suffix2 = suffix2_counts.head(50).index
        suffix2_dummies = suffix2_dummies[top_suffix2]

    # 合并特征
    numeric_features = features_df[['name_length'] + [col for col in features_df.columns if col.startswith('sem_')]]
    final_features = pd.concat([numeric_features, suffix1_dummies, suffix2_dummies], axis=1)

    logger.info(f"Final feature matrix shape: {final_features.shape}")

    return final_features.values, final_features.columns.tolist(), valid_indices


def run_dbscan_clustering(
    X: np.ndarray,
    eps: float = 0.5,
    min_samples: int = 10,
    use_pca: bool = True,
    pca_components: int = 50,
    random_state: int = 42
):
    """运行DBSCAN聚类

    Args:
        X: 特征矩阵
        eps: 邻域半径（距离阈值）
        min_samples: 形成核心点所需的最小样本数
        use_pca: 是否使用PCA降维
        pca_components: PCA降维维度
        random_state: 随机种子

    Returns:
        labels, dbscan, scaler, pca
    """
    logger.info(f"Running DBSCAN clustering with eps={eps}, min_samples={min_samples}")
    logger.info(f"Input shape: {X.shape}")

    # 标准化
    logger.info("Standardizing features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA降维
    pca = None
    if use_pca and X.shape[1] > pca_components:
        logger.info(f"Applying PCA: {X.shape[1]} -> {pca_components} dimensions")
        pca = PCA(n_components=pca_components, random_state=random_state)
        X_processed = pca.fit_transform(X_scaled)
        logger.info(f"PCA explained variance: {pca.explained_variance_ratio_.sum():.3f}")
    else:
        X_processed = X_scaled

    # DBSCAN聚类
    logger.info(f"Running DBSCAN...")
    start_time = time.time()

    dbscan = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric='euclidean',
        n_jobs=-1  # 使用所有CPU核心
    )

    labels = dbscan.fit_predict(X_processed)

    elapsed = time.time() - start_time
    logger.info(f"Clustering completed in {elapsed:.2f}s")

    # 计算聚类统计
    unique, counts = np.unique(labels, return_counts=True)
    n_clusters = len(unique) - (1 if -1 in unique else 0)
    n_noise = counts[unique == -1][0] if -1 in unique else 0

    logger.info(f"Number of clusters: {n_clusters}")
    logger.info(f"Number of noise points: {n_noise} ({n_noise/len(labels)*100:.1f}%)")
    logger.info(f"Cluster distribution:")

    for cluster_id, count in zip(unique, counts):
        if cluster_id == -1:
            logger.info(f"  Noise: {count} villages ({count/len(labels)*100:.1f}%)")
        else:
            logger.info(f"  Cluster {cluster_id}: {count} villages ({count/len(labels)*100:.1f}%)")

    # 计算评估指标（排除噪声点）
    if n_clusters > 1:
        mask = labels != -1
        if mask.sum() > 0:
            try:
                sil_score = silhouette_score(X_processed[mask], labels[mask])
                db_score = davies_bouldin_score(X_processed[mask], labels[mask])
                logger.info(f"Silhouette Score (excluding noise): {sil_score:.4f}")
                logger.info(f"Davies-Bouldin Index (excluding noise): {db_score:.4f}")
            except Exception as e:
                logger.warning(f"Could not compute metrics: {e}")

    return labels, dbscan, scaler, pca


def analyze_noise_points(df_valid: pd.DataFrame, labels: np.ndarray, output_path: Path):
    """分析噪声点（异常村名）

    噪声点是DBSCAN识别出的不属于任何聚类的村庄，
    这些村庄通常具有独特或罕见的命名模式。
    """
    logger.info("Analyzing noise points...")

    noise_mask = labels == -1
    noise_villages = df_valid[noise_mask].copy()

    if len(noise_villages) == 0:
        logger.info("No noise points found")
        return

    logger.info(f"Found {len(noise_villages)} noise points")

    # 保存噪声点
    noise_villages.to_csv(output_path / 'noise_points.csv', index=False, encoding='utf-8-sig')
    logger.info(f"Saved noise points to {output_path / 'noise_points.csv'}")

    # 分析噪声点的特征
    logger.info("Noise point characteristics:")
    logger.info(f"  Average name length: {noise_villages['自然村'].str.len().mean():.2f}")

    # 噪声点的地理分布
    city_dist = noise_villages['市级'].value_counts().head(10)
    logger.info("  Top 10 cities with noise points:")
    for city, count in city_dist.items():
        logger.info(f"    {city}: {count}")


def main():
    parser = argparse.ArgumentParser(description='DBSCAN村级聚类分析')
    parser.add_argument('--db-path', default='data/villages.db', help='数据库路径')
    parser.add_argument('--output-dir', default='results/dbscan_clustering', help='输出目录')
    parser.add_argument('--eps', type=float, default=0.5, help='DBSCAN邻域半径')
    parser.add_argument('--min-samples', type=int, default=10, help='DBSCAN最小样本数')
    parser.add_argument('--limit', type=int, default=None, help='限制村庄数量（用于测试）')
    parser.add_argument('--pca-components', type=int, default=50, help='PCA降维维度')
    parser.add_argument('--random-state', type=int, default=42, help='随机种子')

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("DBSCAN村级聚类分析")
    logger.info("="*80)
    logger.info(f"Eps: {args.eps}")
    logger.info(f"Min samples: {args.min_samples}")
    logger.info(f"PCA components: {args.pca_components}")
    if args.limit:
        logger.info(f"Limit: {args.limit} villages (testing mode)")
    logger.info("="*80)

    # 加载数据
    df = load_villages(args.db_path, limit=args.limit)

    # 提取特征
    X, feature_names, valid_indices = extract_village_features(df)

    # 只保留有效的村庄
    df_valid = df.iloc[valid_indices].reset_index(drop=True)
    logger.info(f"Valid villages: {len(df_valid)} out of {len(df)}")

    # 运行DBSCAN聚类
    labels, dbscan, scaler, pca = run_dbscan_clustering(
        X,
        eps=args.eps,
        min_samples=args.min_samples,
        use_pca=True,
        pca_components=args.pca_components,
        random_state=args.random_state
    )

    # 保存结果
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存聚类标签
    df_valid['cluster_id'] = labels
    df_valid.to_csv(output_path / 'village_clusters_dbscan.csv', index=False, encoding='utf-8-sig')
    logger.info(f"Saved clustering results to {output_path / 'village_clusters_dbscan.csv'}")

    # 分析噪声点
    analyze_noise_points(df_valid, labels, output_path)

    # 保存聚类统计（排除噪声点）
    cluster_mask = labels != -1
    if cluster_mask.sum() > 0:
        cluster_stats = df_valid[cluster_mask].groupby('cluster_id').agg({
            '自然村': 'count',
            '市级': lambda x: x.mode()[0] if len(x.mode()) > 0 else None,
            '县区级': lambda x: x.mode()[0] if len(x.mode()) > 0 else None
        }).rename(columns={'自然村': 'village_count'})

        cluster_stats.to_csv(output_path / 'cluster_statistics.csv', encoding='utf-8-sig')
        logger.info(f"Saved cluster statistics to {output_path / 'cluster_statistics.csv'}")

    logger.info("="*80)
    logger.info("DBSCAN聚类完成！")
    logger.info(f"结果保存在: {args.output_dir}")
    logger.info("="*80)


if __name__ == '__main__':
    main()
