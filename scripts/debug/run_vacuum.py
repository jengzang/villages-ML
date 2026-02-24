#!/usr/bin/env python3
"""
Run VACUUM to reclaim disk space after table deletion.
"""

import sqlite3
import os
from datetime import datetime

db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"

print("=" * 70)
print("Database VACUUM Operation")
print("=" * 70)
print(f"Database: {db_path}")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Check database size before
size_before = os.path.getsize(db_path) / (1024 * 1024)  # MB
print(f"Database size before VACUUM: {size_before:.2f} MB ({size_before/1024:.2f} GB)")
print()

# Connect and run VACUUM
print("Running VACUUM operation...")
print("This may take several minutes for large databases...")
print()

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Run VACUUM
    cursor.execute("VACUUM")
    conn.commit()

    print("[+] VACUUM completed successfully!")

    conn.close()

    # Check database size after
    size_after = os.path.getsize(db_path) / (1024 * 1024)  # MB
    space_saved = size_before - size_after

    print()
    print("=" * 70)
    print("VACUUM Results")
    print("=" * 70)
    print(f"Database size before: {size_before:.2f} MB ({size_before/1024:.2f} GB)")
    print(f"Database size after:  {size_after:.2f} MB ({size_after/1024:.2f} GB)")
    print(f"Space reclaimed:      {space_saved:.2f} MB ({space_saved/1024:.2f} GB)")
    print(f"Reduction:            {space_saved/size_before*100:.1f}%")
    print()
    print("[+] Operation completed successfully!")

except sqlite3.OperationalError as e:
    print(f"[-] VACUUM failed: {e}")
    print()
    print("Possible reasons:")
    print("  1. Insufficient disk space (VACUUM needs ~2x database size)")
    print("  2. Database is locked by another process")
    print("  3. File system limitations")
    print()
    print("The database is still functional, space will just not be reclaimed.")
    exit(1)

except Exception as e:
    print(f"[-] Unexpected error: {e}")
    exit(1)
