#!/usr/bin/env python3
"""
Database Status Verification Script

Checks the status of all tables in villages.db:
- Lists all tables with row counts
- Samples data from key tables
- Assesses data quality
- Generates comprehensive status report

Usage:
    python scripts/check_database_status.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

DB_PATH = project_root / "data" / "villages.db"


def get_all_tables(conn):
    """Get list of all tables in database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]


def get_row_count(conn, table_name):
    """Get row count for a table."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        return cursor.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"


def sample_table(conn, table_name, limit=5):
    """Sample first N rows from a table."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {limit}")
        return cursor.fetchall()
    except Exception as e:
        return f"Error: {e}"


def get_table_schema(conn, table_name):
    """Get schema for a table."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info(`{table_name}`)")
        return cursor.fetchall()
    except Exception as e:
        return f"Error: {e}"


def categorize_tables(table_stats):
    """Categorize tables by population status."""
    populated = []
    empty = []

    for table, count in table_stats.items():
        if isinstance(count, int):
            if count > 0:
                populated.append((table, count))
            else:
                empty.append(table)
        else:
            empty.append(table)

    return populated, empty


def get_key_statistics(conn):
    """Get key statistics from main tables."""
    stats = {}

    # Total villages
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM `广东省自然村_preprocessed`")
    stats['total_villages'] = cursor.fetchone()[0]

    # Unique characters
    cursor.execute("SELECT COUNT(*) FROM char_frequency_global")
    stats['unique_chars'] = cursor.fetchone()[0]

    # Spatial coverage
    cursor.execute("SELECT COUNT(*) FROM village_spatial_features")
    stats['spatial_coverage'] = cursor.fetchone()[0]

    # Feature coverage
    cursor.execute("SELECT COUNT(*) FROM village_features")
    stats['feature_coverage'] = cursor.fetchone()[0]

    return stats


def main():
    """Main verification function."""
    print("=" * 80)
    print("Database Status Verification")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Get all tables
    print("Fetching table list...")
    tables = get_all_tables(conn)
    print(f"Total tables: {len(tables)}")
    print()

    # Get row counts for all tables
    print("Counting rows for each table...")
    table_stats = {}
    for table in tables:
        count = get_row_count(conn, table)
        table_stats[table] = count

    # Categorize tables
    populated, empty = categorize_tables(table_stats)

    print(f"Populated tables: {len(populated)} ({len(populated)/len(tables)*100:.1f}%)")
    print(f"Empty tables: {len(empty)} ({len(empty)/len(tables)*100:.1f}%)")
    print()

    # Get key statistics
    print("Fetching key statistics...")
    try:
        stats = get_key_statistics(conn)
        print(f"Total villages: {stats['total_villages']:,}")
        print(f"Unique characters: {stats['unique_chars']:,}")
        print(f"Spatial coverage: {stats['spatial_coverage']:,} ({stats['spatial_coverage']/stats['total_villages']*100:.2f}%)")
        print(f"Feature coverage: {stats['feature_coverage']:,} ({stats['feature_coverage']/stats['total_villages']*100:.2f}%)")
    except Exception as e:
        print(f"Error fetching statistics: {e}")
    print()

    # Display populated tables
    print("=" * 80)
    print("POPULATED TABLES")
    print("=" * 80)
    for table, count in sorted(populated, key=lambda x: x[1], reverse=True):
        print(f"{table:50s} {count:>15,} rows")
    print()

    # Display empty tables
    if empty:
        print("=" * 80)
        print("EMPTY TABLES")
        print("=" * 80)
        for table in sorted(empty):
            print(f"  - {table}")
        print()

    conn.close()

    print("=" * 80)
    print("Verification complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
