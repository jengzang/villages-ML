#!/usr/bin/env python3
"""Check the main village table schema - output to file."""

import sqlite3
import json

db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"
output_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\scripts\debug\table_schema.txt"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(广东省自然村)")
columns = cursor.fetchall()

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("Main table: 广东省自然村\n")
    f.write("=" * 70 + "\n")
    f.write(f"{'Index':<6} {'Name':<20} {'Type':<10} {'NotNull':<8} {'Default':<10} {'PK':<4}\n")
    f.write("-" * 70 + "\n")

    for col in columns:
        idx, name, type_, notnull, default, pk = col
        f.write(f"{idx:<6} {name:<20} {type_:<10} {notnull:<8} {str(default):<10} {pk:<4}\n")

    f.write(f"\nTotal columns: {len(columns)}\n")

    # Check a sample row
    cursor.execute("SELECT * FROM 广东省自然村 LIMIT 1")
    sample = cursor.fetchone()

    f.write("\n\nSample row:\n")
    f.write("-" * 70 + "\n")
    for col, val in zip(columns, sample):
        f.write(f"{col[1]}: {val}\n")

    # Check aggregation table structure
    f.write("\n\n" + "=" * 70 + "\n")
    f.write("city_aggregates table schema:\n")
    f.write("=" * 70 + "\n")

    cursor.execute("PRAGMA table_info(city_aggregates)")
    city_agg_cols = cursor.fetchall()

    for col in city_agg_cols:
        idx, name, type_, notnull, default, pk = col
        f.write(f"{idx:<6} {name:<30} {type_:<10}\n")

    # Sample data
    cursor.execute("SELECT * FROM city_aggregates LIMIT 1")
    sample_agg = cursor.fetchone()

    f.write("\nSample city_aggregates row:\n")
    f.write("-" * 70 + "\n")
    for col, val in zip(city_agg_cols, sample_agg):
        f.write(f"{col[1]}: {val}\n")

conn.close()

print(f"Schema written to: {output_path}")
