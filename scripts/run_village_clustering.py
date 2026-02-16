#!/usr/bin/env python3
"""
村级聚类分析

直接对200,000+个自然村进行聚类，而不是对县进行聚类。

特征：
- 村名字符（2-4个字）
- 语义类别（基于字符匹配）
- 后缀模式（suffix_1, suffix_2）
- 地理位置（可选）
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
from sklearn.cluster import MiniBatchKMeans
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_villages(db_path: str, limit: int = None) -> pd.DataFrame:
    """从数据库加载村庄数据"""
    conn = sqlite3.connect(db_path)

    # 使用SELECT *避免中文列名编码问题
    query = "SELECT * FROM `广东省自然村`"

    if limit:
        query += f" LIMIT {limit}"

    df = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"Loaded {len(df)} villages")
    logger.info(f"Columns: {df.columns.tolist()}")
    return df


def extract_village_features(df: pd.DataFrame) -> tuple:
    """提取村级特征

    特征包括：
    1. 村名长度
    2. 字符级特征（独热编码前100个高频字）
    3. 后缀特征（suffix_1, suffix_2）
    4. 语义特征（基于关键字匹配）

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

        if (len(features_list)) % 10000 == 0:
            logger.info(f"Processed {len(features_list)} villages...")

    logger.info(f"Extracted features for {len(features_list)} villages")

    # 转换为DataFrame
    features_df = pd.DataFrame(features_list)

    # 处理分类特征（后缀）
    # 使用独热编码
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


def run_village_clustering(
    X: np.ndarray,
    k: int = 50,
    use_pca: bool = True,
    pca_components: int = 50,
    batch_size: int = 10000,
    random_state: int = 42
):
    """运行村级聚类

    使用MiniBatchKMeans处理大规模数据
    """
    logger.info(f"Running village clustering with k={k}")
    logger.info(f"Input shape: {X.shape}")

    # 标准化
    logger.info("Standardizing features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA降维
    if use_pca and X.shape[1] > pca_components:
        logger.info(f"Applying PCA: {X.shape[1]} -> {pca_components} dimensions")
        pca = PCA(n_components=pca_components, random_state=random_state)
        X_processed = pca.fit_transform(X_scaled)
        logger.info(f"PCA explained variance: {pca.explained_variance_ratio_.sum():.3f}")
    else:
        X_processed = X_scaled

    # MiniBatchKMeans聚类
    logger.info(f"Running MiniBatchKMeans with k={k}, batch_size={batch_size}")
    start_time = time.time()

    kmeans = MiniBatchKMeans(
        n_clusters=k,
        batch_size=batch_size,
        random_state=random_state,
        max_iter=100,
        n_init=3,
        verbose=1
    )

    labels = kmeans.fit_predict(X_processed)

    elapsed = time.time() - start_time
    logger.info(f"Clustering completed in {elapsed:.2f}s")

    # 计算聚类统计
    unique, counts = np.unique(labels, return_counts=True)
    logger.info(f"Cluster distribution:")
    for cluster_id, count in zip(unique, counts):
        logger.info(f"  Cluster {cluster_id}: {count} villages ({count/len(labels)*100:.1f}%)")

    return labels, kmeans, scaler, pca if use_pca else None


def main():
    parser = argparse.ArgumentParser(description='村级聚类分析')
    parser.add_argument('--db-path', default='data/villages.db', help='数据库路径')
    parser.add_argument('--output-dir', default='results/village_clustering', help='输出目录')
    parser.add_argument('--k', type=int, default=50, help='聚类数量')
    parser.add_argument('--limit', type=int, default=None, help='限制村庄数量（用于测试）')
    parser.add_argument('--batch-size', type=int, default=10000, help='MiniBatchKMeans批次大小')
    parser.add_argument('--pca-components', type=int, default=50, help='PCA降维维度')
    parser.add_argument('--random-state', type=int, default=42, help='随机种子')

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("村级聚类分析")
    logger.info("="*80)
    logger.info(f"K: {args.k}")
    logger.info(f"Batch size: {args.batch_size}")
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

    # 运行聚类
    labels, kmeans, scaler, pca = run_village_clustering(
        X,
        k=args.k,
        use_pca=True,
        pca_components=args.pca_components,
        batch_size=args.batch_size,
        random_state=args.random_state
    )

    # 保存结果
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存聚类标签
    df_valid['cluster_id'] = labels
    df_valid.to_csv(output_path / 'village_clusters.csv', index=False, encoding='utf-8-sig')
    logger.info(f"Saved clustering results to {output_path / 'village_clusters.csv'}")

    # 保存聚类统计
    cluster_stats = df_valid.groupby('cluster_id').agg({
        '自然村': 'count',
        '市级': lambda x: x.mode()[0] if len(x.mode()) > 0 else None,
        '县区级': lambda x: x.mode()[0] if len(x.mode()) > 0 else None
    }).rename(columns={'自然村': 'village_count'})

    cluster_stats.to_csv(output_path / 'cluster_statistics.csv', encoding='utf-8-sig')
    logger.info(f"Saved cluster statistics to {output_path / 'cluster_statistics.csv'}")

    logger.info("="*80)
    logger.info("村级聚类完成！")
    logger.info(f"结果保存在: {args.output_dir}")
    logger.info("="*80)


if __name__ == '__main__':
    main()
