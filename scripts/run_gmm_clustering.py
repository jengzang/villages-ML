#!/usr/bin/env python3
"""
GMM村级聚类分析

使用GMM（Gaussian Mixture Models）进行村级聚类，主要优势：
1. 软聚类：提供每个村庄属于各聚类的概率分布
2. 不确定性量化：识别命名模式模糊的村庄
3. 灵活的聚类形状：可以建模椭圆形聚类
4. 概率基础：有明确的统计假设

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
from sklearn.mixture import GaussianMixture
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


def run_gmm_clustering(
    X: np.ndarray,
    n_components: int = 50,
    covariance_type: str = 'full',
    use_pca: bool = True,
    pca_components: int = 50,
    random_state: int = 42
):
    """运行GMM聚类

    Args:
        X: 特征矩阵
        n_components: 混合成分数量（类似于k）
        covariance_type: 协方差类型 ('full', 'tied', 'diag', 'spherical')
        use_pca: 是否使用PCA降维
        pca_components: PCA降维维度
        random_state: 随机种子

    Returns:
        labels, probabilities, gmm, scaler, pca
    """
    logger.info(f"Running GMM clustering with n_components={n_components}, covariance_type={covariance_type}")
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

    # GMM聚类
    logger.info(f"Running GMM...")
    start_time = time.time()

    gmm = GaussianMixture(
        n_components=n_components,
        covariance_type=covariance_type,
        n_init=10,
        random_state=random_state,
        verbose=1,
        max_iter=100
    )

    labels = gmm.fit_predict(X_processed)
    probabilities = gmm.predict_proba(X_processed)

    elapsed = time.time() - start_time
    logger.info(f"Clustering completed in {elapsed:.2f}s")

    # 计算聚类统计
    unique, counts = np.unique(labels, return_counts=True)
    logger.info(f"Number of components: {n_components}")
    logger.info(f"Cluster distribution:")

    for cluster_id, count in zip(unique, counts):
        logger.info(f"  Cluster {cluster_id}: {count} villages ({count/len(labels)*100:.1f}%)")

    # 计算评估指标
    try:
        sil_score = silhouette_score(X_processed, labels)
        db_score = davies_bouldin_score(X_processed, labels)
        logger.info(f"Silhouette Score: {sil_score:.4f}")
        logger.info(f"Davies-Bouldin Index: {db_score:.4f}")
        logger.info(f"BIC: {gmm.bic(X_processed):.2f}")
        logger.info(f"AIC: {gmm.aic(X_processed):.2f}")
    except Exception as e:
        logger.warning(f"Could not compute metrics: {e}")

    return labels, probabilities, gmm, scaler, pca


def analyze_uncertainty(df_valid: pd.DataFrame, probabilities: np.ndarray, labels: np.ndarray, output_path: Path):
    """分析聚类不确定性

    识别命名模式模糊的村庄（高熵、低最大概率）
    """
    logger.info("Analyzing clustering uncertainty...")

    # 计算每个村庄的最大概率
    max_probs = probabilities.max(axis=1)

    # 计算熵（不确定性度量）
    epsilon = 1e-10  # 避免log(0)
    entropy = -np.sum(probabilities * np.log(probabilities + epsilon), axis=1)

    # 添加到DataFrame
    df_valid['max_probability'] = max_probs
    df_valid['entropy'] = entropy

    # 识别高不确定性村庄（低最大概率或高熵）
    uncertain_mask = (max_probs < 0.5) | (entropy > 2.0)
    uncertain_villages = df_valid[uncertain_mask].copy()

    logger.info(f"Found {len(uncertain_villages)} uncertain villages ({len(uncertain_villages)/len(df_valid)*100:.1f}%)")

    if len(uncertain_villages) > 0:
        # 保存不确定村庄
        uncertain_villages_sorted = uncertain_villages.sort_values('entropy', ascending=False)
        uncertain_villages_sorted.to_csv(output_path / 'uncertain_villages.csv', index=False, encoding='utf-8-sig')
        logger.info(f"Saved uncertain villages to {output_path / 'uncertain_villages.csv'}")

        # 统计
        logger.info("Uncertainty statistics:")
        logger.info(f"  Average max probability: {max_probs.mean():.4f}")
        logger.info(f"  Average entropy: {entropy.mean():.4f}")
        logger.info(f"  Villages with max_prob < 0.5: {(max_probs < 0.5).sum()}")
        logger.info(f"  Villages with entropy > 2.0: {(entropy > 2.0).sum()}")


def main():
    parser = argparse.ArgumentParser(description='GMM村级聚类分析')
    parser.add_argument('--db-path', default='data/villages.db', help='数据库路径')
    parser.add_argument('--output-dir', default='results/gmm_clustering', help='输出目录')
    parser.add_argument('--n-components', type=int, default=50, help='GMM混合成分数量')
    parser.add_argument('--covariance-type', default='full', choices=['full', 'tied', 'diag', 'spherical'],
                        help='协方差类型')
    parser.add_argument('--limit', type=int, default=None, help='限制村庄数量（用于测试）')
    parser.add_argument('--pca-components', type=int, default=50, help='PCA降维维度')
    parser.add_argument('--random-state', type=int, default=42, help='随机种子')

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("GMM村级聚类分析")
    logger.info("="*80)
    logger.info(f"N components: {args.n_components}")
    logger.info(f"Covariance type: {args.covariance_type}")
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

    # 运行GMM聚类
    labels, probabilities, gmm, scaler, pca = run_gmm_clustering(
        X,
        n_components=args.n_components,
        covariance_type=args.covariance_type,
        use_pca=True,
        pca_components=args.pca_components,
        random_state=args.random_state
    )

    # 保存结果
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存聚类标签和概率
    df_valid['cluster_id'] = labels

    # 保存所有概率（作为JSON）
    prob_list = [probabilities[i].tolist() for i in range(len(probabilities))]
    df_valid['cluster_probabilities'] = [json.dumps(p) for p in prob_list]

    df_valid.to_csv(output_path / 'village_clusters_gmm.csv', index=False, encoding='utf-8-sig')
    logger.info(f"Saved clustering results to {output_path / 'village_clusters_gmm.csv'}")

    # 分析不确定性
    analyze_uncertainty(df_valid, probabilities, labels, output_path)

    # 保存聚类统计
    cluster_stats = df_valid.groupby('cluster_id').agg({
        '自然村': 'count',
        '市级': lambda x: x.mode()[0] if len(x.mode()) > 0 else None,
        '县区级': lambda x: x.mode()[0] if len(x.mode()) > 0 else None
    }).rename(columns={'自然村': 'village_count'})

    cluster_stats.to_csv(output_path / 'cluster_statistics.csv', encoding='utf-8-sig')
    logger.info(f"Saved cluster statistics to {output_path / 'cluster_statistics.csv'}")

    logger.info("="*80)
    logger.info("GMM聚类完成！")
    logger.info(f"结果保存在: {args.output_dir}")
    logger.info("="*80)


if __name__ == '__main__':
    main()
