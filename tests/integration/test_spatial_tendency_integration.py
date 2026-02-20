"""
Test script for spatial-tendency integration.

This script performs end-to-end testing of the spatial-tendency integration feature.

Usage:
    python scripts/test_spatial_tendency_integration.py
    python scripts/test_spatial_tendency_integration.py --skip-init
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.db_writer import (
    create_spatial_tendency_table,
    create_spatial_tendency_indexes
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_table_creation(db_path: str) -> bool:
    """Test that tables can be created."""
    logger.info("Test 1: Table Creation")
    logger.info("-" * 60)

    try:
        conn = sqlite3.connect(db_path)
        create_spatial_tendency_table(conn)
        create_spatial_tendency_indexes(conn)

        # Verify table exists
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='spatial_tendency_integration'
        """)
        result = cursor.fetchone()

        if result:
            logger.info("✓ Table 'spatial_tendency_integration' exists")

            # Check schema
            cursor.execute("PRAGMA table_info(spatial_tendency_integration)")
            columns = cursor.fetchall()
            logger.info(f"✓ Table has {len(columns)} columns")

            expected_columns = [
                'id', 'run_id', 'tendency_run_id', 'spatial_run_id',
                'character', 'cluster_id', 'cluster_tendency_mean',
                'cluster_tendency_std', 'cluster_size', 'n_villages_with_char',
                'centroid_lon', 'centroid_lat', 'avg_distance_km',
                'spatial_coherence', 'dominant_city', 'dominant_county',
                'is_significant', 'avg_p_value', 'created_at'
            ]

            actual_columns = [col[1] for col in columns]
            missing = set(expected_columns) - set(actual_columns)
            extra = set(actual_columns) - set(expected_columns)

            if missing:
                logger.error(f"✗ Missing columns: {missing}")
                return False
            if extra:
                logger.warning(f"⚠ Extra columns: {extra}")

            logger.info("✓ Schema is correct")

            # Check indexes
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='spatial_tendency_integration'
            """)
            indexes = cursor.fetchall()
            logger.info(f"✓ {len(indexes)} indexes created")

            conn.close()
            return True
        else:
            logger.error("✗ Table does not exist")
            conn.close()
            return False

    except Exception as e:
        logger.error(f"✗ Table creation failed: {e}")
        return False


def test_data_availability(db_path: str) -> dict:
    """Test that required data is available."""
    logger.info("\nTest 2: Data Availability")
    logger.info("-" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    results = {}

    # Check tendency analysis data
    cursor.execute("SELECT COUNT(*) FROM regional_tendency")
    tendency_count = cursor.fetchone()[0]
    logger.info(f"Regional tendency records: {tendency_count}")
    results['tendency_available'] = tendency_count > 0

    # Check significance data
    cursor.execute("SELECT COUNT(*) FROM tendency_significance")
    significance_count = cursor.fetchone()[0]
    logger.info(f"Tendency significance records: {significance_count}")
    results['significance_available'] = significance_count > 0

    # Check spatial features
    try:
        cursor.execute("SELECT COUNT(*) FROM village_spatial_features")
        spatial_count = cursor.fetchone()[0]
        logger.info(f"Village spatial features: {spatial_count}")
        results['spatial_available'] = spatial_count > 0
    except sqlite3.OperationalError:
        logger.warning("⚠ Table 'village_spatial_features' does not exist")
        logger.info("  Run Phase 13 spatial analysis first")
        spatial_count = 0
        results['spatial_available'] = False

    # Check spatial clusters
    try:
        cursor.execute("SELECT COUNT(*) FROM spatial_clusters")
        cluster_count = cursor.fetchone()[0]
        logger.info(f"Spatial clusters: {cluster_count}")
        results['clusters_available'] = cluster_count > 0
    except sqlite3.OperationalError:
        logger.warning("⚠ Table 'spatial_clusters' does not exist")
        cluster_count = 0
        results['clusters_available'] = False

    # Get available run IDs
    cursor.execute("SELECT DISTINCT run_id FROM regional_tendency LIMIT 5")
    tendency_runs = [row[0] for row in cursor.fetchall()]
    logger.info(f"Available tendency run IDs: {tendency_runs}")
    results['tendency_run_ids'] = tendency_runs

    try:
        cursor.execute("SELECT DISTINCT run_id FROM village_spatial_features LIMIT 5")
        spatial_runs = [row[0] for row in cursor.fetchall()]
        logger.info(f"Available spatial run IDs: {spatial_runs}")
        results['spatial_run_ids'] = spatial_runs
    except sqlite3.OperationalError:
        logger.info("No spatial run IDs available (table doesn't exist)")
        results['spatial_run_ids'] = []

    conn.close()

    all_available = all([
        results['tendency_available'],
        results['spatial_available']
    ])

    if all_available:
        logger.info("✓ All required data is available")
    else:
        logger.warning("⚠ Some required data is missing")

    return results


def test_integration_logic(db_path: str, data_info: dict) -> bool:
    """Test the integration logic with sample data."""
    logger.info("\nTest 3: Integration Logic")
    logger.info("-" * 60)

    if not data_info['tendency_available'] or not data_info['spatial_available']:
        logger.warning("⚠ Skipping integration test - required data not available")
        return True

    try:
        # Import integration functions
        from scripts.spatial_tendency_integration import (
            load_tendency_results,
            load_spatial_features,
            load_villages_with_chars,
            integrate_spatial_tendency
        )

        conn = sqlite3.connect(db_path)

        # Use first available run IDs
        tendency_run_id = data_info['tendency_run_ids'][0] if data_info['tendency_run_ids'] else None
        spatial_run_id = data_info['spatial_run_ids'][0] if data_info['spatial_run_ids'] else None

        if not tendency_run_id or not spatial_run_id:
            logger.warning("⚠ No run IDs available for testing")
            return True

        logger.info(f"Using tendency_run_id: {tendency_run_id}")
        logger.info(f"Using spatial_run_id: {spatial_run_id}")

        # Load data
        logger.info("Loading tendency results...")
        tendency_df = load_tendency_results(conn, tendency_run_id, 'county')
        logger.info(f"✓ Loaded {len(tendency_df)} tendency records")

        logger.info("Loading spatial features...")
        spatial_df = load_spatial_features(conn, spatial_run_id)
        logger.info(f"✓ Loaded {len(spatial_df)} spatial features")

        logger.info("Loading village data...")
        villages_df = load_villages_with_chars(conn, db_path)
        logger.info(f"✓ Loaded {len(villages_df)} villages")

        # Test with a common character
        test_char = '村'
        logger.info(f"\nTesting integration for character: {test_char}")

        result_df = integrate_spatial_tendency(
            tendency_df=tendency_df,
            spatial_df=spatial_df,
            villages_df=villages_df,
            character=test_char,
            tendency_run_id=tendency_run_id,
            spatial_run_id=spatial_run_id
        )

        if len(result_df) > 0:
            logger.info(f"✓ Generated {len(result_df)} integration records")
            logger.info(f"  Clusters: {result_df['cluster_id'].nunique()}")
            logger.info(f"  Total villages with char: {result_df['n_villages_with_char'].sum()}")
            logger.info(f"  Avg spatial coherence: {result_df['spatial_coherence'].mean():.3f}")

            # Check for required columns
            required_cols = [
                'character', 'cluster_id', 'cluster_size', 'n_villages_with_char',
                'centroid_lon', 'centroid_lat', 'spatial_coherence',
                'dominant_city', 'dominant_county'
            ]
            missing_cols = set(required_cols) - set(result_df.columns)
            if missing_cols:
                logger.error(f"✗ Missing columns in result: {missing_cols}")
                return False

            logger.info("✓ All required columns present")
            return True
        else:
            logger.warning(f"⚠ No integration results for character '{test_char}'")
            return True

    except Exception as e:
        logger.error(f"✗ Integration logic test failed: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def test_query_functionality(db_path: str) -> bool:
    """Test query functionality."""
    logger.info("\nTest 4: Query Functionality")
    logger.info("-" * 60)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if there's any data to query
        cursor.execute("SELECT COUNT(*) FROM spatial_tendency_integration")
        count = cursor.fetchone()[0]

        if count == 0:
            logger.info("⚠ No integration data to query (table is empty)")
            logger.info("  This is expected if integration hasn't been run yet")
            conn.close()
            return True

        logger.info(f"Found {count} integration records")

        # Test basic query
        cursor.execute("""
            SELECT character, COUNT(*) as n_clusters
            FROM spatial_tendency_integration
            GROUP BY character
            LIMIT 5
        """)
        results = cursor.fetchall()
        logger.info(f"✓ Query successful: {len(results)} characters found")

        # Test filtered query
        cursor.execute("""
            SELECT COUNT(*)
            FROM spatial_tendency_integration
            WHERE is_significant = 1
        """)
        sig_count = cursor.fetchone()[0]
        logger.info(f"✓ Significant results: {sig_count} ({sig_count/count*100:.1f}%)")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"✗ Query test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Test spatial-tendency integration implementation'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to database (default: data/villages.db)'
    )
    parser.add_argument(
        '--skip-init',
        action='store_true',
        help='Skip table initialization test'
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    logger.info("="*60)
    logger.info("SPATIAL-TENDENCY INTEGRATION TEST SUITE")
    logger.info("="*60)
    logger.info(f"Database: {db_path}")
    logger.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    results = {}

    # Test 1: Table Creation
    if not args.skip_init:
        results['table_creation'] = test_table_creation(str(db_path))
    else:
        logger.info("Skipping table creation test")
        results['table_creation'] = True

    # Test 2: Data Availability
    data_info = test_data_availability(str(db_path))
    results['data_availability'] = all([
        data_info.get('tendency_available', False),
        data_info.get('spatial_available', False)
    ])

    # Test 3: Integration Logic
    results['integration_logic'] = test_integration_logic(str(db_path), data_info)

    # Test 4: Query Functionality
    results['query_functionality'] = test_query_functionality(str(db_path))

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name:30s} {status}")

    all_passed = all(results.values())

    logger.info("="*60)
    if all_passed:
        logger.info("✓ ALL TESTS PASSED")
        logger.info("\nNext steps:")
        logger.info("1. Run integration analysis:")
        logger.info("   python scripts/spatial_tendency_integration.py \\")
        logger.info("     --char 田 \\")
        logger.info(f"     --tendency-run-id {data_info['tendency_run_ids'][0] if data_info.get('tendency_run_ids') else '<run_id>'} \\")
        logger.info(f"     --spatial-run-id {data_info['spatial_run_ids'][0] if data_info.get('spatial_run_ids') else '<run_id>'} \\")
        logger.info("     --output-run-id integration_test_001")
        logger.info("\n2. Query results:")
        logger.info("   python scripts/query_spatial_tendency.py --run-id integration_test_001")
        sys.exit(0)
    else:
        logger.error("✗ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
