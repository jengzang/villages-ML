#!/usr/bin/env python3
"""Check the main village table schema."""

import sqlite3

db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(广东省自然村)")
columns = cursor.fetchall()

print("Main table: 广东省自然村")
print("=" * 70)
print(f"{'Index':<6} {'Name':<20} {'Type':<10} {'NotNull':<8} {'Default':<10} {'PK':<4}")
print("-" * 70)

for col in columns:
    idx, name, type_, notnull, default, pk = col
    print(f"{idx:<6} {name:<20} {type_:<10} {notnull:<8} {str(default):<10} {pk:<4}")

print(f"\nTotal columns: {len(columns)}")

# Check a sample row
cursor.execute("SELECT * FROM 广东省自然村 LIMIT 1")
sample = cursor.fetchone()

print("\n\nSample row (first 5 columns):")
print("-" * 70)
for i, (col, val) in enumerate(zip(columns[:5], sample[:5])):
    print(f"{col[1]}: {val}")

conn.close()
