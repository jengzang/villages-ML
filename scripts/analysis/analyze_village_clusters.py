#!/usr/bin/env python3
"""分析村级聚类结果"""

import pandas as pd

# 读取聚类结果
df = pd.read_csv('results/village_clustering_full/village_clusters.csv', encoding='utf-8-sig')

print(f"总村数: {len(df)}")
print(f"聚类数: {df['cluster_id'].nunique()}")
print()

# 分析每个聚类的特征
print("="*80)
print("各聚类示例村名")
print("="*80)

# 选择几个有代表性的聚类
sample_clusters = [1, 16, 17, 44, 41, 4, 5, 12]

for cluster_id in sample_clusters:
    cluster_df = df[df['cluster_id'] == cluster_id]
    print(f"\nCluster {cluster_id} ({len(cluster_df)}个村, {len(cluster_df)/len(df)*100:.1f}%):")
    print("示例村名:", cluster_df['自然村'].head(15).tolist())

    # 统计后缀
    suffixes = cluster_df['自然村'].apply(lambda x: x[-1] if pd.notna(x) and len(x) > 0 else '')
    suffix_counts = suffixes.value_counts().head(5)
    print("主要后缀:", dict(suffix_counts))

    # 统计地区分布
    city_counts = cluster_df['市级'].value_counts().head(3)
    print("主要地区:", dict(city_counts))

print("\n" + "="*80)
print("聚类规模分布")
print("="*80)
cluster_sizes = df['cluster_id'].value_counts().sort_index()
print(cluster_sizes)
