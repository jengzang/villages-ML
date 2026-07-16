"""Apply conservative admin-prefix duplicate merges to the raw village table.

The script reads ``results/intra_admin_near_duplicates/merge_proposals.csv`` and
applies only proposals whose coordinate distance is <= the configured threshold.
It records full audit rows before deleting anything.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import time
from pathlib import Path


DB_PATH = Path("data/villages.db")
PROPOSAL_PATH = Path("results/intra_admin_near_duplicates/merge_proposals.csv")
RAW_TABLE = "广东省自然村"
AUDIT_TABLE = "cleanup_admin_prefix_merge_audit"


def is_blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def load_proposals(path: Path, max_distance_m: float) -> list[dict[str, str]]:
    proposals = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["proposal_type"] != "admin_prefix_duplicate":
                continue
            if not row["distance_m"] or float(row["distance_m"]) > max_distance_m:
                continue
            proposals.append(row)
    return proposals


def fetch_row(conn: sqlite3.Connection, rowid: int) -> dict[str, object]:
    conn.row_factory = sqlite3.Row
    row = conn.execute(f'SELECT rowid, * FROM "{RAW_TABLE}" WHERE rowid = ?', (rowid,)).fetchone()
    if row is None:
        raise ValueError(f"rowid not found: {rowid}")
    return dict(row)


def create_audit_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {AUDIT_TABLE} (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            applied_at REAL NOT NULL,
            action TEXT NOT NULL,
            keep_rowid INTEGER NOT NULL,
            delete_rowid INTEGER NOT NULL,
            dialect_transferred TEXT,
            proposal_json TEXT NOT NULL,
            keep_row_before_json TEXT NOT NULL,
            delete_row_before_json TEXT NOT NULL
        )
        """
    )


def apply_merges(db_path: Path, proposal_path: Path, max_distance_m: float, dry_run: bool) -> dict[str, int]:
    proposals = load_proposals(proposal_path, max_distance_m)
    delete_ids = [int(row["delete_rowid"]) for row in proposals]
    keep_ids = [int(row["keep_rowid"]) for row in proposals]
    if len(delete_ids) != len(set(delete_ids)):
        raise ValueError("duplicate delete_rowid found in selected proposals")
    if set(delete_ids) & set(keep_ids):
        raise ValueError("a selected row appears as both keep and delete")

    conn = sqlite3.connect(db_path)
    create_audit_table(conn)

    stats = {
        "selected_proposals": len(proposals),
        "dialect_transfers": 0,
        "deleted_rows": 0,
        "audit_rows": 0,
    }
    applied_at = time.time()

    try:
        conn.execute("BEGIN")
        for proposal in proposals:
            keep_rowid = int(proposal["keep_rowid"])
            delete_rowid = int(proposal["delete_rowid"])
            keep_before = fetch_row(conn, keep_rowid)
            delete_before = fetch_row(conn, delete_rowid)

            if keep_before["自然村"] != proposal["keep_自然村"]:
                raise ValueError(f"keep row changed unexpectedly: {keep_rowid}")
            if delete_before["自然村"] != proposal["delete_自然村"]:
                raise ValueError(f"delete row changed unexpectedly: {delete_rowid}")

            transfer = ""
            if is_blank(keep_before.get("方言分布")) and not is_blank(delete_before.get("方言分布")):
                transfer = str(delete_before["方言分布"]).strip()

            conn.execute(
                f"""
                INSERT INTO {AUDIT_TABLE} (
                    applied_at, action, keep_rowid, delete_rowid, dialect_transferred,
                    proposal_json, keep_row_before_json, delete_row_before_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    applied_at,
                    "dry_run" if dry_run else "applied",
                    keep_rowid,
                    delete_rowid,
                    transfer,
                    json.dumps(proposal, ensure_ascii=False),
                    json.dumps(keep_before, ensure_ascii=False),
                    json.dumps(delete_before, ensure_ascii=False),
                ),
            )
            stats["audit_rows"] += 1

            if transfer:
                conn.execute(
                    f'UPDATE "{RAW_TABLE}" SET 方言分布 = ? WHERE rowid = ?',
                    (transfer, keep_rowid),
                )
                stats["dialect_transfers"] += 1

            conn.execute(f'DELETE FROM "{RAW_TABLE}" WHERE rowid = ?', (delete_rowid,))
            stats["deleted_rows"] += 1

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--proposals", type=Path, default=PROPOSAL_PATH)
    parser.add_argument("--max-distance-m", type=float, default=500.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats = apply_merges(args.db, args.proposals, args.max_distance_m, args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
