"""Build conservative merge proposals from intra-admin near-duplicate audit."""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter
from pathlib import Path


DB_PATH = Path("data/villages.db")
PAIR_PATH = Path("results/intra_admin_near_duplicates/merge_review_pairs.csv")
OUTPUT_PATH = Path("results/intra_admin_near_duplicates/merge_proposals.csv")


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def load_rows(conn: sqlite3.Connection) -> dict[int, dict[str, str]]:
    rows = conn.execute(
        """
        SELECT rowid, 市级, 区县级, 乡镇级, 行政村, 自然村, 拼音, 方言分布,
               longitude, latitude
        FROM "广东省自然村"
        """
    )
    result = {}
    for row in rows:
        result[int(row[0])] = {
            "rowid": str(row[0]),
            "市级": clean(row[1]),
            "区县级": clean(row[2]),
            "乡镇级": clean(row[3]),
            "行政村": clean(row[4]),
            "自然村": clean(row[5]),
            "拼音": clean(row[6]),
            "方言分布": clean(row[7]),
            "longitude": clean(row[8]),
            "latitude": clean(row[9]),
        }
    return result


def prefix_proposal(pair: dict[str, str], rows: dict[int, dict[str, str]]) -> dict[str, str] | None:
    """Return a keep/delete proposal for admin-prefix duplicate pairs."""
    if "same_after_admin_prefix_removed" not in pair["rules"]:
        return None

    a_id = int(pair["rowid_a"])
    b_id = int(pair["rowid_b"])
    a = rows[a_id]
    b = rows[b_id]
    a_prefix_removed = pair["prefix_removed_a"]
    b_prefix_removed = pair["prefix_removed_b"]

    keep = delete = None
    if a["自然村"] == a_prefix_removed and b["自然村"] != b_prefix_removed:
        keep, delete = a, b
    elif b["自然村"] == b_prefix_removed and a["自然村"] != a_prefix_removed:
        keep, delete = b, a
    elif len(a["自然村"]) <= len(b["自然村"]):
        keep, delete = a, b
    else:
        keep, delete = b, a

    transfer_dialect = ""
    if not keep["方言分布"] and delete["方言分布"]:
        transfer_dialect = delete["方言分布"]

    return {
        "proposal_type": "admin_prefix_duplicate",
        "action": "keep_short_no_admin_prefix_delete_prefixed",
        "confidence": "high",
        "市级": keep["市级"],
        "区县级": keep["区县级"],
        "乡镇级": keep["乡镇级"],
        "行政村": keep["行政村"],
        "keep_rowid": keep["rowid"],
        "keep_自然村": keep["自然村"],
        "keep_拼音": keep["拼音"],
        "keep_方言分布": keep["方言分布"],
        "delete_rowid": delete["rowid"],
        "delete_自然村": delete["自然村"],
        "delete_拼音": delete["拼音"],
        "delete_方言分布": delete["方言分布"],
        "dialect_transfer_to_keep": transfer_dialect,
        "distance_m": pair["distance_m"],
        "rules": pair["rules"],
        "reason": "同一行政村内，长名去行政村前缀后等于短名",
    }


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    rows = load_rows(conn)
    proposals = []
    with PAIR_PATH.open(encoding="utf-8") as f:
        for pair in csv.DictReader(f):
            proposal = prefix_proposal(pair, rows)
            if proposal:
                proposals.append(proposal)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "proposal_type", "action", "confidence", "市级", "区县级", "乡镇级", "行政村",
        "keep_rowid", "keep_自然村", "keep_拼音", "keep_方言分布",
        "delete_rowid", "delete_自然村", "delete_拼音", "delete_方言分布",
        "dialect_transfer_to_keep", "distance_m", "rules", "reason",
    ]
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(proposals)

    stats = Counter()
    for proposal in proposals:
        stats["total"] += 1
        if proposal["dialect_transfer_to_keep"]:
            stats["needs_dialect_transfer"] += 1
        if proposal["keep_方言分布"] and proposal["delete_方言分布"] and proposal["keep_方言分布"] != proposal["delete_方言分布"]:
            stats["dialect_conflict"] += 1

    print(f"wrote {OUTPUT_PATH}")
    print(dict(stats))
    for proposal in proposals[:30]:
        print(
            proposal["keep_rowid"], proposal["keep_自然村"], "<= keep | delete =>",
            proposal["delete_rowid"], proposal["delete_自然村"],
            "| dialect_transfer:", proposal["dialect_transfer_to_keep"] or "no",
            "|", proposal["市级"], proposal["区县级"], proposal["乡镇级"], proposal["行政村"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
