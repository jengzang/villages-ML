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


def test_clear_dry_run_does_not_create_missing_database(tmp_path):
    db_path = tmp_path / "missing.db"

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
    assert "将会删除 0 张衍生表" in result.stdout
    assert not db_path.exists()


def test_national_compact_retention_dry_run_lists_drop_targets(tmp_path):
    db_path = tmp_path / "national.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE 全国自然村 (id INTEGER)")
    conn.execute("CREATE TABLE 全国自然村_预处理 (id INTEGER)")
    conn.execute("CREATE TABLE village_features (id INTEGER)")
    conn.execute("CREATE TABLE char_similarity (id INTEGER)")
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
            "--dry-run",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "Compact retention (dry-run)" in result.stdout
    assert "全国自然村_预处理" in result.stdout
    assert "village_features" in result.stdout
    assert "char_similarity" not in result.stdout
