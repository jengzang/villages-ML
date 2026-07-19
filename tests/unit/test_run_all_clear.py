import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_clear_dry_run_keeps_profile_raw_table(tmp_path):
    db_path = tmp_path / "national.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE 全国自然村 (id INTEGER)")
    conn.execute("CREATE TABLE derived_table (id INTEGER)")
    conn.commit()
    conn.close()

    result = subprocess.run(
        [
            str(PROJECT_ROOT / ".venv/bin/python"),
            "run_all_phases.py",
            "--config",
            "config/pipeline.national.json",
            "--phases",
            "0",
            "--db-path",
            str(db_path),
            "--skip-dependencies",
            "--clear",
            "--dry-run",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "保留 全国自然村" in result.stdout
    assert "将会删除 1 张衍生表" in result.stdout
