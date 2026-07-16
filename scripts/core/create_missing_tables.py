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
import argparse
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.db_writer import create_clustering_tables


def parse_args():
    parser = argparse.ArgumentParser(description="Create auxiliary pipeline tables")
    parser.add_argument(
        "--db-path",
        default=str(project_root / "data" / "villages.db"),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--tables",
        default="clustering",
        help="Comma-separated table groups to create: clustering, query_policy, all",
    )
    return parser.parse_args()


def _requested_groups(value: str) -> set[str]:
    groups = {item.strip() for item in value.split(",") if item.strip()}
    if not groups:
        return {"clustering"}
    if "all" in groups:
        return {"clustering", "query_policy"}
    return groups


def create_query_policy_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_policy_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            value_type TEXT NOT NULL DEFAULT 'string',
            description TEXT,
            updated_at REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT,
            query_params TEXT,
            row_count INTEGER,
            elapsed_ms REAL,
            status TEXT NOT NULL,
            error_message TEXT,
            created_at REAL NOT NULL
        )
    """)
    now = time.time()
    defaults = [
        ("max_rows_default", "1000", "integer", "Default maximum rows returned by safe queries"),
        ("max_rows_absolute", "10000", "integer", "Hard maximum rows returned by safe queries"),
        ("enable_full_scan", "false", "boolean", "Whether unfiltered full table scans are allowed"),
        ("enable_runtime_clustering", "false", "boolean", "Whether online clustering is allowed"),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO query_policy_config
        (key, value, value_type, description, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, [(key, value, value_type, description, now) for key, value, value_type, description in defaults])
    conn.commit()


def main():
    args = parse_args()
    db_path = Path(args.db_path)
    groups = _requested_groups(args.tables)

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)

    if "clustering" in groups:
        print("Creating clustering tables...")
        create_clustering_tables(conn)

    if "query_policy" in groups:
        print("Creating query policy tables...")
        create_query_policy_tables(conn)

    # Verify tables were created
    cursor = conn.cursor()
    expected_tables = []
    if "clustering" in groups:
        expected_tables.extend(["cluster_assignments", "cluster_profiles", "clustering_metrics"])
    if "query_policy" in groups:
        expected_tables.extend(["query_policy_config", "query_logs"])

    placeholders = ",".join("?" for _ in expected_tables)
    cursor.execute(f"""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ({placeholders})
        ORDER BY name
    """, expected_tables)
    tables = cursor.fetchall()

    print(f"\nCreated {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")

    conn.close()
    print("\nPhase 1 complete")

if __name__ == '__main__':
    main()
