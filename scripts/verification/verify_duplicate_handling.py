"""
Verify that duplicate place names are properly separated after fix.

This script verifies that:
1. Duplicate place names (like "太平镇") are properly separated into distinct records
2. Each record has correct hierarchical context (city, county, township)
3. Total village counts match the main table
"""

import sqlite3
from pathlib import Path


def verify_duplicate_handling(db_path: str):
    """Verify that duplicate place names are properly separated."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 80)
    print("DUPLICATE PLACE NAMES VERIFICATION")
    print("=" * 80)

    # Test case 1: 太平镇 should have 7 separate records
    print("\n1. Testing '太平镇' (should have 7 locations):")
    print("-" * 80)

    query = """
        SELECT city, county, township, region_name,
               SUM(total_villages) as total_villages
        FROM char_regional_analysis
        WHERE region_level = 'township' AND region_name = '太平镇'
        GROUP BY city, county, township, region_name
        ORDER BY total_villages DESC
    """

    try:
        results = cursor.execute(query).fetchall()

        if len(results) == 0:
            print("  ❌ FAIL: No records found for '太平镇'")
            print("  This might mean the data hasn't been regenerated yet.")
        else:
            print(f"  Found {len(results)} separate records for '太平镇':")
            total_sum = 0
            for row in results:
                city, county, township, region_name, villages = row
                print(f"    • {city} > {county} > {township}: {villages} villages")
                total_sum += villages

            print(f"\n  Total villages across all locations: {total_sum}")

            # Verify against main table
            main_query = """
                SELECT "市级", "区县级", "乡镇级", COUNT(*) as count
                FROM "广东省自然村"
                WHERE "乡镇级" = '太平镇'
                GROUP BY "市级", "区县级", "乡镇级"
                ORDER BY count DESC
            """

            main_results = cursor.execute(main_query).fetchall()

            print(f"\n  Main table has {len(main_results)} locations:")
            main_total = 0
            for row in main_results:
                city, county, township, count = row
                print(f"    • {city} > {county} > {township}: {count} villages")
                main_total += count

            print(f"\n  Total villages in main table: {main_total}")

            # Check if counts match
            if len(results) == len(main_results):
                print(f"\n  ✅ PASS: Record counts match ({len(results)} locations)")
            else:
                print(f"\n  ❌ FAIL: Record count mismatch ({len(results)} vs {len(main_results)})")

            if total_sum == main_total:
                print(f"  ✅ PASS: Village counts match ({total_sum} villages)")
            else:
                print(f"  ❌ FAIL: Village count mismatch ({total_sum} vs {main_total})")

    except sqlite3.OperationalError as e:
        print(f"  ❌ ERROR: {e}")
        print("  This likely means the table schema hasn't been updated yet.")

    # Test case 2: Check for other duplicate township names
    print("\n\n2. Checking for other duplicate township names:")
    print("-" * 80)

    duplicate_query = """
        SELECT "乡镇级", COUNT(DISTINCT "市级" || '|' || "区县级") as location_count
        FROM "广东省自然村"
        WHERE "乡镇级" IS NOT NULL AND "乡镇级" != ''
        GROUP BY "乡镇级"
        HAVING location_count > 1
        ORDER BY location_count DESC
        LIMIT 10
    """

    duplicate_results = cursor.execute(duplicate_query).fetchall()

    if duplicate_results:
        print(f"  Found {len(duplicate_results)} duplicate township names (showing top 10):")
        for township, count in duplicate_results:
            print(f"    • {township}: appears in {count} locations")

            # Check if properly separated in analysis table
            check_query = """
                SELECT COUNT(DISTINCT city || '|' || county || '|' || township) as separated_count
                FROM char_regional_analysis
                WHERE region_level = 'township' AND region_name = ?
            """
            try:
                separated_count = cursor.execute(check_query, (township,)).fetchone()[0]
                if separated_count == count:
                    print(f"      ✅ Properly separated ({separated_count} records)")
                elif separated_count == 0:
                    print(f"      ⚠️  No records in analysis table (data not generated yet)")
                else:
                    print(f"      ❌ Mismatch: {separated_count} records vs {count} locations")
            except sqlite3.OperationalError:
                print(f"      ⚠️  Cannot verify (schema not updated)")
    else:
        print("  No duplicate township names found.")

    # Test case 3: Verify hierarchical columns exist
    print("\n\n3. Verifying schema structure:")
    print("-" * 80)

    schema_query = "PRAGMA table_info(char_regional_analysis)"
    try:
        columns = cursor.execute(schema_query).fetchall()
        column_names = [col[1] for col in columns]

        required_columns = ['city', 'county', 'township', 'region_name']
        missing_columns = [col for col in required_columns if col not in column_names]

        if not missing_columns:
            print("  ✅ PASS: All hierarchical columns exist")
            print(f"  Columns: {', '.join(required_columns)}")
        else:
            print(f"  ❌ FAIL: Missing columns: {', '.join(missing_columns)}")
            print(f"  Current columns: {', '.join(column_names)}")

    except sqlite3.OperationalError as e:
        print(f"  ❌ ERROR: {e}")
        print("  Table might not exist yet.")

    conn.close()

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)


def main():
    # Get database path
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / 'data' / 'villages.db'

    print(f"Database: {db_path}")
    print(f"Database exists: {db_path.exists()}\n")

    if not db_path.exists():
        print("Error: Database file not found!")
        return

    verify_duplicate_handling(str(db_path))


if __name__ == '__main__':
    main()
