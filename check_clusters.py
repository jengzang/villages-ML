import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# 检查 DBSCAN 聚类数
cursor.execute('''
    SELECT COUNT(DISTINCT cluster_id) as cluster_count
    FROM spatial_clusters
    WHERE run_id = 'spatial_eps_20'
''')
cluster_count = cursor.fetchone()[0]

# 检查 KDE 热点数
cursor.execute('''
    SELECT COUNT(*) as hotspot_count
    FROM spatial_hotspots
    WHERE run_id = 'spatial_eps_20'
''')
hotspot_count = cursor.fetchone()[0]

# 查看热点类型分布
cursor.execute('''
    SELECT hotspot_type, COUNT(*) as count
    FROM spatial_hotspots
    WHERE run_id = 'spatial_eps_20'
    GROUP BY hotspot_type
''')
hotspot_breakdown = cursor.fetchall()

print(f'DBSCAN 聚类数: {cluster_count}')
print(f'KDE 热点数: {hotspot_count}')
print(f'\n热点类型分布:')
for htype, count in hotspot_breakdown:
    print(f'  {htype}: {count}')

# 查看聚类大小分布
cursor.execute('''
    SELECT
        MIN(cluster_size) as min_size,
        MAX(cluster_size) as max_size,
        AVG(cluster_size) as avg_size,
        COUNT(*) as total_clusters
    FROM spatial_clusters
    WHERE run_id = 'spatial_eps_20'
''')
stats = cursor.fetchone()
print(f'\nDBSCAN 聚类统计:')
print(f'  最小聚类: {stats[0]} 个村庄')
print(f'  最大聚类: {stats[1]} 个村庄')
print(f'  平均聚类: {stats[2]:.1f} 个村庄')
print(f'  总聚类数: {stats[3]}')

# 查看热点大小分布
cursor.execute('''
    SELECT
        MIN(village_count) as min_count,
        MAX(village_count) as max_count,
        AVG(village_count) as avg_count,
        COUNT(*) as total_hotspots
    FROM spatial_hotspots
    WHERE run_id = 'spatial_eps_20'
''')
hotspot_stats = cursor.fetchone()
print(f'\nKDE 热点统计:')
print(f'  最小热点: {hotspot_stats[0]} 个村庄')
print(f'  最大热点: {hotspot_stats[1]} 个村庄')
print(f'  平均热点: {hotspot_stats[2]:.1f} 个村庄')
print(f'  总热点数: {hotspot_stats[3]}')

conn.close()
