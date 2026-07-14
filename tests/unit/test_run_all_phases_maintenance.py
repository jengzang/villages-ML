"""
Unit tests for run_all_phases database maintenance.
"""

import sqlite3

from run_all_phases import run_database_maintenance


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
