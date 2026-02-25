import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# 删除 optimized_kde_v1
cursor.execute("DELETE FROM spatial_clusters WHERE run_id = 'optimized_kde_v1'")
deleted = cursor.rowcount

cursor.execute("DELETE FROM village_spatial_features WHERE run_id = 'optimized_kde_v1'")
deleted_features = cursor.rowcount

cursor.execute("DELETE FROM spatial_hotspots WHERE run_id = 'optimized_kde_v1'")
deleted_hotspots = cursor.rowcount

conn.commit()

print(f'已删除 optimized_kde_v1:')
print(f'  spatial_clusters: {deleted} 条记录')
print(f'  village_spatial_features: {deleted_features} 条记录')
print(f'  spatial_hotspots: {deleted_hotspots} 条记录')

# 验证剩余数据
cursor.execute("SELECT run_id, COUNT(*) FROM spatial_clusters GROUP BY run_id")
print(f'\n剩余聚类数据:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} 条记录')

conn.close()
