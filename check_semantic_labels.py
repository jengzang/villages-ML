"""Check semantic labels data."""
import sqlite3

db_path = 'data/villages.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if semantic_labels table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_labels'")
table_exists = cursor.fetchone()

if table_exists:
    print("[OK] semantic_labels table exists")

    # Check row count
    cursor.execute("SELECT COUNT(*) FROM semantic_labels")
    count = cursor.fetchone()[0]
    print(f"[INFO] semantic_labels has {count:,} rows")

    # Show sample data
    cursor.execute("SELECT * FROM semantic_labels LIMIT 5")
    rows = cursor.fetchall()
    print("\n[INFO] Sample data:")
    for row in rows:
        print(f"  {row}")
else:
    print("[ERROR] semantic_labels table does not exist!")
    print("\n[INFO] Available tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")

conn.close()
