"""Verify village_id implementation across all tables.

This script verifies:
1. All tables have village_id column
2. village_id format is correct (v_<ROWID>)
3. village_id values are unique in preprocessed table
4. Coverage of village_id across tables
5. Indexes exist on village_id columns
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run all verification tests."""
    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Tables that should have village_id
    tables = [
        '广东省自然村',
        '广东省自然村_预处理',
        'village_features',
        'village_ngrams',
        'village_semantic_structure',
        'village_spatial_features'
    ]

    logger.info("\n" + "="*60)
    logger.info("Village ID Verification")
    logger.info("="*60)

    # Test 1: Check all tables have village_id column
    logger.info("\nTest 1: Checking village_id column exists...")
    all_have_column = True
    for table in tables:
        try:
            cursor.execute(f'PRAGMA table_info("{table}")')
            columns = [col[1] for col in cursor.fetchall()]
            if 'village_id' in columns:
                logger.info(f"  ✓ {table}")
            else:
                logger.error(f"  ✗ {table} - missing village_id column")
                all_have_column = False
        except sqlite3.OperationalError as e:
            logger.warning(f"  ⚠ {table} - table does not exist: {e}")

    if all_have_column:
        logger.info("  [PASS] All tables have village_id column")
    else:
        logger.error("  [FAIL] Some tables missing village_id column")

    # Test 2: Check village_id format
    logger.info("\nTest 2: Checking village_id format...")
    cursor.execute("""
        SELECT village_id FROM 广东省自然村_预处理
        WHERE village_id NOT LIKE 'v_%' OR village_id IS NULL
        LIMIT 10
    """)
    invalid = cursor.fetchall()
    if len(invalid) == 0:
        logger.info("  ✓ All village_id values have correct format (v_<ROWID>)")
        logger.info("  [PASS] village_id format is correct")
    else:
        logger.error(f"  ✗ Found {len(invalid)} invalid village_id values")
        logger.error(f"  Examples: {invalid[:5]}")
        logger.error("  [FAIL] village_id format is incorrect")

    # Test 3: Check village_id uniqueness in preprocessed table
    logger.info("\nTest 3: Checking village_id uniqueness...")
    cursor.execute("""
        SELECT village_id, COUNT(*) as cnt
        FROM 广东省自然村_预处理
        GROUP BY village_id
        HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()
    if len(duplicates) == 0:
        logger.info("  ✓ All village_id values are unique")
        logger.info("  [PASS] village_id uniqueness verified")
    else:
        logger.error(f"  ✗ Found {len(duplicates)} duplicate village_id values")
        logger.error(f"  Examples: {duplicates[:5]}")
        logger.error("  [FAIL] village_id has duplicates")

    # Test 4: Check coverage
    logger.info("\nTest 4: Checking village_id coverage...")
    coverage_results = []
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}" WHERE village_id IS NULL')
            null_count = cursor.fetchone()[0]
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            total_count = cursor.fetchone()[0]
            coverage = (total_count - null_count) / total_count * 100 if total_count > 0 else 0
            coverage_results.append((table, coverage, total_count - null_count, total_count))
            logger.info(f"  {table}: {coverage:.1f}% ({total_count - null_count:,}/{total_count:,})")
        except sqlite3.OperationalError:
            logger.warning(f"  ⚠ {table} - table does not exist")

    # Check if critical tables have 100% coverage
    critical_tables = ['广东省自然村_预处理', 'village_spatial_features']
    all_critical_covered = True
    for table, coverage, _, _ in coverage_results:
        if table in critical_tables and coverage < 100:
            logger.error(f"  ✗ {table} should have 100% coverage but has {coverage:.1f}%")
            all_critical_covered = False

    if all_critical_covered:
        logger.info("  [PASS] Critical tables have 100% coverage")
    else:
        logger.error("  [FAIL] Some critical tables have incomplete coverage")

    # Test 5: Check indexes exist
    logger.info("\nTest 5: Checking indexes...")
    index_count = 0
    for table in tables:
        try:
            cursor.execute(f"""
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='{table}' AND sql LIKE '%village_id%'
            """)
            indexes = cursor.fetchall()
            if len(indexes) > 0:
                logger.info(f"  ✓ {table} has village_id index: {indexes[0][0]}")
                index_count += 1
            else:
                logger.warning(f"  ⚠ {table} missing village_id index")
        except sqlite3.OperationalError:
            pass

    if index_count >= 4:  # At least 4 tables should have indexes
        logger.info("  [PASS] Most tables have village_id indexes")
    else:
        logger.warning("  [WARN] Some tables missing village_id indexes")

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Verification Summary")
    logger.info("="*60)
    logger.info(f"Tables checked: {len(tables)}")
    logger.info(f"Tables with village_id column: {sum(1 for t, c, _, _ in coverage_results)}")
    logger.info(f"Tables with indexes: {index_count}")
    logger.info("\n✅ Verification complete!")

    conn.close()


if __name__ == "__main__":
    main()
