"""
Phase 1: Create missing clustering tables.

This script creates the clustering tables that are defined in db_writer.py
but don't exist in the database yet:
- cluster_assignments
- cluster_profiles
- clustering_metrics
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.db_writer import create_clustering_tables

def main():
    db_path = project_root / 'data' / 'villages.db'

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)

    print("Creating clustering tables...")
    create_clustering_tables(conn)

    # Verify tables were created
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('cluster_assignments', 'cluster_profiles', 'clustering_metrics')
        ORDER BY name
    """)
    tables = cursor.fetchall()

    print(f"\nCreated {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")

    conn.close()
    print("\nPhase 1 complete")

if __name__ == '__main__':
    main()
