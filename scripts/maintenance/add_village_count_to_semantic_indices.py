#!/usr/bin/env python3
"""
Add village_count column to semantic_indices table.

This script:
1. Adds village_count column to semantic_indices
2. Calculates village count for each region
3. Creates index for fast filtering
4. Validates the results

Backend requirement: Support min_villages parameter for fast filtering.
Expected performance improvement: 2000x (21s → 10ms)
"""

import sqlite3
from datetime import datetime


def step1_add_column(db_path: str):
    """Step 1: Add village_count column."""
    print("\n" + "="*70)
    print("Step 1: Adding village_count Column")
    print("="*70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(semantic_indices)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'village_count' in columns:
        print("[INFO] Column 'village_count' already exists, skipping...")
        conn.close()
        return

    # Add column
    print("Adding village_count column...")
    cursor.execute("""
        ALTER TABLE semantic_indices
        ADD COLUMN village_count INTEGER
    """)

    conn.commit()
    conn.close()
    print("[OK] Column added successfully")


def step2_calculate_village_counts(db_path: str):
    """Step 2: Calculate village count for each region."""
    print("\n" + "="*70)
    print("Step 2: Calculating Village Counts")
    print("="*70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all unique regions from semantic_indices
    cursor.execute("""
        SELECT DISTINCT region_level, region_name
        FROM semantic_indices
        ORDER BY region_level, region_name
    """)
    regions = cursor.fetchall()

    print(f"Processing {len(regions)} regions...")

    # Get column indices for the preprocessed table
    cursor.execute("PRAGMA table_info(广东省自然村_预处理)")
    columns = cursor.fetchall()

    # Find column indices (0=市级, 1=区县级, 2=乡镇级)
    level_column_index = {
        'city': 0,      # 市级
        'county': 1,    # 区县级
        'township': 2   # 乡镇级
    }

    updated_count = 0

    for idx, (region_level, region_name) in enumerate(regions, 1):
        if idx % 100 == 0:
            print(f"  Progress: {idx}/{len(regions)}")

        # Get column index for this level
        col_idx = level_column_index.get(region_level)

        if col_idx is None:
            print(f"  [WARNING] Unknown region_level: {region_level}")
            continue

        # Build query using column index
        # Use the actual column name from the table
        col_name = columns[col_idx][1]

        # Count villages in this region using village_id (unique identifier)
        query = f"""
            SELECT COUNT(DISTINCT village_id)
            FROM 广东省自然村_预处理
            WHERE "{col_name}" = ?
        """

        cursor.execute(query, (region_name,))
        village_count = cursor.fetchone()[0]

        # Update semantic_indices
        cursor.execute("""
            UPDATE semantic_indices
            SET village_count = ?
            WHERE region_level = ? AND region_name = ?
        """, (village_count, region_level, region_name))

        updated_count += cursor.rowcount

        if idx % 100 == 0:
            conn.commit()

    conn.commit()

    print(f"\n[OK] Updated {updated_count} records")

    # Show statistics
    cursor.execute("""
        SELECT region_level,
               COUNT(*) as region_count,
               MIN(village_count) as min_villages,
               MAX(village_count) as max_villages,
               AVG(village_count) as avg_villages
        FROM semantic_indices
        GROUP BY region_level
    """)

    print("\nVillage count statistics by level:")
    for level, count, min_v, max_v, avg_v in cursor.fetchall():
        print(f"  {level}:")
        print(f"    Regions: {count}")
        print(f"    Villages: min={min_v}, max={max_v}, avg={avg_v:.1f}")

    conn.close()


def step3_create_index(db_path: str):
    """Step 3: Create index on village_count."""
    print("\n" + "="*70)
    print("Step 3: Creating Index")
    print("="*70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if index already exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_semantic_indices_village_count'
    """)

    if cursor.fetchone():
        print("[INFO] Index already exists, skipping...")
        conn.close()
        return

    print("Creating index on village_count...")
    cursor.execute("""
        CREATE INDEX idx_semantic_indices_village_count
        ON semantic_indices(village_count)
    """)

    conn.commit()
    conn.close()
    print("[OK] Index created successfully")


def step4_validate(db_path: str):
    """Step 4: Validate the results."""
    print("\n" + "="*70)
    print("Step 4: Validation")
    print("="*70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check 1: All records have village_count
    cursor.execute("""
        SELECT COUNT(*)
        FROM semantic_indices
        WHERE village_count IS NULL
    """)
    null_count = cursor.fetchone()[0]

    if null_count == 0:
        print("[PASS] All records have village_count")
    else:
        print(f"[FAIL] Found {null_count} records with NULL village_count")
        return False

    # Check 2: All village_count > 0
    cursor.execute("""
        SELECT COUNT(*)
        FROM semantic_indices
        WHERE village_count <= 0
    """)
    zero_count = cursor.fetchone()[0]

    if zero_count == 0:
        print("[PASS] All village_count > 0")
    else:
        print(f"[WARNING] Found {zero_count} records with village_count <= 0")

    # Check 3: Verify a few samples
    print("\nSample verification:")
    cursor.execute("""
        SELECT region_level, region_name, village_count
        FROM semantic_indices
        WHERE category = '水系'
        ORDER BY village_count DESC
        LIMIT 5
    """)

    for level, name, count in cursor.fetchall():
        print(f"  {level:10s} {name:20s} {count:6,} villages")

    # Check 4: Index exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_semantic_indices_village_count'
    """)

    if cursor.fetchone():
        print("\n[PASS] Index exists")
    else:
        print("\n[FAIL] Index not found")
        return False

    conn.close()
    return True


def main():
    """Main execution function."""
    db_path = 'data/villages.db'

    print("\n" + "="*70)
    print("Add village_count Column to semantic_indices")
    print("="*70)
    print(f"Database: {db_path}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    try:
        step1_add_column(db_path)
        step2_calculate_village_counts(db_path)
        step3_create_index(db_path)
        success = step4_validate(db_path)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*70)
        if success:
            print("Operation Complete!")
        else:
            print("Operation Complete with Warnings")
        print("="*70)
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds")
        print("\nChanges:")
        print("  - Added village_count column to semantic_indices")
        print("  - Calculated village counts for all regions")
        print("  - Created index for fast filtering")
        print("\nExpected performance improvement: 2000x (21s → 10ms)")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
