import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.core.phase12_ngram_analysis import (
    step1_create_tables,
    step2_extract_global_ngrams,
    step3_extract_regional_ngrams,
    step3_5_calculate_regional_totals_raw,
    step4_calculate_tendency,
    step7_detect_patterns,
)


def _create_preprocessed_table(conn):
    conn.execute(
        """
        CREATE TABLE 广东省自然村_预处理 (
            市级 TEXT,
            区县级 TEXT,
            乡镇级 TEXT,
            村委会 TEXT,
            自然村_去前缀 TEXT,
            字符数量 INTEGER
        )
        """
    )
    rows = [
        ("广州市", "天河区", "五山街道", "五山村委", "新村", 2),
        ("广州市", "越秀区", "北京街道", "北京村委", "老村", 2),
        ("深圳市", "南山区", "粤海街道", "粤海村委", "新屋", 2),
    ]
    suffix_chars = "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民"
    rows.extend(
        ("广州市", "天河区", "五山街道", "五山村委", f"{char}村", 2)
        for char in suffix_chars[:60]
    )
    conn.executemany(
        """
        INSERT INTO 广东省自然村_预处理
            (市级, 区县级, 乡镇级, 村委会, 自然村_去前缀, 字符数量)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def test_phase12_generation_honors_n_values_positions_and_region_levels(tmp_path):
    db_path = tmp_path / "villages.db"
    conn = sqlite3.connect(db_path)
    _create_preprocessed_table(conn)
    conn.close()

    step1_create_tables(str(db_path))
    step2_extract_global_ngrams(str(db_path), n_values=[2], positions=["all"])
    step3_extract_regional_ngrams(str(db_path), n_values=[2], regional_levels=["city"], positions=["all"])
    step3_5_calculate_regional_totals_raw(str(db_path))
    step4_calculate_tendency(str(db_path), regional_levels=["city"])
    step7_detect_patterns(str(db_path), n_values=[2], min_freq_by_n={2: 1})

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT DISTINCT n FROM ngram_frequency").fetchall() == [(2,)]
    assert conn.execute("SELECT DISTINCT position FROM ngram_frequency").fetchall() == [("all",)]
    assert conn.execute("SELECT DISTINCT level FROM regional_ngram_frequency").fetchall() == [("city",)]
    assert conn.execute("SELECT DISTINCT level FROM ngram_tendency").fetchall() == [("city",)]
    assert conn.execute("SELECT DISTINCT n FROM structural_patterns").fetchall() == [(2,)]
    conn.close()
