"""
Clean up old schema after migration to optimized schema.

WARNING: This script will DELETE old tables. Make sure:
1. Migration is complete and verified
2. New tables are working correctly
3. You have a backup of the database

This script removes:
- Old frequency tables (with run_id)
- Old tendency tables (with run_id)
- Redundant data (non-active run_ids)

Expected space savings: 3-4 GB
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def get_database_size(db_path):
    """Get database file size in GB."""
    size_bytes = db_path.stat().st_size
    size_gb = size_bytes / (1024 ** 3)
    return size_gb


def cleanup_old_tables(conn):
    """Remove old tables after migration."""
    cursor = conn.cursor()

    # Tables to remove (replaced by new merged tables)
    old_tables = [
        'char_frequency_regional',
        'regional_tendency',
        'pattern_frequency_regional',
        'pattern_tendency',
        'semantic_vtf_regional',
        'semantic_tendency',
        'char_frequency_global',
        'pattern_frequency_global',
        'semantic_vtf_global'
    ]

    print("Removing old tables...")
    for table in old_tables:
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if cursor.fetchone():
            print(f"  Dropping {table}...")
            cursor.execute(f'DROP TABLE {table}')
        else:
            print(f"  {table} does not exist, skipping")

    conn.commit()
    print("Old tables removed!")


def rename_new_tables(conn):
    """Rename _v2 tables to standard names."""
    cursor = conn.cursor()

    renames = [
        ('char_frequency_global_v2', 'char_frequency_global'),
        ('pattern_frequency_global_v2', 'pattern_frequency_global'),
        ('semantic_vtf_global_v2', 'semantic_vtf_global')
    ]

    print("\nRenaming new tables...")
    for old_name, new_name in renames:
        # Check if old table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (old_name,)
        )
        if cursor.fetchone():
            print(f"  Renaming {old_name} -> {new_name}...")
            cursor.execute(f'ALTER TABLE {old_name} RENAME TO {new_name}')
        else:
            print(f"  {old_name} does not exist, skipping")

    conn.commit()
    print("Tables renamed!")


def vacuum_database(conn):
    """Vacuum database to reclaim space."""
    print("\nVacuuming database to reclaim space...")
    print("  This may take several minutes...")
    conn.execute('VACUUM')
    print("  Vacuum complete!")


def verify_cleanup(conn):
    """Verify cleanup was successful."""
    print("\nVerifying cleanup...")

    cursor = conn.cursor()

    # Check old tables are gone
    old_tables = [
        'char_frequency_regional',
        'regional_tendency',
        'pattern_frequency_regional',
        'pattern_tendency'
    ]

    print("  Checking old tables removed:")
    for table in old_tables:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        exists = cursor.fetchone()
        status = "EXISTS (ERROR!)" if exists else "REMOVED (OK)"
        print(f"    {table:40} {status}")

    # Check new tables exist
    new_tables = [
        'char_regional_analysis',
        'pattern_regional_analysis',
        'semantic_regional_analysis',
        'char_frequency_global',
        'pattern_frequency_global',
        'semantic_vtf_global'
    ]

    print("\n  Checking new tables exist:")
    for table in new_tables:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        exists = cursor.fetchone()
        if exists:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"    {table:40} {count:>10,} rows")
        else:
            print(f"    {table:40} MISSING (ERROR!)")


def main():
    db_path = project_root / 'data' / 'villages.db'
    print(f"Database: {db_path}")

    # Get size before cleanup
    size_before = get_database_size(db_path)
    print(f"Size before cleanup: {size_before:.2f} GB")

    # Confirm with user
    print("\n" + "=" * 60)
    print("WARNING: This will DELETE old tables!")
    print("=" * 60)
    print("\nMake sure you have:")
    print("  1. Completed migration successfully")
    print("  2. Verified new tables are working")
    print("  3. Backed up the database")
    print("\nOld tables to be removed:")
    print("  - char_frequency_regional")
    print("  - regional_tendency")
    print("  - pattern_frequency_regional")
    print("  - pattern_tendency")
    print("  - semantic_vtf_regional")
    print("  - semantic_tendency")
    print("  - char_frequency_global (old)")
    print("  - pattern_frequency_global (old)")
    print("  - semantic_vtf_global (old)")

    response = input("\nProceed with cleanup? (yes/no): ")
    if response.lower() != 'yes':
        print("Cleanup cancelled.")
        return

    conn = sqlite3.connect(db_path)
    try:
        # Cleanup
        cleanup_old_tables(conn)
        rename_new_tables(conn)
        verify_cleanup(conn)

        # Vacuum to reclaim space
        vacuum_database(conn)

        print("\nCleanup completed successfully!")

    except Exception as e:
        print(f"\nERROR: Cleanup failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    # Get size after cleanup
    size_after = get_database_size(db_path)
    savings = size_before - size_after
    savings_pct = (savings / size_before) * 100

    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Size before: {size_before:.2f} GB")
    print(f"Size after:  {size_after:.2f} GB")
    print(f"Savings:     {savings:.2f} GB ({savings_pct:.1f}%)")
    print("=" * 60)


if __name__ == '__main__':
    main()
