"""Optimize preprocessed table by retaining only essential columns.

This script rebuilds the preprocessed table with only 11 essential columns,
reducing storage space from 115.6 MB to approximately 45-55 MB.
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def optimize_preprocessed_table(db_path: Path):
    """Rebuild preprocessed table with only essential columns."""

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check if source table exists
    cursor.execute(f"""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='{S.preprocessed_table}'
    """)
    if not cursor.fetchone():
        logger.error(f"Source table {S.preprocessed_table} not found!")
        conn.close()
        return

    # Get row count before optimization
    cursor.execute(f"SELECT COUNT(*) FROM {S.preprocessed_table}")
    original_count = cursor.fetchone()[0]
    logger.info(f"Original table has {original_count:,} rows")

    # Create backup table name
    backup_table = f"{S.preprocessed_table}_backup"

    # Rename original table to backup
    logger.info(f"Backing up original table to {backup_table}...")
    cursor.execute(f"DROP TABLE IF EXISTS {backup_table}")
    cursor.execute(f"ALTER TABLE {S.preprocessed_table} RENAME TO {backup_table}")
    conn.commit()

    # Create optimized table with only 11 columns
    logger.info("Creating optimized table schema...")
    cursor.execute(f"""
    CREATE TABLE {S.preprocessed_table} (
        {S.city_col} TEXT,
        {S.county_col} TEXT,
        {S.township_col} TEXT,
        {S.committee_col_preprocessed} TEXT,
        {S.village_name_col_normalized} TEXT,
        {S.village_name_col_prefix_removed} TEXT,
        {S.longitude_col} TEXT,
        {S.latitude_col} TEXT,
        {S.language_col_preprocessed} TEXT,
        {S.char_set_col} TEXT,
        {S.char_count_col} INTEGER
    )
    """)

    # Copy data with column renaming (backup has 行政村→村委会, 自然村_规范化→自然村_规范名)
    logger.info("Copying data to optimized table...")
    cursor.execute(f"""
    INSERT INTO {S.preprocessed_table} (
        {S.city_col}, {S.county_col}, {S.township_col}, {S.committee_col_preprocessed},
        {S.village_name_col_normalized}, {S.village_name_col_prefix_removed},
        {S.longitude_col}, {S.latitude_col}, {S.language_col_preprocessed},
        {S.char_set_col}, {S.char_count_col}
    )
    SELECT
        {S.city_col}, {S.county_col}, {S.township_col}, {S.committee_col_raw},
        自然村_规范化, {S.village_name_col_prefix_removed},
        {S.longitude_col}, {S.latitude_col}, {S.language_col_preprocessed},
        {S.char_set_col}, {S.char_count_col}
    FROM {backup_table}
    """)
    conn.commit()

    # Verify row count
    cursor.execute(f"SELECT COUNT(*) FROM {S.preprocessed_table}")
    new_count = cursor.fetchone()[0]
    logger.info(f"Optimized table has {new_count:,} rows")

    if new_count != original_count:
        logger.error(f"Row count mismatch! Original: {original_count}, New: {new_count}")
        logger.error("Rolling back...")
        cursor.execute(f"DROP TABLE IF EXISTS {S.preprocessed_table}")
        cursor.execute(f"ALTER TABLE {backup_table} RENAME TO {S.preprocessed_table}")
        conn.commit()
        conn.close()
        return

    # Create indexes for query performance
    logger.info("Creating indexes...")
    cursor.execute(f"CREATE INDEX idx_prep_city ON {S.preprocessed_table}({S.city_col})")
    cursor.execute(f"CREATE INDEX idx_prep_county ON {S.preprocessed_table}({S.county_col})")
    cursor.execute(f"CREATE INDEX idx_prep_township ON {S.preprocessed_table}({S.township_col})")
    cursor.execute(f"CREATE INDEX idx_prep_village ON {S.preprocessed_table}({S.committee_col_preprocessed})")
    conn.commit()

    # Get table sizes
    cursor.execute("PRAGMA page_count")
    total_pages = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    total_size_mb = (total_pages * page_size) / (1024 * 1024)

    logger.info(f"\n{'='*70}")
    logger.info("Optimization Complete!")
    logger.info(f"{'='*70}")
    logger.info(f"Rows: {new_count:,}")
    logger.info(f"Columns: 28 -> 11 (reduced by 17 columns)")
    logger.info(f"Database size: {total_size_mb:.1f} MB")
    logger.info(f"\nBackup table '{backup_table}' retained for safety.")
    logger.info(f"\nTo permanently remove backup: DROP TABLE {backup_table};")
    logger.info(f"\nTo rollback: DROP TABLE {S.preprocessed_table}; ALTER TABLE {backup_table} RENAME TO {S.preprocessed_table};")

    conn.close()
    logger.info("Optimization complete!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Optimize preprocessed village table")
    parser.add_argument("--db", type=str, default="data/villages.db",
                        help="Path to database file (default: data/villages.db)")
    args = parser.parse_args()

    project_root = Path(args.db).parent.parent.resolve()
    db_path = Path(args.db).resolve()
    optimize_preprocessed_table(db_path)
