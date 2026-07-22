"""Compact-mode pipeline retention helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class RetentionPolicy:
    """Configured post-run retention cleanup policy."""

    enabled: bool
    drop_tables: list[str]


@dataclass(frozen=True)
class RetentionResult:
    """Result of applying a retention policy."""

    enabled: bool
    dry_run: bool
    dropped_tables: list[str]
    missing_tables: list[str]


def retention_policy_from_config(config: dict[str, Any] | None) -> RetentionPolicy:
    """Build a retention policy from a pipeline profile config."""
    config = config or {}
    retention = config.get("retention") or {}
    enabled = bool(retention.get("enabled", False))
    drop_tables_config = retention.get("drop_tables", [])
    if not isinstance(drop_tables_config, list):
        raise ValueError("retention.drop_tables must be a list")

    drop_tables = []
    for table in drop_tables_config:
        if not isinstance(table, str) or not table:
            raise ValueError("retention.drop_tables entries must be non-empty strings")
        drop_tables.append(table)

    return RetentionPolicy(enabled=enabled, drop_tables=drop_tables)


def apply_retention_policy(
    db_path: str,
    policy: RetentionPolicy,
    dry_run: bool = False,
) -> RetentionResult:
    """Drop tables listed by an enabled retention policy.

    The helper only drops tables explicitly listed by the profile. It never
    infers drop targets from the database.
    """
    if not policy.enabled:
        return RetentionResult(enabled=False, dry_run=dry_run, dropped_tables=[], missing_tables=[])

    db_file = Path(db_path)
    if not db_file.exists():
        if dry_run:
            return RetentionResult(
                enabled=True,
                dry_run=True,
                dropped_tables=[],
                missing_tables=list(policy.drop_tables),
            )
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}

        present_targets = [table for table in policy.drop_tables if table in existing_tables]
        missing_targets = [table for table in policy.drop_tables if table not in existing_tables]

        if dry_run:
            return RetentionResult(
                enabled=True,
                dry_run=True,
                dropped_tables=[],
                missing_tables=missing_targets,
            )

        for table in present_targets:
            cursor.execute(f'DROP TABLE "{table}"')
        conn.commit()

        return RetentionResult(
            enabled=True,
            dry_run=False,
            dropped_tables=present_targets,
            missing_tables=missing_targets,
        )
    finally:
        conn.close()
