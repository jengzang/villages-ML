"""Optimize preprocessed table by retaining only essential columns.

This script rebuilds the 广东省自然村_预处理 table with only 11 essential columns,
reducing storage space from 115.6 MB to approximately 45-55 MB.

Retained columns (11):
1. 市级 - City level
2. 区县级 - District/County level
3. 乡镇级 - Township level
4. 村委会 - Village Committee (renamed from 行政村)
5. 自然村_规范名 - Normalized village name (renamed from 自然村_规范化)
6. 自然村_去前缀 - Village name with prefix removed
7. longitude - Longitude coordinate
8. latitude - Latitude coordinate
9. 语言分布 - Language distribution
10. 字符集 - Character set (JSON array)
11. 字符数量 - Character count

Removed columns (17):
- All original raw columns except geographic hierarchy and language
- All intermediate processing flags (有括号, 有噪音, etc.)
- All prefix metadata (前缀匹配来源, 前缀置信度, etc.)
- All validity flags (有效, 无效原因, etc.)
"""

import sqlite3
import logging
from pathlib import Path

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
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='广东省自然村_预处理'
    """)
    if not cursor.fetchone():
        logger.error("Source table 广东省自然村_预处理 not found!")
        conn.close()
        return

    # Get row count before optimization
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村_预处理")
    original_count = cursor.fetchone()[0]
    logger.info(f"Original table has {original_count:,} rows")

    # Create backup table name
    backup_table = "广东省自然村_预处理_backup"

    # Rename original table to backup
    logger.info(f"Backing up original table to {backup_table}...")
    cursor.execute(f"DROP TABLE IF EXISTS {backup_table}")
    cursor.execute(f"ALTER TABLE 广东省自然村_预处理 RENAME TO {backup_table}")
    conn.commit()

    # Create optimized table with only 11 columns
    logger.info("Creating optimized table schema...")
    cursor.execute("""
    CREATE TABLE 广东省自然村_预处理 (
        市级 TEXT,
        区县级 TEXT,
        乡镇级 TEXT,
        村委会 TEXT,
        自然村_规范名 TEXT,
        自然村_去前缀 TEXT,
        longitude TEXT,
        latitude TEXT,
        语言分布 TEXT,
        字符集 TEXT,
        字符数量 INTEGER
    )
    """)

    # Copy data with column renaming
    logger.info("Copying data to optimized table...")
    cursor.execute(f"""
    INSERT INTO 广东省自然村_预处理 (
        市级, 区县级, 乡镇级, 村委会,
        自然村_规范名, 自然村_去前缀,
        longitude, latitude, 语言分布, 字符集, 字符数量
    )
    SELECT
        市级, 区县级, 乡镇级, 行政村,
        自然村_规范化, 自然村_去前缀,
        longitude, latitude, 语言分布, 字符集, 字符数量
    FROM {backup_table}
    """)
    conn.commit()

    # Verify row count
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村_预处理")
    new_count = cursor.fetchone()[0]
    logger.info(f"Optimized table has {new_count:,} rows")

    if new_count != original_count:
        logger.error(f"Row count mismatch! Original: {original_count}, New: {new_count}")
        logger.error("Rolling back...")
        cursor.execute("DROP TABLE IF EXISTS 广东省自然村_预处理")
        cursor.execute(f"ALTER TABLE {backup_table} RENAME TO 广东省自然村_预处理")
        conn.commit()
        conn.close()
        return

    # Create indexes for query performance
    logger.info("Creating indexes...")
    cursor.execute("CREATE INDEX idx_prep_city ON 广东省自然村_预处理(市级)")
    cursor.execute("CREATE INDEX idx_prep_county ON 广东省自然村_预处理(区县级)")
    cursor.execute("CREATE INDEX idx_prep_township ON 广东省自然村_预处理(乡镇级)")
    cursor.execute("CREATE INDEX idx_prep_village ON 广东省自然村_预处理(村委会)")
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
    logger.info(f"Columns: 28 → 11 (reduced by 17 columns)")
    logger.info(f"Database size: {total_size_mb:.1f} MB")
    logger.info(f"\nBackup table '{backup_table}' retained for safety.")
    logger.info(f"To remove backup: DROP TABLE {backup_table};")

    conn.close()


def main():
    """Main entry point."""
    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    optimize_preprocessed_table(db_path)


if __name__ == "__main__":
    main()
