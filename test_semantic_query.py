"""Test semantic composition query."""
import sqlite3

db_path = 'data/villages.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Test the query used in phase14
cursor.execute("""
    SELECT village_id, 村委会, 自然村_去前缀
    FROM 广东省自然村_预处理
    WHERE 有效 = 1
    LIMIT 10
""")

rows = cursor.fetchall()
print(f"[INFO] Query returned {len(rows)} rows (showing first 10)")
for row in rows:
    print(f"  village_id={row[0]}, 村委会={row[1]}, 自然村_去前缀={row[2]}")

# Check total count
cursor.execute("""
    SELECT COUNT(*)
    FROM 广东省自然村_预处理
    WHERE 有效 = 1
""")
total = cursor.fetchone()[0]
print(f"\n[INFO] Total valid villages: {total:,}")

conn.close()
