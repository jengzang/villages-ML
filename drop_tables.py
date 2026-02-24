"""Drop tables that need to be regenerated."""
import sqlite3

db_path = 'data/villages.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables_to_drop = [
    '广东省自然村_预处理',
    'village_ngrams',
    'village_semantic_structure',
    'village_features',
    'village_spatial_features'
]

print("Dropping tables...")
for table in tables_to_drop:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"[OK] Dropped: {table}")
    except Exception as e:
        print(f"[ERROR] Error dropping {table}: {e}")

conn.commit()
conn.close()
print("\nDone! Now run the generation scripts.")
