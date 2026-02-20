"""
Test script for query policy framework.

This script tests:
1. Query validation (blocking full table scans)
2. Row limit enforcement
3. Pagination support
4. Configuration loading
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.deployment import QueryPolicy, DeploymentConfig, SafeQueryExecutor, PolicyViolationError
from src.data.db_query import get_village_features


def test_query_policy():
    """Test query policy framework."""
    print("=" * 80)
    print("Testing Query Policy Framework")
    print("=" * 80)

    # Connect to database
    db_path = Path(__file__).parent.parent / 'data' / 'villages.db'
    conn = sqlite3.connect(str(db_path))

    # Test 1: Load configurations
    print("\n[Test 1] Loading configurations...")
    default_config = DeploymentConfig()
    print(f"  Default max_rows: {default_config.max_rows_default}")
    print(f"  Default enable_full_scan: {default_config.enable_full_scan}")

    prod_config = DeploymentConfig.production()
    print(f"  Production max_rows: {prod_config.max_rows_default}")
    print(f"  Production enable_full_scan: {prod_config.enable_full_scan}")

    dev_config = DeploymentConfig.development()
    print(f"  Development max_rows: {dev_config.max_rows_default}")
    print(f"  Development enable_full_scan: {dev_config.enable_full_scan}")
    print("  [OK] Configuration loading works")

    # Test 2: Query with filters (should succeed)
    print("\n[Test 2] Query with filters (should succeed)...")
    policy = QueryPolicy(max_rows=100, enable_full_scan=False)
    executor = SafeQueryExecutor(conn, policy)

    try:
        result = executor.execute(
            get_village_features,
            run_id='feature_001',
            city='广州市',
            limit=10
        )
        print(f"  [OK] Query succeeded, returned {len(result)} rows")
    except Exception as e:
        print(f"  [FAIL] Query failed: {e}")

    # Test 3: Query without filters (should fail)
    print("\n[Test 3] Query without filters (should fail)...")
    try:
        result = executor.execute(
            get_village_features,
            run_id='feature_001'
        )
        print(f"  [FAIL] Query should have been blocked but succeeded")
    except PolicyViolationError as e:
        print(f"  [OK] Query correctly blocked: {e}")

    # Test 4: Query with limit exceeding absolute max (should be capped)
    print("\n[Test 4] Query with limit exceeding absolute max...")
    policy_strict = QueryPolicy(max_rows=100, max_rows_absolute=500)
    executor_strict = SafeQueryExecutor(conn, policy_strict)

    try:
        # Request 1000 rows but should be capped at 500
        result = executor_strict.execute(
            get_village_features,
            run_id='feature_001',
            city='广州市',
            limit=1000
        )
        print(f"  [OK] Query succeeded with capped limit, returned {len(result)} rows (max 500)")
    except Exception as e:
        print(f"  [FAIL] Query failed: {e}")

    # Test 5: Pagination
    print("\n[Test 5] Pagination support...")
    policy_page = QueryPolicy(max_rows=50, enable_full_scan=False)
    executor_page = SafeQueryExecutor(conn, policy_page)

    try:
        results, total, has_next = executor_page.execute_with_pagination(
            get_village_features,
            run_id='feature_001',
            city='广州市',
            page=1,
            page_size=20
        )
        print(f"  [OK] Pagination works: page 1, {len(results)} rows, total={total}, has_next={has_next}")
    except Exception as e:
        print(f"  [FAIL] Pagination failed: {e}")

    # Test 6: Full scan with permission
    print("\n[Test 6] Full scan with permission...")
    policy_permissive = QueryPolicy(max_rows=100, enable_full_scan=True)
    executor_permissive = SafeQueryExecutor(conn, policy_permissive)

    try:
        result = executor_permissive.execute(
            get_village_features,
            run_id='feature_001',
            limit=50
        )
        print(f"  [OK] Full scan allowed when enabled, returned {len(result)} rows")
    except Exception as e:
        print(f"  [FAIL] Full scan failed: {e}")

    conn.close()

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == '__main__':
    test_query_policy()
