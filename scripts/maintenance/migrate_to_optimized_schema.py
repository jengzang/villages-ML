"""
Migrate data from old schema (with run_id) to new optimized schema.

This script:
1. Reads active run_ids from active_run_ids table
2. Migrates only active version data to new tables
3. Merges frequency + tendency data into single tables
4. Removes run_id columns

Expected space savings: 3-4 GB (60-70% reduction)
"""

import sqlite3
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def get_active_run_id(conn, analysis_type):
    """Get active run_id for an analysis type."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT run_id FROM active_run_ids WHERE analysis_type = ?",
        (analysis_type,)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    return None


def migrate_char_regional_analysis(conn):
    """Migrate char_frequency_regional + regional_tendency -> char_regional_analysis."""
    print("\nMigrating character regional analysis...")

    # Get active run_id
    run_id = get_active_run_id(conn, 'char_frequency')
    if not run_id:
        print("  WARNING: No active run_id for char_frequency, skipping")
        return

    print(f"  Using run_id: {run_id}")

    # Read data from regional_tendency (has all columns)
    query = f"""
        SELECT
            region_level,
            region_name,
            char,
            village_count,
            total_villages,
            frequency,
            rank_within_region,
            global_village_count,
            global_frequency,
            lift,
            log_lift,
            log_odds,
            z_score,
            support_flag,
            rank_overrepresented,
            rank_underrepresented
        FROM regional_tendency
        WHERE run_id = ?
    """

    df = pd.read_sql_query(query, conn, params=(run_id,))
    print(f"  Read {len(df):,} rows from regional_tendency")

    # Write to new table
    df.to_sql('char_regional_analysis', conn, if_exists='replace', index=False)
    print(f"  Wrote {len(df):,} rows to char_regional_analysis")


def migrate_pattern_regional_analysis(conn):
    """Migrate pattern_frequency_regional + pattern_tendency -> pattern_regional_analysis."""
    print("\nMigrating pattern regional analysis...")

    # Get active run_id
    run_id = get_active_run_id(conn, 'patterns')
    if not run_id:
        print("  WARNING: No active run_id for patterns, skipping")
        return

    print(f"  Using run_id: {run_id}")

    # Read data from pattern_tendency (has all columns)
    query = f"""
        SELECT
            pattern_type,
            region_level,
            region_name,
            pattern,
            village_count,
            total_villages,
            frequency,
            rank_within_region,
            global_village_count,
            global_frequency,
            lift,
            log_lift,
            log_odds,
            z_score,
            support_flag,
            rank_overrepresented,
            rank_underrepresented
        FROM pattern_tendency
        WHERE run_id = ?
    """

    df = pd.read_sql_query(query, conn, params=(run_id,))
    print(f"  Read {len(df):,} rows from pattern_tendency")

    # Write to new table
    df.to_sql('pattern_regional_analysis', conn, if_exists='replace', index=False)
    print(f"  Wrote {len(df):,} rows to pattern_regional_analysis")


def migrate_semantic_regional_analysis(conn):
    """Migrate semantic_vtf_regional + semantic_tendency -> semantic_regional_analysis."""
    print("\nMigrating semantic regional analysis...")

    # Get active run_id
    run_id = get_active_run_id(conn, 'semantic')
    if not run_id:
        print("  WARNING: No active run_id for semantic, skipping")
        return

    print(f"  Using run_id: {run_id}")

    # Read data from semantic_tendency (has most columns)
    # Need to merge with semantic_vtf_regional for rank_within_region
    query = f"""
        SELECT
            t.region_level,
            t.region_name,
            t.category,
            t.vtf_count,
            t.total_villages,
            t.frequency,
            v.rank_within_region,
            t.vtf_count as global_vtf_count,
            t.global_frequency,
            t.lift,
            t.log_lift,
            t.log_odds,
            t.z_score,
            t.support_flag,
            NULL as rank_overrepresented,
            NULL as rank_underrepresented
        FROM semantic_tendency t
        LEFT JOIN semantic_vtf_regional v
            ON t.region_level = v.region_level
            AND t.region_name = v.region_name
            AND t.category = v.category
            AND v.run_id = ?
        WHERE t.run_id = ?
    """

    df = pd.read_sql_query(query, conn, params=(run_id, run_id))
    print(f"  Read {len(df):,} rows from semantic_tendency")

    # Write to new table
    df.to_sql('semantic_regional_analysis', conn, if_exists='replace', index=False)
    print(f"  Wrote {len(df):,} rows to semantic_regional_analysis")


def migrate_global_tables(conn):
    """Migrate global frequency tables (remove run_id)."""
    print("\nMigrating global frequency tables...")

    # 1. Character global
    run_id = get_active_run_id(conn, 'char_frequency')
    if run_id:
        print(f"  Migrating char_frequency_global (run_id: {run_id})...")
        query = """
            SELECT char, village_count, total_villages, frequency, rank
            FROM char_frequency_global
            WHERE run_id = ?
        """
        df = pd.read_sql_query(query, conn, params=(run_id,))
        df.to_sql('char_frequency_global_v2', conn, if_exists='replace', index=False)
        print(f"    Wrote {len(df):,} rows")

    # 2. Pattern global
    run_id = get_active_run_id(conn, 'patterns')
    if run_id:
        print(f"  Migrating pattern_frequency_global (run_id: {run_id})...")
        query = """
            SELECT pattern_type, pattern, village_count, total_villages, frequency, rank
            FROM pattern_frequency_global
            WHERE run_id = ?
        """
        df = pd.read_sql_query(query, conn, params=(run_id,))
        df.to_sql('pattern_frequency_global_v2', conn, if_exists='replace', index=False)
        print(f"    Wrote {len(df):,} rows")

    # 3. Semantic global
    run_id = get_active_run_id(conn, 'semantic')
    if run_id:
        print(f"  Migrating semantic_vtf_global (run_id: {run_id})...")
        query = """
            SELECT category, vtf_count, total_villages, frequency, rank
            FROM semantic_vtf_global
            WHERE run_id = ?
        """
        df = pd.read_sql_query(query, conn, params=(run_id,))
        df.to_sql('semantic_vtf_global_v2', conn, if_exists='replace', index=False)
        print(f"    Wrote {len(df):,} rows")


def verify_migration(conn):
    """Verify migration was successful."""
    print("\nVerifying migration...")

    cursor = conn.cursor()

    tables = [
        'char_regional_analysis',
        'pattern_regional_analysis',
        'semantic_regional_analysis',
        'char_frequency_global_v2',
        'pattern_frequency_global_v2',
        'semantic_vtf_global_v2'
    ]

    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f"  {table:40} {count:>10,} rows")


def main():
    db_path = project_root / 'data' / 'villages.db'
    print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        # Migrate data
        migrate_char_regional_analysis(conn)
        migrate_pattern_regional_analysis(conn)
        migrate_semantic_regional_analysis(conn)
        migrate_global_tables(conn)

        # Verify
        verify_migration(conn)

        conn.commit()
        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\nNext steps:")
    print("1. Update analysis scripts to write to new tables")
    print("2. Update API to query new tables")
    print("3. Test thoroughly")
    print("4. Run cleanup_old_schema.py to remove old tables")


if __name__ == '__main__':
    main()
