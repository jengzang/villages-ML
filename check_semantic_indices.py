"""Check semantic_indices table."""
import sqlite3

db_path = 'data/villages.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check semantic_indices table
cursor.execute("SELECT COUNT(*) FROM semantic_indices")
count = cursor.fetchone()[0]
print(f"[INFO] semantic_indices has {count:,} rows")

# Check schema
cursor.execute("PRAGMA table_info(semantic_indices)")
columns = cursor.fetchall()
print("\n[INFO] Schema:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# Show sample data
cursor.execute("SELECT * FROM semantic_indices LIMIT 10")
rows = cursor.fetchall()
print("\n[INFO] Sample data:")
for row in rows:
    print(f"  {row}")

conn.close()
