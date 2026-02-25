import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# 删除 optimized_kde_v1 的所有相关数据
tables = ['spatial_clusters', 'village_spatial_features', 'spatial_hotspots', 'regional_aggregates']
total_deleted = 0

for table in tables:
    try:
        cursor.execute(f"DELETE FROM {table} WHERE run_id = 'optimized_kde_v1'")
        deleted = cursor.rowcount
        if deleted > 0:
            print(f'{table}: 删除 {deleted} 条记录')
            total_deleted += deleted
    except Exception as e:
        print(f'{table}: {e}')

conn.commit()
print(f'\n总计删除: {total_deleted} 条记录')

# 验证删除结果
cursor.execute("SELECT run_id, COUNT(*) FROM spatial_clusters GROUP BY run_id ORDER BY run_id")
print(f'\n剩余 spatial_clusters 数据:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} 条记录')

conn.close()
print('\n✓ 删除完成')
