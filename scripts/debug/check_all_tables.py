# -*- coding: utf-8 -*-
import sqlite3
import sys

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print(f"Total tables: {len(tables)}")
print("=" * 80)

# Check row count for each table
empty_tables = []
populated_tables = []

for table in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = cursor.fetchone()[0]
        status = "[OK]" if count > 0 else "[EMPTY]"
        print(f"{status} {table:40s} {count:>10,} rows")

        if count == 0:
            empty_tables.append(table)
        else:
            populated_tables.append((table, count))
    except Exception as e:
        print(f"[ERROR] {table:40s} {str(e)}")

print("=" * 80)
print(f"\nSummary:")
print(f"  Populated tables: {len(populated_tables)}/{len(tables)}")
print(f"  Empty tables: {len(empty_tables)}/{len(tables)}")

if empty_tables:
    print(f"\nEmpty tables:")
    for table in empty_tables:
        print(f"  - {table}")
else:
    print(f"\n[SUCCESS] All {len(tables)} tables are populated!")

# Highlight the three key tables
print(f"\nKey tables status:")
key_tables = ['semantic_indices', 'village_ngrams', 'spatial_tendency_integration']
for table in key_tables:
    if table in [t[0] for t in populated_tables]:
        count = next(c for t, c in populated_tables if t == table)
        print(f"  [OK] {table}: {count:,} rows")
    else:
        print(f"  [EMPTY] {table}: 0 rows")

conn.close()
