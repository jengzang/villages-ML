"""
Add indexes to optimized tables for API query performance.

This script creates indexes on the new merged tables to support fast API queries.
Without these indexes, API queries would require full table scans.
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def create_indexes(conn):
    """Create indexes on optimized tables."""
    cursor = conn.cursor()

    print("Creating indexes for char_regional_analysis...")

    # Primary key (if not exists)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_char_regional_pk
        ON char_regional_analysis(region_level, region_name, char)
    """)

    # Query by region
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_char_regional_region
        ON char_regional_analysis(region_level, region_name)
    """)

    # Query by character
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_char_regional_char
        ON char_regional_analysis(char)
    """)

    # Sort by lift (tendency analysis)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_char_regional_lift
        ON char_regional_analysis(region_level, region_name, lift DESC)
    """)

    # Filter by significance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_char_regional_significant
        ON char_regional_analysis(region_level, region_name, support_flag)
    """)

    print("Creating indexes for pattern_regional_analysis...")

    # Primary key (if not exists)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_regional_pk
        ON pattern_regional_analysis(pattern_type, region_level, region_name, pattern)
    """)

    # Query by region and type
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_regional_region
        ON pattern_regional_analysis(pattern_type, region_level, region_name)
    """)

    # Query by pattern
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_regional_pattern
        ON pattern_regional_analysis(pattern)
    """)

    # Sort by lift
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_regional_lift
        ON pattern_regional_analysis(pattern_type, region_level, region_name, lift DESC)
    """)

    print("Creating indexes for semantic_regional_analysis...")

    # Primary key (if not exists)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_regional_pk
        ON semantic_regional_analysis(region_level, region_name, category)
    """)

    # Query by region
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_regional_region
        ON semantic_regional_analysis(region_level, region_name)
    """)

    # Query by category
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_regional_category
        ON semantic_regional_analysis(category)
    """)

    # Sort by lift
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_regional_lift
        ON semantic_regional_analysis(region_level, region_name, lift DESC)
    """)

    print("Creating indexes for village_features...")

    # Query by city
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_village_features_city
        ON village_features(city)
    """)

    # Query by county
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_village_features_county
        ON village_features(county)
    """)

    # Query by town
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_village_features_town
        ON village_features(town)
    """)

    # Query by cluster (kmeans)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_village_features_kmeans_cluster
        ON village_features(kmeans_cluster_id)
    """)

    conn.commit()
    print("\nAll indexes created successfully!")


def verify_indexes(conn):
    """Verify indexes were created."""
    cursor = conn.cursor()

    tables = [
        'char_regional_analysis',
        'pattern_regional_analysis',
        'semantic_regional_analysis',
        'village_features'
    ]

    print("\nVerifying indexes...")
    print("=" * 80)

    for table in tables:
        cursor.execute(f'PRAGMA index_list({table})')
        indexes = cursor.fetchall()

        # Count non-primary-key indexes
        custom_indexes = [idx for idx in indexes if idx[3] != 'pk']

        print(f'{table:40} {len(custom_indexes)} custom indexes')


def main():
    db_path = project_root / 'data' / 'villages.db'
    print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        create_indexes(conn)
        verify_indexes(conn)

        print("\nIndexes created successfully!")
        print("\nThese indexes will support fast API queries:")
        print("  - Filter by region (city/county/town)")
        print("  - Filter by character/pattern/category")
        print("  - Sort by tendency (lift)")
        print("  - Filter by significance")

    except Exception as e:
        print(f"\nERROR: Failed to create indexes: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
