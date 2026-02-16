#!/usr/bin/env python3
"""
层次聚类分析脚本

使用Ward方法进行层次聚类，生成树状图展示区域层次关系。
"""

import argparse
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from pathlib import Path
import json
import time
import logging

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_region_vectors(db_path: str, run_id: str) -> tuple:
    """从数据库加载区域特征向量"""
    conn = sqlite3.connect(db_path)

    query = """
    SELECT region_id, region_name, feature_json
    FROM region_vectors
    WHERE run_id = ?
    ORDER BY region_name
    """

    df = pd.read_sql_query(query, conn, params=(run_id,))
    conn.close()

    # 解析特征JSON
    features_list = []
    for feature_json in df['feature_json']:
        features = json.loads(feature_json)
        features_list.append(list(features.values()))

    X = np.array(features_list)
    region_names = df['region_name'].tolist()

    return X, region_names


def run_hierarchical_clustering(
    X: np.ndarray,
    region_names: list,
    method: str = 'ward',
    output_dir: str = 'results/hierarchical'
):
    """运行层次聚类并生成树状图"""

    logger.info(f"Running hierarchical clustering with method={method}")
    logger.info(f"Data shape: {X.shape}")

    # 计算链接矩阵
    start_time = time.time()
    linkage_matrix = linkage(X, method=method)
    elapsed = time.time() - start_time
    logger.info(f"Linkage computation completed in {elapsed:.2f}s")

    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存链接矩阵
    np.save(output_path / 'linkage_matrix.npy', linkage_matrix)
    logger.info(f"Saved linkage matrix to {output_path / 'linkage_matrix.npy'}")

    # 生成树状图
    plt.figure(figsize=(20, 10))
    dendrogram(
        linkage_matrix,
        labels=region_names,
        leaf_rotation=90,
        leaf_font_size=8
    )
    plt.title(f'层次聚类树状图 (method={method})', fontsize=16)
    plt.xlabel('区域', fontsize=12)
    plt.ylabel('距离', fontsize=12)
    plt.tight_layout()

    # 保存图片
    plt.savefig(output_path / 'dendrogram.png', dpi=300, bbox_inches='tight')
    logger.info(f"Saved dendrogram to {output_path / 'dendrogram.png'}")
    plt.close()

    # 在不同高度切割树，生成不同k值的聚类
    results = []
    for k in [4, 6, 8, 10, 12]:
        clusters = fcluster(linkage_matrix, k, criterion='maxclust')
        results.append({
            'k': k,
            'clusters': clusters.tolist()
        })
        logger.info(f"Generated {k} clusters")

    # 保存聚类结果
    results_df = pd.DataFrame({
        'region_name': region_names,
        **{f'cluster_k{r["k"]}': r['clusters'] for r in results}
    })
    results_df.to_csv(output_path / 'hierarchical_clusters.csv', index=False, encoding='utf-8-sig')
    logger.info(f"Saved clustering results to {output_path / 'hierarchical_clusters.csv'}")

    return linkage_matrix, results


def main():
    parser = argparse.ArgumentParser(description='层次聚类分析')
    parser.add_argument('--db-path', default='data/villages.db', help='数据库路径')
    parser.add_argument('--run-id', required=True, help='聚类运行ID（如cluster_001）')
    parser.add_argument('--method', default='ward',
                       choices=['ward', 'complete', 'average', 'single'],
                       help='链接方法')
    parser.add_argument('--output-dir', default='results/hierarchical',
                       help='输出目录')

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("层次聚类分析")
    logger.info("="*80)
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Method: {args.method}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info("="*80)

    # 加载数据
    logger.info("Loading region vectors...")
    X, region_names = load_region_vectors(args.db_path, args.run_id)
    logger.info(f"Loaded {len(region_names)} regions with {X.shape[1]} features")

    # 运行层次聚类
    linkage_matrix, results = run_hierarchical_clustering(
        X, region_names, args.method, args.output_dir
    )

    logger.info("="*80)
    logger.info("层次聚类完成！")
    logger.info(f"结果保存在: {args.output_dir}")
    logger.info("="*80)


if __name__ == '__main__':
    main()
