#!/usr/bin/env python3
"""
Comprehensive database comparison script.
Compares data/old/villages.db with data/villages.db
"""

import sqlite3
import sys

def main():
    print("=" * 100)
    print("DATABASE COMPREHENSIVE COMPARISON")
    print("=" * 100)
    print("OLD: data/old/villages.db (3.1 GB)")
    print("NEW: data/villages.db (2.5 GB)")
    print("=" * 100)

    # Connect to both databases
    conn_old = sqlite3.connect('data/old/villages.db')
    conn_new = sqlite3.connect('data/villages.db')

    cursor_old = conn_old.cursor()
    cursor_new = conn_new.cursor()

    # Get all tables from both databases
    tables_old = set([row[0] for row in cursor_old.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()])

    tables_new = set([row[0] for row in cursor_new.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()])

    # Tables only in old
    only_old = tables_old - tables_new
    # Tables only in new
    only_new = tables_new - tables_old
    # Common tables
    common = tables_old & tables_new

    print(f"\nTABLE SUMMARY:")
    print(f"  Old database: {len(tables_old)} tables")
    print(f"  New database: {len(tables_new)} tables")
    print(f"  Common tables: {len(common)}")
    print(f"  Only in OLD: {len(only_old)}")
    print(f"  Only in NEW: {len(only_new)}")

    if only_old:
        print(f"\nTables ONLY in OLD database:")
        for table in sorted(only_old):
            count = cursor_old.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            print(f"  - {table}: {count:,} rows")

    if only_new:
        print(f"\nTables ONLY in NEW database:")
        for table in sorted(only_new):
            count = cursor_new.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            print(f"  - {table}: {count:,} rows")

    print("\n" + "=" * 100)
    print("DETAILED TABLE COMPARISON")
    print("=" * 100)

    # Compare common tables
    changes = []
    no_changes = []

    for table in sorted(common):
        try:
            count_old = cursor_old.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            count_new = cursor_new.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

            diff = count_new - count_old
            if diff != 0:
                pct = (diff / count_old * 100) if count_old > 0 else 0
                changes.append((table, count_old, count_new, diff, pct))
            else:
                no_changes.append((table, count_old))
        except Exception as e:
            print(f"Error comparing {table}: {e}")

    # Sort by absolute difference
    changes.sort(key=lambda x: abs(x[3]), reverse=True)

    print(f"\nTABLES WITH CHANGES ({len(changes)} tables):")
    print(f"{'Table':<45} {'Old Rows':>15} {'New Rows':>15} {'Difference':>15} {'Change %':>10}")
    print("-" * 105)

    for table, old, new, diff, pct in changes:
        sign = '+' if diff > 0 else ''
        print(f"{table:<45} {old:>15,} {new:>15,} {sign}{diff:>14,} {pct:>9.1f}%")

    print(f"\nTABLES WITH NO CHANGES ({len(no_changes)} tables):")
    for table, count in no_changes:
        print(f"  {table}: {count:,} rows")

    # Detailed analysis for key tables
    print("\n" + "=" * 100)
    print("DETAILED CONTENT ANALYSIS - KEY TABLES")
    print("=" * 100)

    # Analyze ngram tables
    key_tables = ['ngram_significance', 'ngram_tendency', 'regional_ngram_frequency']

    for table in key_tables:
        if table in common:
            print(f"\n{table}:")
            print("-" * 80)

            # Check level distribution
            try:
                old_levels = cursor_old.execute(f'SELECT level, COUNT(*) FROM {table} GROUP BY level ORDER BY level').fetchall()
                new_levels = cursor_new.execute(f'SELECT level, COUNT(*) FROM {table} GROUP BY level ORDER BY level').fetchall()

                print(f"  Level distribution:")
                print(f"    {'Level':<15} {'Old Count':>15} {'New Count':>15} {'Difference':>15}")

                old_dict = {level: count for level, count in old_levels}
                new_dict = {level: count for level, count in new_levels}

                all_levels = sorted(set(old_dict.keys()) | set(new_dict.keys()))

                for level in all_levels:
                    old_count = old_dict.get(level, 0)
                    new_count = new_dict.get(level, 0)
                    diff = new_count - old_count
                    sign = '+' if diff > 0 else ''
                    print(f"    {level:<15} {old_count:>15,} {new_count:>15,} {sign}{diff:>14,}")
            except Exception as e:
                print(f"  Error analyzing levels: {e}")

    conn_old.close()
    conn_new.close()

    print("\n" + "=" * 100)
    print("COMPARISON COMPLETE")
    print("=" * 100)

if __name__ == '__main__':
    main()
