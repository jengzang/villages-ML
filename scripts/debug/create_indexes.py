#!/usr/bin/env python3
"""
Create indexes to optimize real-time aggregation queries.
"""

import sqlite3
import time

db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"

print("=" * 70)
print("Creating Indexes for Real-time Aggregation Optimization")
print("=" * 70)
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List of indexes to create
indexes = [
    {
        "name": "idx_semantic_labels_village_run",
        "table": "semantic_labels",
        "columns": "(village_name, run_id)",
        "description": "Optimize JOIN with semantic_labels"
    },
    {
        "name": "idx_villages_city",
        "table": "广东省自然村",
        "columns": "(市级)",
        "description": "Optimize city-level GROUP BY"
    },
    {
        "name": "idx_villages_county",
        "table": "广东省自然村",
        "columns": "(区县级)",
        "description": "Optimize county-level GROUP BY"
    },
    {
        "name": "idx_villages_town",
        "table": "广东省自然村",
        "columns": "(乡镇级)",
        "description": "Optimize town-level GROUP BY"
    },
    {
        "name": "idx_spatial_features_village",
        "table": "village_spatial_features",
        "columns": "(village_name)",
        "description": "Optimize spatial aggregation JOIN"
    }
]

print("Indexes to create:")
for idx in indexes:
    print(f"  - {idx['name']}: {idx['description']}")
print()

created_count = 0
skipped_count = 0

for idx in indexes:
    print(f"Creating index: {idx['name']}...", end=" ")

    try:
        start_time = time.time()

        # Check if index already exists
        cursor.execute(f"""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='{idx['name']}'
        """)

        if cursor.fetchone():
            print("[SKIPPED - already exists]")
            skipped_count += 1
            continue

        # Create index
        sql = f"CREATE INDEX {idx['name']} ON {idx['table']} {idx['columns']}"
        cursor.execute(sql)
        conn.commit()

        elapsed = time.time() - start_time
        print(f"[OK] ({elapsed:.2f}s)")
        created_count += 1

    except Exception as e:
        print(f"[ERROR] {e}")

print()
print("=" * 70)
print(f"Index creation complete:")
print(f"  Created: {created_count}")
print(f"  Skipped: {skipped_count}")
print(f"  Total: {len(indexes)}")
print("=" * 70)

conn.close()
