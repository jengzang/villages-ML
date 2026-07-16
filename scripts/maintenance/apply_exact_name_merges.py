"""Merge exact same natural-village names within the same administrative village.

Rules:
- Same 市级 + 区县级 + 乡镇级 + 行政村 + 自然村.
- Pairwise coordinate distance must be within the configured threshold.
- Connected components are merged together.
- Keep row priority: has 方言分布 first, then longer 拼音, then lowest rowid.
- Preserve dialect data by writing the union of all non-empty 方言分布 values to
  the kept row.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import time
from collections import defaultdict
from pathlib import Path


DB_PATH = Path("data/villages.db")
RAW_TABLE = "广东省自然村"
AUDIT_TABLE = "cleanup_exact_name_merge_audit"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def dialect_values(value: str) -> list[str]:
    if not value:
        return []
    parts: list[str] = []
    for chunk in value.replace("；", ";").replace("、", ";").split(";"):
        chunk = chunk.strip()
        if chunk and chunk not in parts:
            parts.append(chunk)
    return parts


def merge_dialects(rows: list[dict[str, object]]) -> str:
    values: list[str] = []
    for row in rows:
        for value in dialect_values(clean(row["方言分布"])):
            if value not in values:
                values.append(value)
    return "；".join(values)


def keep_sort_key(row: dict[str, object]) -> tuple[int, int, int]:
    has_dialect = 1 if clean(row["方言分布"]) else 0
    pinyin_len = len(clean(row["拼音"]))
    # Negative rowid because sorted(reverse=True) keeps lowest rowid on ties.
    return has_dialect, pinyin_len, -int(row["rowid"])


def create_audit_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {AUDIT_TABLE} (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            applied_at REAL NOT NULL,
            action TEXT NOT NULL,
            group_key_json TEXT NOT NULL,
            keep_rowid INTEGER NOT NULL,
            delete_rowid INTEGER NOT NULL,
            distance_to_keep_m REAL,
            merged_dialect TEXT,
            keep_row_before_json TEXT NOT NULL,
            delete_row_before_json TEXT NOT NULL,
            component_json TEXT NOT NULL
        )
        """
    )


def load_rows(conn: sqlite3.Connection) -> dict[tuple[str, str, str, str, str], list[dict[str, object]]]:
    conn.row_factory = sqlite3.Row
    groups: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in conn.execute(
        f"""
        SELECT rowid, *
        FROM "{RAW_TABLE}"
        WHERE 自然村 IS NOT NULL AND trim(自然村) != ''
        ORDER BY 市级, 区县级, 乡镇级, 行政村, 自然村, rowid
        """
    ):
        data = dict(row)
        key = (
            clean(data["市级"]),
            clean(data["区县级"]),
            clean(data["乡镇级"]),
            clean(data["行政村"]),
            clean(data["自然村"]),
        )
        groups[key].append(data)
    return groups


def components_within_threshold(
    rows: list[dict[str, object]], max_distance_m: float
) -> list[list[dict[str, object]]]:
    n = len(rows)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    coords = [
        (to_float(row["longitude"]), to_float(row["latitude"]))
        for row in rows
    ]
    for i in range(n):
        lon_i, lat_i = coords[i]
        if lon_i is None or lat_i is None:
            continue
        for j in range(i + 1, n):
            lon_j, lat_j = coords[j]
            if lon_j is None or lat_j is None:
                continue
            if haversine_m(lon_i, lat_i, lon_j, lat_j) <= max_distance_m:
                union(i, j)

    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for idx, row in enumerate(rows):
        grouped[find(idx)].append(row)
    return [component for component in grouped.values() if len(component) > 1]


def distance_between(a: dict[str, object], b: dict[str, object]) -> float | None:
    lon_a, lat_a = to_float(a["longitude"]), to_float(a["latitude"])
    lon_b, lat_b = to_float(b["longitude"]), to_float(b["latitude"])
    if None in (lon_a, lat_a, lon_b, lat_b):
        return None
    return haversine_m(lon_a, lat_a, lon_b, lat_b)  # type: ignore[arg-type]


def apply_merges(db_path: Path, max_distance_m: float, dry_run: bool) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    create_audit_table(conn)
    groups = load_rows(conn)
    applied_at = time.time()
    stats = {
        "duplicate_name_groups": 0,
        "merge_components": 0,
        "deleted_rows": 0,
        "dialect_updates": 0,
        "audit_rows": 0,
    }

    try:
        conn.execute("BEGIN")
        for key, rows in groups.items():
            if len(rows) < 2:
                continue
            components = components_within_threshold(rows, max_distance_m)
            if not components:
                continue
            stats["duplicate_name_groups"] += 1
            for component in components:
                stats["merge_components"] += 1
                keep = sorted(component, key=keep_sort_key, reverse=True)[0]
                deletes = [row for row in component if int(row["rowid"]) != int(keep["rowid"])]
                merged_dialect = merge_dialects(component)
                keep_before = dict(keep)
                component_json = json.dumps(component, ensure_ascii=False)

                if merged_dialect and merged_dialect != clean(keep["方言分布"]):
                    conn.execute(
                        f'UPDATE "{RAW_TABLE}" SET 方言分布 = ? WHERE rowid = ?',
                        (merged_dialect, int(keep["rowid"])),
                    )
                    stats["dialect_updates"] += 1

                for delete in deletes:
                    conn.execute(
                        f"""
                        INSERT INTO {AUDIT_TABLE} (
                            applied_at, action, group_key_json, keep_rowid, delete_rowid,
                            distance_to_keep_m, merged_dialect, keep_row_before_json,
                            delete_row_before_json, component_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            applied_at,
                            "dry_run" if dry_run else "applied",
                            json.dumps(key, ensure_ascii=False),
                            int(keep["rowid"]),
                            int(delete["rowid"]),
                            distance_between(keep, delete),
                            merged_dialect,
                            json.dumps(keep_before, ensure_ascii=False),
                            json.dumps(delete, ensure_ascii=False),
                            component_json,
                        ),
                    )
                    stats["audit_rows"] += 1
                    conn.execute(f'DELETE FROM "{RAW_TABLE}" WHERE rowid = ?', (int(delete["rowid"]),))
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
    parser.add_argument("--max-distance-m", type=float, default=1000.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats = apply_merges(args.db, args.max_distance_m, args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
