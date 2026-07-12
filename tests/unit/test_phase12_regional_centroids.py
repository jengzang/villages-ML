import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.phase12_ngram_analysis import step8_create_optimization_indexes


def test_step8_rebuilds_legacy_regional_centroids_schema(tmp_path):
    db_path = tmp_path / "villages.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE 广东省自然村_预处理 (
            市级 TEXT,
            区县级 TEXT,
            乡镇级 TEXT,
            longitude TEXT,
            latitude TEXT
        )
        """
    )
    cursor.executemany(
        """
        INSERT INTO 广东省自然村_预处理
            (市级, 区县级, 乡镇级, longitude, latitude)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("广州市", "天河区", "五山街道", "113.35", "23.15"),
            ("广州市", "天河区", "五山街道", "113.37", "23.17"),
            ("广州市", "越秀区", "北京街道", "113.26", "23.13"),
        ],
    )
    cursor.execute(
        """
        CREATE TABLE regional_centroids (
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            centroid_lon REAL NOT NULL,
            centroid_lat REAL NOT NULL,
            village_count INTEGER NOT NULL,
            PRIMARY KEY (region_level, region_name)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE ngram_tendency (
            level TEXT,
            ngram TEXT,
            township TEXT,
            lift REAL,
            region TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    step8_create_optimization_indexes(str(db_path))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(regional_centroids)")
    columns = [row[1] for row in cursor.fetchall()]
    assert columns == [
        "region_level",
        "city",
        "county",
        "township",
        "region_name",
        "centroid_lon",
        "centroid_lat",
        "village_count",
    ]

    cursor.execute("SELECT region_level, city, county, township, region_name, village_count FROM regional_centroids")
    rows = set(cursor.fetchall())
    assert ("township", "广州市", "天河区", "五山街道", "五山街道", 2) in rows
    assert ("county", "广州市", "天河区", None, "天河区", 2) in rows
    assert ("city", "广州市", None, None, "广州市", 3) in rows
    conn.close()
