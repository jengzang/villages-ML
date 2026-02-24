"""
Comprehensive database index audit tool.

Generates a report of all tables with their indexes, row counts, and identifies:
- Large tables (>10K rows) with no indexes
- Large tables with few indexes
- All tables missing indexes

Usage:
    python scripts/maintenance/audit_database_indexes.py
    python scripts/maintenance/audit_database_indexes.py --output report.txt
"""

import sqlite3
from pathlib import Path
from typing import Dict, List
import sys


def audit_database_indexes(db_path: str) -> Dict:
    """Generate comprehensive index audit report."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    report = {}

    for table in tables:
        # Get row count
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            row_count = cursor.fetchone()[0]
        except sqlite3.Error:
            row_count = -1

        # Get indexes
        cursor.execute(f'PRAGMA index_list("{table}")')
        indexes = cursor.fetchall()

        # Get index details
        index_details = []
        for idx in indexes:
            idx_name = idx[1]
            cursor.execute(f'PRAGMA index_info("{idx_name}")')
            columns = [col[2] for col in cursor.fetchall()]
            index_details.append({
                'name': idx_name,
                'columns': columns,
                'unique': bool(idx[2])
            })

        report[table] = {
            'row_count': row_count,
            'index_count': len(indexes),
            'indexes': index_details
        }

    conn.close()
    return report


def print_audit_report(report: Dict, output_file=None):
    """Print formatted audit report."""

    # Redirect output if needed
    if output_file:
        sys.stdout = open(output_file, 'w', encoding='utf-8')

    print("\n" + "="*80)
    print("DATABASE INDEX AUDIT REPORT")
    print("="*80)

    # Tables with no indexes (excluding PRIMARY KEY)
    no_indexes = []
    few_indexes = []
    large_no_indexes = []

    for table, info in sorted(report.items()):
        idx_count = info['index_count']
        row_count = info['row_count']

        # Count non-PK indexes
        non_pk_indexes = [idx for idx in info['indexes'] if not idx['name'].startswith('sqlite_autoindex')]
        non_pk_count = len(non_pk_indexes)

        if non_pk_count == 0 and row_count > 0:
            no_indexes.append((table, row_count))
            if row_count > 10000:
                large_no_indexes.append((table, row_count))
        elif non_pk_count > 0 and non_pk_count <= 2 and row_count > 10000:
            few_indexes.append((table, row_count, non_pk_count))

    print(f"\n[CRITICAL] Large tables (>10K rows) with NO indexes:")
    if large_no_indexes:
        for table, count in large_no_indexes:
            print(f"  - {table}: {count:,} rows, 0 indexes")
    else:
        print("  None found [OK]")

    print(f"\n[WARNING] Large tables (>10K rows) with FEW indexes (1-2):")
    if few_indexes:
        for table, count, idx_count in few_indexes:
            print(f"  - {table}: {count:,} rows, {idx_count} index(es)")
    else:
        print("  None found [OK]")

    print(f"\n[INFO] All tables with no indexes:")
    if no_indexes:
        for table, count in no_indexes:
            print(f"  - {table}: {count:,} rows")
    else:
        print("  None found [OK]")

    print(f"\n[SUMMARY]:")
    print(f"  Total tables: {len(report)}")
    print(f"  Tables with no indexes: {len(no_indexes)}")
    print(f"  Large tables needing indexes: {len(large_no_indexes)}")

    # Detailed table breakdown
    print(f"\n[DETAILED TABLE BREAKDOWN]:")
    print("="*80)

    for table, info in sorted(report.items(), key=lambda x: x[1]['row_count'], reverse=True):
        row_count = info['row_count']
        idx_count = info['index_count']
        non_pk_indexes = [idx for idx in info['indexes'] if not idx['name'].startswith('sqlite_autoindex')]

        print(f"\n{table}:")
        print(f"  Rows: {row_count:,}")
        print(f"  Total indexes: {idx_count}")
        print(f"  Non-PK indexes: {len(non_pk_indexes)}")

        if non_pk_indexes:
            print(f"  Indexes:")
            for idx in non_pk_indexes:
                cols = ', '.join(idx['columns'])
                unique = " (UNIQUE)" if idx['unique'] else ""
                print(f"    - {idx['name']}: {cols}{unique}")

    # Restore stdout
    if output_file:
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        print(f"\n[SUCCESS] Report saved to: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit database indexes")
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: print to console)"
    )
    args = parser.parse_args()

    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        exit(1)

    print(f"Auditing database: {db_path}")
    report = audit_database_indexes(str(db_path))
    print_audit_report(report, args.output)

    # Restore stdout
    if args.output:
        print(f"\n[SUCCESS] Report saved to: {args.output}")
