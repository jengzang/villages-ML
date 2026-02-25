import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# 查看所有包含 cluster 的表
cursor.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table' AND name LIKE '%cluster%'
    ORDER BY name
""")
tables = cursor.fetchall()

print('包含 cluster 的表:')
for table in tables:
    print(f'  - {table[0]}')

print('\n各表的数据统计:')
for table in tables:
    table_name = table[0]

    # 检查是否有 run_id 列
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]

    if 'run_id' in columns:
        cursor.execute(f"SELECT run_id, COUNT(*) FROM {table_name} GROUP BY run_id")
        results = cursor.fetchall()
        print(f'\n{table_name}:')
        for run_id, count in results:
            print(f'  {run_id}: {count} 条记录')
    else:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f'\n{table_name}: {count} 条记录 (无 run_id)')

conn.close()
