"""Clear village_semantic_structure table."""
import sqlite3

db_path = 'data/villages.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("DELETE FROM village_semantic_structure")
conn.commit()

print(f"[OK] Cleared village_semantic_structure table")

conn.close()
