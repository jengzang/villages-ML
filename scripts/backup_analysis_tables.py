"""Backup analysis tables before prefix cleaning."""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_table(conn: sqlite3.Connection, table_name: str, backup_suffix: str = "_before_prefix_cleaning"):
    """
    Backup a table by creating a copy with a suffix.

    Args:
        conn: Database connection
        table_name: Name of table to backup
        backup_suffix: Suffix to add to backup table name
    """
    backup_name = f"{table_name}{backup_suffix}"

    cursor = conn.cursor()

    # Check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    if not cursor.fetchone():
        logger.warning(f"Table {table_name} does not exist, skipping")
        return False

    # Drop backup table if exists
    cursor.execute(f"DROP TABLE IF EXISTS {backup_name}")

    # Create backup
    cursor.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
    conn.commit()

    # Verify row counts
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    original_count = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM {backup_name}")
    backup_count = cursor.fetchone()[0]

    if original_count == backup_count:
        logger.info(f"✓ Backed up {table_name} → {backup_name} ({original_count} rows)")
        return True
    else:
        logger.error(f"✗ Backup verification failed for {table_name}")
        return False


def main():
    """Backup all analysis tables before prefix cleaning."""
    db_path = Path(__file__).parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Tables to backup
    tables_to_backup = [
        "character_frequency",
        "regional_character_frequency",
        "character_tendency",
        "character_tendency_zscore",
        "character_significance"
    ]

    logger.info("Starting backup process...")
    success_count = 0

    for table in tables_to_backup:
        if backup_table(conn, table):
            success_count += 1

    conn.close()

    logger.info(f"\nBackup complete: {success_count}/{len(tables_to_backup)} tables backed up")


if __name__ == "__main__":
    main()
