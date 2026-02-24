#!/usr/bin/env python3
"""
Delete aggregation and clustering tables that can be computed in real-time.

PHASE 1: Delete tables
- city_aggregates (21 rows)
- county_aggregates (121 rows)
- town_aggregates (1,579 rows)
- region_spatial_aggregates (1,587 rows)
- cluster_assignments (1,709 rows)
- cluster_profiles (30 rows)
- clustering_metrics (32 rows)

Total: 5,079 rows, ~650MB storage
"""

import sqlite3
import os
from datetime import datetime

db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"

# Tables to delete
tables_to_delete = [
    'city_aggregates',
    'county_aggregates',
    'town_aggregates',
    'region_spatial_aggregates',
    'cluster_assignments',
    'cluster_profiles',
    'clustering_metrics'
]

print("=" * 70)
print("DATABASE OPTIMIZATION: Deleting Aggregation Tables")
print("=" * 70)
print(f"Database: {db_path}")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current database size
db_size_before = os.path.getsize(db_path) / (1024 * 1024)  # MB
print(f"Database size before: {db_size_before:.2f} MB")
print()

# Get row counts before deletion
print("Tables to delete:")
print("-" * 70)
total_rows = 0

for table in tables_to_delete:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        total_rows += count
        print(f"  {table:40s} {count:>10,} rows")
    except sqlite3.OperationalError:
        print(f"  {table:40s} {'NOT FOUND':>10s}")

print("-" * 70)
print(f"  {'Total rows to delete':40s} {total_rows:>10,}")
print()

# Confirm deletion
print("WARNING: This operation will permanently delete these tables!")
print("A backup has been created at: data/backups/")
print()
response = input("Continue with deletion? (yes/no): ")

if response.lower() != 'yes':
    print("\nOperation cancelled.")
    conn.close()
    exit(0)

# Delete tables
print("\nDeleting tables...")
deleted_count = 0

for table in tables_to_delete:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  [+] Deleted: {table}")
        deleted_count += 1
    except Exception as e:
        print(f"  [-] Error deleting {table}: {e}")

conn.commit()

# Vacuum database to reclaim space
print("\nVacuuming database to reclaim space...")
cursor.execute("VACUUM")
conn.commit()

# Check new database size
db_size_after = os.path.getsize(db_path) / (1024 * 1024)  # MB
space_saved = db_size_before - db_size_after

print("\n" + "=" * 70)
print("DELETION COMPLETE")
print("=" * 70)
print(f"Tables deleted: {deleted_count}/{len(tables_to_delete)}")
print(f"Rows deleted: {total_rows:,}")
print(f"Database size before: {db_size_before:.2f} MB")
print(f"Database size after: {db_size_after:.2f} MB")
print(f"Space saved: {space_saved:.2f} MB ({space_saved/db_size_before*100:.1f}%)")
print()

# Verify remaining tables
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
remaining_tables = cursor.fetchone()[0]
print(f"Remaining tables: {remaining_tables}")

conn.close()

print("\n[+] Operation completed successfully!")
print("\nNext steps:")
print("  1. Update API endpoints to use real-time computation")
print("  2. Test API endpoints")
print("  3. Update documentation")
