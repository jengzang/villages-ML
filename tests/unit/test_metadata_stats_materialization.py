"""
Unit tests for metadata statistics materialization.
"""

import sqlite3

from scripts.preprocessing.create_preprocessed_table import materialize_metadata_stats
from src.schema import DEFAULT_SCHEMA as S


def _create_preprocessed_sample(conn):
    conn.execute(
        f"""
        CREATE TABLE {S.preprocessed_table} (
            {S.city_col} TEXT,
            {S.county_col} TEXT,
            {S.township_col} TEXT,
            {S.village_name_col_normalized} TEXT,
            {S.char_set_col} TEXT,
            {S.village_id_col} TEXT
        )
        """
    )
    conn.executemany(
        f"""
        INSERT INTO {S.preprocessed_table}
            ({S.city_col}, {S.county_col}, {S.township_col},
             {S.village_name_col_normalized}, {S.char_set_col}, {S.village_id_col})
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("广州市", "天河区", "五山街道", "上村", '["上","村"]', "v_1"),
            ("广州市", "天河区", "五山街道", "下村", '["下","村"]', "v_2"),
            ("广州市", "越秀区", "北京街道", "东村", '["东","村"]', "v_3"),
            ("深圳市", "南山区", "粤海街道", "海村", '["海","村"]', "v_4"),
        ],
    )
    conn.commit()


def test_materialize_metadata_stats_creates_overview_and_hierarchy_tables():
    conn = sqlite3.connect(":memory:")
    _create_preprocessed_sample(conn)

    materialize_metadata_stats(conn, data_version="unit_test")

    overview = conn.execute(
        """
        SELECT total_villages, total_cities, total_counties, total_townships,
               unique_characters, data_version
        FROM metadata_overview_stats
        """
    ).fetchone()
    assert overview == (4, 2, 3, 3, 5, "unit_test")

    rows = conn.execute(
        """
        SELECT level, name, city, county, township, parent, village_count, sort_key
        FROM region_hierarchy_stats
        ORDER BY level, sort_key
        """
    ).fetchall()

    assert ("city", "广州市", "广州市", None, None, None, 3, "广州市") in rows
    assert ("county", "天河区", "广州市", "天河区", None, "广州市", 2, "广州市|天河区") in rows
    assert (
        "township",
        "五山街道",
        "广州市",
        "天河区",
        "五山街道",
        "天河区",
        2,
        "广州市|天河区|五山街道",
    ) in rows
    assert len(rows) == 8

    preprocessed_columns = [
        row[1] for row in conn.execute(f"PRAGMA table_info({S.preprocessed_table})").fetchall()
    ]
    assert "total_villages" not in preprocessed_columns
    assert "village_count" not in preprocessed_columns
