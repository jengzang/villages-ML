import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# 比较两个 run_id 的数据
for run_id in ['optimized_kde_v1', 'spatial_eps_20']:
    cursor.execute('''
        SELECT
            COUNT(*) as total_clusters,
            SUM(cluster_size) as total_villages,
            AVG(cluster_size) as avg_size,
            MAX(cluster_size) as max_size,
            AVG(avg_distance_km) as avg_dist
        FROM spatial_clusters
        WHERE run_id = ?
    ''', (run_id,))

    result = cursor.fetchone()
    print(f'{run_id}:')
    print(f'  聚类数: {result[0]}')
    print(f'  村庄数: {result[1]}')
    print(f'  平均大小: {result[2]:.1f}')
    print(f'  最大聚类: {result[3]}')
    print(f'  平均距离: {result[4]:.2f} km')
    print()

# 检查是否是相同的数据
cursor.execute('''
    SELECT
        a.cluster_id,
        a.cluster_size as size_v1,
        b.cluster_size as size_eps20,
        ABS(a.center_lat - b.center_lat) as lat_diff,
        ABS(a.center_lon - b.center_lon) as lon_diff
    FROM spatial_clusters a
    INNER JOIN spatial_clusters b
        ON a.cluster_id = b.cluster_id
        AND b.run_id = 'spatial_eps_20'
    WHERE a.run_id = 'optimized_kde_v1'
    ORDER BY a.cluster_id
    LIMIT 10
''')

print('前10个聚类对比 (cluster_id 匹配):')
print('cluster_id | size_v1 | size_eps20 | lat_diff | lon_diff')
for row in cursor.fetchall():
    print(f'{row[0]:10} | {row[1]:7} | {row[2]:10} | {row[3]:.6f} | {row[4]:.6f}')

# 检查是否完全相同
cursor.execute('''
    SELECT COUNT(*)
    FROM spatial_clusters a
    INNER JOIN spatial_clusters b
        ON a.cluster_id = b.cluster_id
        AND a.cluster_size = b.cluster_size
        AND ABS(a.center_lat - b.center_lat) < 0.0001
        AND ABS(a.center_lon - b.center_lon) < 0.0001
        AND b.run_id = 'spatial_eps_20'
    WHERE a.run_id = 'optimized_kde_v1'
''')

identical_count = cursor.fetchone()[0]
print(f'\n完全相同的聚类数: {identical_count} / 253')

conn.close()
