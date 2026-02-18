"""Create audit log table for prefix cleaning operations.

This script creates a detailed audit log table that records:
- Which villages had prefixes removed
- What the administrative village was
- Complete geographic hierarchy
- Before/after comparison
- Match source and confidence
- LLM reasoning (if used)
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_audit_log_table(conn: sqlite3.Connection):
    """Create the prefix cleaning audit log table."""
    cursor = conn.cursor()

    # Drop if exists
    cursor.execute("DROP TABLE IF EXISTS prefix_cleaning_audit_log")

    # Create table
    cursor.execute("""
    CREATE TABLE prefix_cleaning_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        -- Geographic hierarchy (complete)
        市级 TEXT,
        区县级 TEXT,
        乡镇级 TEXT,
        行政村 TEXT,

        -- Cleaning information
        自然村_原始 TEXT NOT NULL,
        自然村_基础清洗 TEXT NOT NULL,
        自然村_去前缀 TEXT NOT NULL,

        -- Prefix information
        检测到前缀 INTEGER NOT NULL,
        前缀候选 TEXT,
        去除的前缀 TEXT,
        剩余部分 TEXT,

        -- Match information
        匹配来源 TEXT,
        匹配的行政村 TEXT,
        规则置信度 REAL,
        最终置信度 REAL,

        -- Decision information
        是否去除 INTEGER NOT NULL,
        需要人工审核 INTEGER NOT NULL,

        -- Timestamp
        处理时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX idx_audit_city ON prefix_cleaning_audit_log(市级)")
    cursor.execute("CREATE INDEX idx_audit_removed ON prefix_cleaning_audit_log(是否去除)")
    cursor.execute("CREATE INDEX idx_audit_review ON prefix_cleaning_audit_log(需要人工审核)")
    cursor.execute("CREATE INDEX idx_audit_confidence ON prefix_cleaning_audit_log(最终置信度)")

    conn.commit()
    logger.info("Created prefix_cleaning_audit_log table")


def populate_audit_log(conn: sqlite3.Connection):
    """Populate audit log from preprocessed table."""
    cursor = conn.cursor()

    logger.info("Populating audit log from preprocessed table...")

    query = """
    INSERT INTO prefix_cleaning_audit_log (
        市级, 区县级, 乡镇级, 行政村,
        自然村_原始, 自然村_基础清洗, 自然村_去前缀,
        检测到前缀, 前缀候选, 去除的前缀, 剩余部分,
        匹配来源, 匹配的行政村, 规则置信度, 最终置信度,
        是否去除, 需要人工审核
    )
    SELECT
        市级, 区县级, 乡镇级, 行政村,
        自然村, 自然村_基础清洗, 自然村_去前缀,
        有前缀,
        CASE WHEN 有前缀=1 THEN 去除的前缀 ELSE NULL END,
        去除的前缀,
        CASE WHEN 有前缀=1 THEN 自然村_去前缀 ELSE NULL END,
        前缀匹配来源,
        行政村,
        前缀置信度,
        前缀置信度,
        有前缀,
        需要审核
    FROM 广东省自然村_预处理
    WHERE 有效 = 1
    """

    cursor.execute(query)
    conn.commit()

    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM prefix_cleaning_audit_log")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(是否去除) FROM prefix_cleaning_audit_log")
    removed = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(需要人工审核) FROM prefix_cleaning_audit_log")
    review = cursor.fetchone()[0] or 0

    logger.info(f"Audit log populated:")
    logger.info(f"  Total entries: {total}")
    logger.info(f"  Prefixes removed: {removed} ({100*removed/total:.1f}%)")
    logger.info(f"  Needs review: {review} ({100*review/total:.1f}%)")


def main():
    """Create and populate audit log table."""
    db_path = Path(__file__).parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Create audit log table
    create_audit_log_table(conn)

    # Check if preprocessed table exists
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='广东省自然村_预处理'"
    )
    if not cursor.fetchone():
        logger.error("Preprocessed table not found. Run create_preprocessed_table.py first.")
        conn.close()
        return

    # Populate audit log
    populate_audit_log(conn)

    conn.close()
    logger.info("Audit log creation complete!")


if __name__ == "__main__":
    main()
