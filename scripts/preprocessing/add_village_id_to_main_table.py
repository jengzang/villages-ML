"""Add village_id to main table by mapping to preprocessed table ROWID.

This script:
1. Adds village_id column to main table
2. Populates village_id by mapping to preprocessed table
3. Creates index on village_id for fast lookups
"""

import sqlite3
import logging
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.schema import DEFAULT_SCHEMA as S

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Add village_id to main table."""
    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Add village_id column if not exists
    try:
        cursor.execute(f"ALTER TABLE {S.raw_table} ADD COLUMN {S.village_id_col} TEXT")
        logger.info(f"Added {S.village_id_col} column to {S.raw_table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info(f"{S.village_id_col} column already exists")
        else:
            raise

    # Populate village_id by mapping to preprocessed table
    logger.info(f"Populating {S.village_id_col}...")
    cursor.execute(f"""
        UPDATE {S.raw_table}
        SET {S.village_id_col} = (
            SELECT p.{S.village_id_col}
            FROM {S.preprocessed_table} p
            WHERE p.{S.city_col} = {S.raw_table}.{S.city_col}
              AND p.{S.county_col} = {S.raw_table}.{S.county_col}
              AND p.{S.township_col} = {S.raw_table}.{S.township_col}
              AND p.{S.committee_col_preprocessed} = {S.raw_table}.{S.committee_col_raw}
              AND p.{S.village_name_col_raw} = {S.raw_table}.{S.village_name_col_raw}
            LIMIT 1
        )
    """)
    conn.commit()
    logger.info(f"{S.village_id_col} populated")

    # Create index
    logger.info(f"Creating index on {S.village_id_col}...")
    try:
        cursor.execute(f"CREATE INDEX idx_main_village_id ON {S.raw_table}({S.village_id_col})")
        logger.info("Index created successfully")
    except sqlite3.OperationalError as e:
        if "already exists" in str(e).lower():
            logger.info("Index already exists")
        else:
            raise

    # Verify
    cursor.execute(f"SELECT COUNT(*) FROM {S.raw_table} WHERE {S.village_id_col} IS NOT NULL")
    populated_count = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM {S.raw_table}")
    total_count = cursor.fetchone()[0]

    coverage = (populated_count / total_count * 100) if total_count > 0 else 0

    logger.info(f"\nVerification:")
    logger.info(f"  Total villages: {total_count:,}")
    logger.info(f"  Populated {S.village_id_col}: {populated_count:,}")
    logger.info(f"  Coverage: {coverage:.2f}%")

    if populated_count < total_count:
        cursor.execute(f"SELECT COUNT(*) FROM {S.raw_table} WHERE {S.village_id_col} IS NULL LIMIT 10")
        null_count = cursor.fetchone()[0]
        logger.warning(f"  {null_count:,} villages have NULL {S.village_id_col}")

    conn.close()
    logger.info("Complete!")


if __name__ == "__main__":
    main()
