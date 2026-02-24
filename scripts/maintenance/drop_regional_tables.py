"""
Drop existing regional analysis tables before regeneration.

This script drops all regional analysis tables that will be regenerated
with hierarchical columns (city, county, township) to fix the duplicate
place names issue.

Tables to drop:
- char_regional_analysis
- semantic_regional_analysis
- pattern_regional_analysis
- ngram_tendency
- ngram_significance
- regional_ngram_frequency
"""

import sqlite3
from pathlib import Path

def drop_regional_tables(db_path: str):
    """Drop existing regional analysis tables before regeneration."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables_to_drop = [
        'char_regional_analysis',
        'semantic_regional_analysis',
        'pattern_regional_analysis',
        'ngram_tendency',
        'ngram_significance',
        'regional_ngram_frequency',
    ]

    print("Dropping regional analysis tables...")
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"  [OK] Dropped: {table}")
        except Exception as e:
            print(f"  [ERROR] Error dropping {table}: {e}")

    conn.commit()
    conn.close()
    print("\nAll regional tables dropped successfully!")


def main():
    # Get database path
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / 'data' / 'villages.db'

    print(f"Database: {db_path}")
    print(f"Database exists: {db_path.exists()}\n")

    if not db_path.exists():
        print("Error: Database file not found!")
        return

    # Confirm before dropping
    response = input("Are you sure you want to drop all regional analysis tables? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        return

    drop_regional_tables(str(db_path))


if __name__ == '__main__':
    main()
