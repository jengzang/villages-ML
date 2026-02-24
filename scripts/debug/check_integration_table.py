# -*- coding: utf-8 -*-
import sqlite3
import sys

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='spatial_tendency_integration'")
table_exists = cursor.fetchone()

if table_exists:
    print("[OK] Table 'spatial_tendency_integration' exists")

    # Check row count
    cursor.execute('SELECT COUNT(*) FROM spatial_tendency_integration')
    count = cursor.fetchone()[0]
    print(f"[OK] Row count: {count}")

    if count > 0:
        # Show sample data
        cursor.execute('SELECT * FROM spatial_tendency_integration LIMIT 5')
        rows = cursor.fetchall()

        # Get column names
        cursor.execute('PRAGMA table_info(spatial_tendency_integration)')
        columns = [row[1] for row in cursor.fetchall()]

        print(f"\n[OK] Columns: {', '.join(columns)}")
        print(f"\n[OK] Sample data (first 5 rows):")
        for row in rows:
            print(row)

        # Show character distribution
        cursor.execute('SELECT character, COUNT(*) as cluster_count FROM spatial_tendency_integration GROUP BY character')
        char_dist = cursor.fetchall()
        print(f"\n[OK] Character distribution:")
        for char, count in char_dist:
            print(f"  {char}: {count} clusters")
else:
    print("[ERROR] Table 'spatial_tendency_integration' does not exist")

conn.close()
