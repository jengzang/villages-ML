import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pipelines.feature_materialization_pipeline import write_village_features
from src.semantic.lexicon_loader import SemanticLexicon
from src.schema import get_schema


def test_write_village_features_uses_configured_schema_for_id_mapping():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE 全国自然村_预处理 (
            省级 TEXT,
            地级 TEXT,
            县级 TEXT,
            村委会 TEXT,
            自然村_去前缀 TEXT,
            village_id TEXT
        )
    """)
    lexicon = SemanticLexicon("data/semantic_lexicon_national_v1.json")
    semantic_columns = ",\n            ".join(
        f"{column} INTEGER NOT NULL DEFAULT 0"
        for column in lexicon.get_column_names()
    )
    conn.execute(f"""
        CREATE TABLE village_features (
            village_id TEXT PRIMARY KEY,
            run_id TEXT,
            city TEXT,
            county TEXT,
            town TEXT,
            village_committee TEXT,
            village_name TEXT NOT NULL,
            pinyin TEXT,
            name_length INTEGER NOT NULL,
            suffix_1 TEXT,
            suffix_2 TEXT,
            suffix_3 TEXT,
            prefix_1 TEXT,
            prefix_2 TEXT,
            prefix_3 TEXT,
            {semantic_columns},
            kmeans_cluster_id INTEGER,
            dbscan_cluster_id INTEGER,
            gmm_cluster_id INTEGER,
            has_valid_chars INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute(
        "INSERT INTO 全国自然村_预处理 VALUES (?, ?, ?, ?, ?, ?)",
        ("广东省", "广州市", "番禺区", "测试村委会", "水口", "nat_001"),
    )

    df = pd.DataFrame([
        {
            "city": "广东省",
            "county": "广州市",
            "town": "番禺区",
            "village_committee": "测试村委会",
            "village_name": "水口",
            "pinyin": "",
            "name_length": 2,
            "suffix_1": "口",
            "suffix_2": "水口",
            "suffix_3": None,
            "prefix_1": "水",
            "prefix_2": "水口",
            "prefix_3": None,
            **{column: 0 for column in lexicon.get_column_names()},
            "kmeans_cluster_id": None,
            "dbscan_cluster_id": None,
            "gmm_cluster_id": None,
            "has_valid_chars": 1,
        }
    ])
    df.loc[0, "sem_water"] = 1

    write_village_features(
        conn,
        "run_test",
        df,
        lexicon_path="data/semantic_lexicon_national_v1.json",
        schema=get_schema("national"),
    )

    row = conn.execute("SELECT village_id FROM village_features").fetchone()
    assert row == ("nat_001",)
