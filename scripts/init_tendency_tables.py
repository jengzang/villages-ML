#!/usr/bin/env python
"""
Initialize tendency analysis database tables.

This script creates the tendency_significance table and related indexes
in the villages database.

Usage:
    python scripts/init_tendency_tables.py
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def init_tendency_tables(db_path: str = 'data/villages.db'):
    """
    Initialize tendency analysis tables in the database.

    Args:
        db_path: Path to SQLite database
    """
    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create tendency_significance table
        logger.info("Creating tendency_significance table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tendency_significance (
                run_id TEXT NOT NULL,
                region_level TEXT NOT NULL,
                region_name TEXT NOT NULL,
                char TEXT NOT NULL,
                chi_square_statistic REAL NOT NULL,
                p_value REAL NOT NULL,
                is_significant INTEGER NOT NULL,
                significance_level TEXT NOT NULL,
                effect_size REAL NOT NULL,
                effect_size_interpretation TEXT NOT NULL,
                ci_lower REAL,
                ci_upper REAL,
                created_at REAL NOT NULL,
                PRIMARY KEY (run_id, region_level, region_name, char),
                FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
            )
        """)

        # Create indexes
        logger.info("Creating indexes for tendency_significance...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_significance_level ON tendency_significance(run_id, region_level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_significance_char ON tendency_significance(run_id, char)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_significance_pvalue ON tendency_significance(run_id, p_value)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_significance_flag ON tendency_significance(run_id, is_significant)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_significance_effect ON tendency_significance(run_id, effect_size DESC)")

        conn.commit()
        logger.info("✓ Tendency analysis tables initialized successfully")

        # Verify table creation
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tendency_significance'")
        if cursor.fetchone():
            logger.info("✓ Table 'tendency_significance' verified")
        else:
            logger.error("✗ Table 'tendency_significance' not found")

        # Count existing records
        cursor.execute("SELECT COUNT(*) FROM tendency_significance")
        count = cursor.fetchone()[0]
        logger.info(f"Current records in tendency_significance: {count}")

    except Exception as e:
        logger.error(f"Error initializing tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    init_tendency_tables()
