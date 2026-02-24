#!/usr/bin/env python3
"""Check tables targeted for deletion and their row counts."""

import sqlite3
import os

db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [row[0] for row in cursor.fetchall()]

print(f"Total tables in database: {len(all_tables)}\n")

# Target tables for deletion (Phase 1)
target_tables = [
    'city_aggregates',
    'county_aggregates',
    'town_aggregates',
    'region_spatial_aggregates',
    'cluster_assignments',
    'cluster_profiles',
    'clustering_metrics'
]

print("=" * 70)
print("PHASE 1: Tables targeted for deletion")
print("=" * 70)

total_rows = 0
existing_tables = []

for table in target_tables:
    if table in all_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        total_rows += count
        existing_tables.append(table)
        print(f"[+] {table:40s} {count:>10,} rows")
    else:
        print(f"[-] {table:40s} {'NOT FOUND':>10s}")

print("-" * 70)
print(f"Total rows in existing target tables: {total_rows:,}")
print(f"Tables to delete: {len(existing_tables)}")

# Check all aggregation and clustering related tables
print("\n" + "=" * 70)
print("All aggregation/clustering tables in database:")
print("=" * 70)

agg_cluster_tables = []
for table in all_tables:
    if 'aggregate' in table.lower() or 'cluster' in table.lower():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        agg_cluster_tables.append((table, count))
        marker = "[*]" if table in target_tables else "   "
        print(f"{marker} {table:40s} {count:>10,} rows")

print(f"\nTotal aggregation/clustering tables: {len(agg_cluster_tables)}")

conn.close()
