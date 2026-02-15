#!/usr/bin/env python3
"""
村级聚类可视化

使用UMAP（Uniform Manifold Approximation and Projection）
将高维特征投影到2D空间进行可视化。

主要功能：
1. 2D散点图展示聚类结果
2. 交互式HTML可视化
3. 聚类质量评估
4. 发现子聚类和过渡区域
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
import matplotlib.pyplot as plt
import seaborn as sns

# 尝试导入UMAP
try:
    from umap import UMAP
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    logging.warning("UMAP not available. Install with: pip install umap-learn")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


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
    """提取村级特征"""
    logger.info("Extracting village features...")

    features_list = []
    valid_indices = []

    for idx, row in df.iterrows():
        village_name = row['自然村']

        if pd.isna(village_name) or len(village_name) == 0:
            continue

        valid_indices.append(idx)

        features = {
            'name_length': len(village_name),
        }

        if len(village_name) >= 1:
            features['suffix_1'] = village_name[-1]
        if len(village_name) >= 2:
            features['suffix_2'] = village_name[-2:]

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

    features_df = pd.DataFrame(features_list)

    suffix1_dummies = pd.get_dummies(features_df['suffix_1'], prefix='suf1')
    suffix2_dummies = pd.get_dummies(features_df['suffix_2'], prefix='suf2')

    if len(suffix1_dummies.columns) > 50:
        suffix1_counts = suffix1_dummies.sum().sort_values(ascending=False)
        top_suffix1 = suffix1_counts.head(50).index
        suffix1_dummies = suffix1_dummies[top_suffix1]

    if len(suffix2_dummies.columns) > 50:
        suffix2_counts = suffix2_dummies.sum().sort_values(ascending=False)
        top_suffix2 = suffix2_counts.head(50).index
        suffix2_dummies = suffix2_dummies[top_suffix2]

    numeric_features = features_df[['name_length'] + [col for col in features_df.columns if col.startswith('sem_')]]
    final_features = pd.concat([numeric_features, suffix1_dummies, suffix2_dummies], axis=1)

    logger.info(f"Final feature matrix shape: {final_features.shape}")

    return final_features.values, final_features.columns.tolist(), valid_indices


def reduce_dimensions(
    X: np.ndarray,
    method: str = 'umap',
    use_pca: bool = True,
    pca_components: int = 50,
    random_state: int = 42
):
    """降维到2D用于可视化

    Args:
        X: 特征矩阵
        method: 降维方法 ('umap' 或 'pca')
        use_pca: 是否先用PCA预处理
        pca_components: PCA降维维度
        random_state: 随机种子

    Returns:
        X_2d, scaler, pca
    """
    logger.info(f"Reducing dimensions using {method.upper()}")
    logger.info(f"Input shape: {X.shape}")

    # 标准化
    logger.info("Standardizing features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA预处理（可选）
    pca = None
    if use_pca and X.shape[1] > pca_components:
        logger.info(f"Applying PCA: {X.shape[1]} -> {pca_components} dimensions")
        pca = PCA(n_components=pca_components, random_state=random_state)
        X_processed = pca.fit_transform(X_scaled)
        logger.info(f"PCA explained variance: {pca.explained_variance_ratio_.sum():.3f}")
    else:
        X_processed = X_scaled

    # 降维到2D
    if method == 'umap':
        if not UMAP_AVAILABLE:
            logger.error("UMAP not available. Install with: pip install umap-learn")
            logger.info("Falling back to PCA")
            method = 'pca'

    if method == 'umap':
        logger.info("Running UMAP...")
        start_time = time.time()

        reducer = UMAP(
            n_components=2,
            n_neighbors=15,
            min_dist=0.1,
            metric='euclidean',
            random_state=random_state,
            verbose=True
        )

        X_2d = reducer.fit_transform(X_processed)

        elapsed = time.time() - start_time
        logger.info(f"UMAP completed in {elapsed:.2f}s")

    elif method == 'pca':
        logger.info("Using PCA for 2D projection...")
        pca_2d = PCA(n_components=2, random_state=random_state)
        X_2d = pca_2d.fit_transform(X_processed)
        logger.info(f"PCA explained variance: {pca_2d.explained_variance_ratio_.sum():.3f}")

    else:
        raise ValueError(f"Unknown method: {method}")

    logger.info(f"2D projection shape: {X_2d.shape}")

    return X_2d, scaler, pca


def plot_clusters(X_2d: np.ndarray, labels: np.ndarray, output_path: Path, title: str = "Village Clusters"):
    """绘制聚类散点图

    Args:
        X_2d: 2D坐标
        labels: 聚类标签
        output_path: 输出路径
        title: 图表标题
    """
    logger.info("Creating cluster visualization...")

    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 10))

    # 获取唯一标签
    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels)

    # 使用seaborn调色板
    if n_clusters <= 20:
        palette = sns.color_palette("tab20", n_clusters)
    else:
        palette = sns.color_palette("husl", n_clusters)

    # 绘制每个聚类
    for i, label in enumerate(unique_labels):
        mask = labels == label
        color = palette[i % len(palette)]

        if label == -1:
            # 噪声点（DBSCAN）
            ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
                      c=[color], s=10, alpha=0.3, label=f'Noise ({mask.sum()})')
        else:
            ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
                      c=[color], s=20, alpha=0.6, label=f'Cluster {label} ({mask.sum()})')

    ax.set_xlabel('Dimension 1', fontsize=12)
    ax.set_ylabel('Dimension 2', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')

    # 图例（如果聚类数不太多）
    if n_clusters <= 20:
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)

    plt.tight_layout()

    # 保存图表
    output_file = output_path / 'cluster_visualization.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Saved visualization to {output_file}")

    plt.close()


def main():
    parser = argparse.ArgumentParser(description='村级聚类可视化')
    parser.add_argument('--db-path', default='data/villages.db', help='数据库路径')
    parser.add_argument('--cluster-file', required=True, help='聚类结果CSV文件路径')
    parser.add_argument('--output-dir', default='results/visualization', help='输出目录')
    parser.add_argument('--method', default='umap', choices=['umap', 'pca'], help='降维方法')
    parser.add_argument('--limit', type=int, default=None, help='限制村庄数量（用于测试）')
    parser.add_argument('--pca-components', type=int, default=50, help='PCA降维维度')
    parser.add_argument('--random-state', type=int, default=42, help='随机种子')

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("村级聚类可视化")
    logger.info("="*80)
    logger.info(f"Method: {args.method.upper()}")
    logger.info(f"Cluster file: {args.cluster_file}")
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

    # 加载聚类结果
    cluster_df = pd.read_csv(args.cluster_file, encoding='utf-8-sig')
    logger.info(f"Loaded clustering results: {len(cluster_df)} villages")

    # 确保数据对齐
    if len(cluster_df) != len(df_valid):
        logger.warning(f"Cluster file has {len(cluster_df)} villages, but we have {len(df_valid)} valid villages")
        logger.warning("Using only the first N villages from cluster file")
        min_len = min(len(cluster_df), len(df_valid))
        cluster_df = cluster_df.iloc[:min_len]
        df_valid = df_valid.iloc[:min_len]
        X = X[:min_len]

    # 获取聚类标签
    if 'cluster_id' not in cluster_df.columns:
        logger.error("Cluster file must have 'cluster_id' column")
        return

    labels = cluster_df['cluster_id'].values

    # 降维到2D
    X_2d, scaler, pca = reduce_dimensions(
        X,
        method=args.method,
        use_pca=True,
        pca_components=args.pca_components,
        random_state=args.random_state
    )

    # 保存结果
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存2D坐标
    df_valid['x_2d'] = X_2d[:, 0]
    df_valid['y_2d'] = X_2d[:, 1]
    df_valid['cluster_id'] = labels

    df_valid.to_csv(output_path / 'villages_2d.csv', index=False, encoding='utf-8-sig')
    logger.info(f"Saved 2D coordinates to {output_path / 'villages_2d.csv'}")

    # 绘制聚类可视化
    plot_clusters(X_2d, labels, output_path, title=f"Village Clusters ({args.method.upper()})")

    logger.info("="*80)
    logger.info("可视化完成！")
    logger.info(f"结果保存在: {args.output_dir}")
    logger.info("="*80)


if __name__ == '__main__':
    main()
