"""
Create optimized database schema without run_id redundancy.

This script creates new merged tables that combine frequency + tendency data
and removes run_id columns (version management via active_run_ids table instead).

New tables:
- char_regional_analysis (merges char_frequency_regional + regional_tendency)
- pattern_regional_analysis (merges pattern_frequency_regional + pattern_tendency)
- semantic_regional_analysis (merges semantic_vtf_regional + semantic_tendency)
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def create_optimized_tables(conn):
    """Create new optimized table schemas."""
    cursor = conn.cursor()

    # 1. Character Regional Analysis (merged frequency + tendency)
    print("Creating char_regional_analysis...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS char_regional_analysis (
            region_level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region_name TEXT NOT NULL,
            char TEXT NOT NULL,
            -- Frequency data
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            -- Tendency data
            global_village_count INTEGER NOT NULL,
            global_frequency REAL NOT NULL,
            lift REAL NOT NULL,
            log_lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL,
            support_flag INTEGER NOT NULL,
            rank_overrepresented INTEGER,
            rank_underrepresented INTEGER,
            PRIMARY KEY (region_level, city, county, township, char)
        )
    """)

    # 2. Pattern Regional Analysis (merged frequency + tendency)
    print("Creating pattern_regional_analysis...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_regional_analysis (
            pattern_type TEXT NOT NULL,
            region_level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region_name TEXT NOT NULL,
            pattern TEXT NOT NULL,
            -- Frequency data
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            -- Tendency data
            global_village_count INTEGER NOT NULL,
            global_frequency REAL NOT NULL,
            lift REAL NOT NULL,
            log_lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL,
            support_flag INTEGER NOT NULL,
            rank_overrepresented INTEGER,
            rank_underrepresented INTEGER,
            PRIMARY KEY (pattern_type, region_level, city, county, township, pattern)
        )
    """)

    # 3. Semantic Regional Analysis (merged vtf + tendency)
    print("Creating semantic_regional_analysis...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_regional_analysis (
            region_level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region_name TEXT NOT NULL,
            category TEXT NOT NULL,
            -- VTF data
            vtf_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            -- Tendency data
            global_vtf_count INTEGER NOT NULL,
            global_frequency REAL NOT NULL,
            lift REAL NOT NULL,
            log_lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL,
            support_flag INTEGER NOT NULL,
            rank_overrepresented INTEGER,
            rank_underrepresented INTEGER,
            PRIMARY KEY (region_level, city, county, township, category)
        )
    """)

    # 4. Update global tables (remove run_id)
    print("Creating char_frequency_global_v2...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS char_frequency_global_v2 (
            char TEXT PRIMARY KEY,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank INTEGER NOT NULL
        )
    """)

    print("Creating pattern_frequency_global_v2...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_frequency_global_v2 (
            pattern_type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank INTEGER NOT NULL,
            PRIMARY KEY (pattern_type, pattern)
        )
    """)

    print("Creating semantic_vtf_global_v2...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_vtf_global_v2 (
            category TEXT PRIMARY KEY,
            vtf_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank INTEGER NOT NULL
        )
    """)

    conn.commit()
    print("All optimized tables created successfully!")


def main():
    db_path = project_root / 'data' / 'villages.db'
    print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        create_optimized_tables(conn)
    finally:
        conn.close()

    print("\nOptimized schema created!")
    print("\nNext steps:")
    print("1. Run migrate_to_optimized_schema.py to migrate data")
    print("2. Update analysis scripts to use new tables")
    print("3. Update API to query new tables")
    print("4. Run cleanup_old_schema.py to remove old tables")


if __name__ == '__main__':
    main()

