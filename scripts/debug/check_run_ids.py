import sqlite3

conn = sqlite3.connect('data/villages.db')

# Check tendency run_ids
print('=== Tendency Run IDs (regional_tendency) ===')
try:
    cursor = conn.execute('SELECT DISTINCT run_id FROM regional_tendency LIMIT 5')
    for row in cursor:
        print(row[0])
except Exception as e:
    print(f"Error: {e}")

print('\n=== Spatial Run IDs (village_spatial_features) ===')
try:
    cursor = conn.execute('SELECT DISTINCT run_id FROM village_spatial_features LIMIT 5')
    for row in cursor:
        print(row[0])
except Exception as e:
    print(f"Error: {e}")

conn.close()
