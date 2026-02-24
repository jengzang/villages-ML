"""
Drop deprecated tables from database optimization (2026-02-24).

These 4 tables were replaced by unified *_regional_analysis tables:
- char_frequency_regional → char_regional_analysis
- regional_tendency → char_regional_analysis
- semantic_tendency → semantic_regional_analysis
- semantic_vtf_regional → semantic_regional_analysis

See: docs/guides/DATABASE_MIGRATION_FOR_BACKEND.md

Usage:
    python scripts/maintenance/drop_deprecated_tables.py
"""

import sqlite3
from pathlib import Path


def drop_deprecated_tables(db_path: str):
    """Drop deprecated tables from database optimization."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    deprecated_tables = [
        'char_frequency_regional',
        'regional_tendency',
        'semantic_tendency',
        'semantic_vtf_regional',
    ]

    print("\nDropping deprecated tables...")
    print("=" * 80)

    dropped_count = 0
    for table in deprecated_tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            dropped_count += 1
            print(f"  [OK] Dropped: {table}")
        except sqlite3.Error as e:
            print(f"  [ERROR] Error dropping {table}: {e}")

    conn.commit()
    conn.close()

    print("=" * 80)
    print(f"\n[SUCCESS] Successfully dropped {dropped_count}/{len(deprecated_tables)} deprecated tables")
    print("Database cleanup complete!")


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        exit(1)

    print(f"Database: {db_path}")
    drop_deprecated_tables(str(db_path))
