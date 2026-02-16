"""
Initialize spatial-tendency integration tables in the database.

This script creates the necessary database tables and indexes for storing
spatial-tendency integration results.

Usage:
    python scripts/init_spatial_tendency_tables.py
    python scripts/init_spatial_tendency_tables.py --db-path data/villages.db
"""

import argparse
import logging
import sqlite3
import sys
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


def main():
    parser = argparse.ArgumentParser(
        description='Initialize spatial-tendency integration tables'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to database (default: data/villages.db)'
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    logger.info(f"Initializing spatial-tendency integration tables in: {db_path}")

    conn = sqlite3.connect(db_path)

    try:
        # Create tables
        logger.info("Creating spatial_tendency_integration table...")
        create_spatial_tendency_table(conn)

        # Create indexes
        logger.info("Creating indexes...")
        create_spatial_tendency_indexes(conn)

        # Verify tables exist
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='spatial_tendency_integration'
        """)
        result = cursor.fetchone()

        if result:
            logger.info("✓ Table 'spatial_tendency_integration' created successfully")

            # Check record count
            cursor.execute("SELECT COUNT(*) FROM spatial_tendency_integration")
            count = cursor.fetchone()[0]
            logger.info(f"  Current records: {count}")
        else:
            logger.error("✗ Table creation failed")
            sys.exit(1)

        logger.info("\nInitialization complete!")
        logger.info("\nNext steps:")
        logger.info("1. Run spatial-tendency integration analysis:")
        logger.info("   python scripts/spatial_tendency_integration.py \\")
        logger.info("     --char 田 \\")
        logger.info("     --tendency-run-id <your_tendency_run_id> \\")
        logger.info("     --spatial-run-id <your_spatial_run_id> \\")
        logger.info("     --output-run-id integration_001")
        logger.info("\n2. Query results:")
        logger.info("   python scripts/query_spatial_tendency.py --run-id integration_001")

    except Exception as e:
        logger.error(f"Error during initialization: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
