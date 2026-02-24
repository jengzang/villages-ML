"""Add village_id to main table by mapping to preprocessed table ROWID.

This script:
1. Adds village_id column to main table (广东省自然村)
2. Populates village_id by mapping to preprocessed table
3. Creates index on village_id for fast lookups
"""

import sqlite3
import logging
from pathlib import Path

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
        cursor.execute("ALTER TABLE 广东省自然村 ADD COLUMN village_id TEXT")
        logger.info("Added village_id column to main table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("village_id column already exists")
        else:
            raise

    # Populate village_id by mapping to preprocessed table
    logger.info("Populating village_id...")
    cursor.execute("""
        UPDATE 广东省自然村
        SET village_id = (
            SELECT p.village_id
            FROM 广东省自然村_预处理 p
            WHERE p.市级 = 广东省自然村.市级
              AND p.区县级 = 广东省自然村.区县级
              AND p.乡镇级 = 广东省自然村.乡镇级
              AND p.村委会 = 广东省自然村.村委会
              AND p.自然村 = 广东省自然村.自然村
            LIMIT 1
        )
    """)
    conn.commit()
    logger.info("village_id populated")

    # Create index
    logger.info("Creating index on village_id...")
    try:
        cursor.execute("CREATE INDEX idx_main_village_id ON 广东省自然村(village_id)")
        logger.info("Index created successfully")
    except sqlite3.OperationalError as e:
        if "already exists" in str(e).lower():
            logger.info("Index already exists")
        else:
            raise

    # Verify
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村 WHERE village_id IS NOT NULL")
    populated_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM 广东省自然村")
    total_count = cursor.fetchone()[0]

    coverage = (populated_count / total_count * 100) if total_count > 0 else 0

    logger.info(f"\nVerification:")
    logger.info(f"  Total villages: {total_count:,}")
    logger.info(f"  Populated village_id: {populated_count:,}")
    logger.info(f"  Coverage: {coverage:.2f}%")

    if populated_count < total_count:
        cursor.execute("SELECT COUNT(*) FROM 广东省自然村 WHERE village_id IS NULL LIMIT 10")
        null_count = cursor.fetchone()[0]
        logger.warning(f"  {null_count:,} villages have NULL village_id")

    conn.close()
    logger.info("Complete!")


if __name__ == "__main__":
    main()
