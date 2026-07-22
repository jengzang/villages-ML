"""
Unit tests for run_all_phases database maintenance.
"""

import sqlite3
import subprocess
from pathlib import Path

from run_all_phases import run_database_maintenance


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_database_maintenance_runs_analyze_and_optimize(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("CREATE INDEX idx_sample_value ON sample(value)")
    conn.executemany("INSERT INTO sample(value) VALUES (?)", [("a",), ("b",), ("c",)])
    conn.commit()
    conn.close()

    assert run_database_maintenance(str(db_path), run_vacuum=False)

    conn = sqlite3.connect(db_path)
    try:
        stat_tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_stat1'"
        ).fetchall()
        assert stat_tables == [("sqlite_stat1",)]
    finally:
        conn.close()


def test_database_maintenance_can_run_vacuum(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO sample(value) VALUES ('a')")
    conn.commit()
    conn.close()

    assert run_database_maintenance(str(db_path), run_vacuum=True)


def test_vacuum_can_run_as_standalone_maintenance_command(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO sample(value) VALUES ('a')")
    conn.commit()
    conn.close()

    result = subprocess.run(
        [
            str(PROJECT_ROOT / ".venv/bin/python"),
            "run_all_phases.py",
            "--db-path",
            str(db_path),
            "--vacuum",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "Database Maintenance" in result.stdout
    assert "VACUUM completed" in result.stdout
    assert "Phase  " not in result.stdout


def test_standalone_vacuum_respects_dry_run(tmp_path):
    db_path = tmp_path / "missing.db"

    result = subprocess.run(
        [
            str(PROJECT_ROOT / ".venv/bin/python"),
            "run_all_phases.py",
            "--db-path",
            str(db_path),
            "--vacuum",
            "--dry-run",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "--vacuum (dry-run)" in result.stdout
    assert not db_path.exists()
