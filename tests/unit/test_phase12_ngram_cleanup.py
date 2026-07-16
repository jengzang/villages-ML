import sqlite3
import sys
import types
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

update_run_id_stub = types.ModuleType("utils.update_run_id")
update_run_id_stub.update_active_run_id = lambda *args, **kwargs: None
sys.modules["utils.update_run_id"] = update_run_id_stub

from scripts.core.phase12_ngram_analysis import step6_cleanup_insignificant_data


def _create_ngram_cleanup_tables(conn):
    conn.executescript(
        """
        CREATE TABLE ngram_tendency (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL NOT NULL,
            regional_count INTEGER NOT NULL,
            regional_total INTEGER NOT NULL,
            regional_total_raw INTEGER,
            global_count INTEGER NOT NULL,
            global_total INTEGER NOT NULL,
            PRIMARY KEY (level, city, county, township, ngram, n, position)
        );
        CREATE TABLE regional_ngram_frequency (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (level, city, county, township, ngram, n, position)
        );
        CREATE TABLE ngram_significance (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            chi2 REAL NOT NULL,
            p_value REAL NOT NULL,
            cramers_v REAL NOT NULL,
            is_significant INTEGER NOT NULL,
            total_before_filter INTEGER,
            PRIMARY KEY (level, city, county, township, ngram, n, position)
        );
        """
    )


def _insert_tendency(conn, ngram, n, position, regional_count, global_count):
    row = (
        "township",
        "广州市",
        "天河区",
        "五山街道",
        "五山街道",
        ngram,
        n,
        position,
        2.0,
        1.0,
        3.0,
        regional_count,
        100,
        100,
        global_count,
        1000,
    )
    conn.execute(
        """
        INSERT INTO ngram_tendency
        (level, city, county, township, region, ngram, n, position, lift, log_odds,
         z_score, regional_count, regional_total, regional_total_raw, global_count, global_total)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )
    conn.execute(
        """
        INSERT INTO regional_ngram_frequency
        (level, city, county, township, region, ngram, n, position, frequency, total_count, percentage)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row[:8] + (regional_count, 100, regional_count),
    )


def _insert_significance(conn, ngram, n, position):
    conn.execute(
        """
        INSERT INTO ngram_significance
        (level, city, county, township, region, ngram, n, position, chi2, p_value,
         cramers_v, is_significant, total_before_filter)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "township",
            "广州市",
            "天河区",
            "五山街道",
            "五山街道",
            ngram,
            n,
            position,
            9.0,
            0.01,
            0.2,
            1,
            100,
        ),
    )


def test_cleanup_uses_strict_n_position_match_and_support_thresholds(tmp_path):
    db_path = tmp_path / "villages.db"
    conn = sqlite3.connect(db_path)
    _create_ngram_cleanup_tables(conn)
    _insert_tendency(conn, "新村", 2, "all", regional_count=3, global_count=10)
    _insert_significance(conn, "新村", 2, "all")
    _insert_tendency(conn, "新村", 2, "prefix", regional_count=3, global_count=10)
    _insert_tendency(conn, "孤例", 2, "all", regional_count=1, global_count=10)
    _insert_significance(conn, "孤例", 2, "all")
    _insert_tendency(conn, "稀有", 2, "all", regional_count=3, global_count=2)
    _insert_significance(conn, "稀有", 2, "all")
    conn.commit()
    conn.close()

    step6_cleanup_insignificant_data(
        str(db_path),
        min_regional_count_by_n={2: 3},
        min_global_count_by_n={2: 10},
    )

    conn = sqlite3.connect(db_path)
    tendency_rows = conn.execute(
        "SELECT ngram, n, position FROM ngram_tendency ORDER BY ngram, position"
    ).fetchall()
    frequency_rows = conn.execute(
        "SELECT ngram, n, position FROM regional_ngram_frequency ORDER BY ngram, position"
    ).fetchall()
    significance_rows = conn.execute(
        "SELECT ngram, n, position FROM ngram_significance ORDER BY ngram, position"
    ).fetchall()
    conn.close()

    assert tendency_rows == [("新村", 2, "all")]
    assert frequency_rows == [("新村", 2, "all")]
    assert significance_rows == [("新村", 2, "all")]
