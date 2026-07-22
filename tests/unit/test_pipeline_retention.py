import sqlite3

from src.pipeline_config import load_pipeline_config
from src.pipeline_retention import apply_retention_policy, retention_policy_from_config


def test_national_retention_policy_drops_compact_targets_only():
    config = load_pipeline_config("config/pipeline.national.json")

    policy = retention_policy_from_config(config)

    assert policy.enabled is True
    assert "全国自然村_预处理" in policy.drop_tables
    assert "village_features" in policy.drop_tables
    assert "village_ngrams" in policy.drop_tables
    assert "全国自然村" not in policy.drop_tables
    assert "char_similarity" not in policy.drop_tables


def test_guangdong_retention_policy_is_disabled():
    config = load_pipeline_config("config/pipeline.guangdong.json")

    policy = retention_policy_from_config(config)

    assert policy.enabled is False
    assert policy.drop_tables == []


def test_apply_retention_policy_dry_run_does_not_drop_tables(tmp_path):
    db_path = tmp_path / "compact.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE 全国自然村 (id INTEGER)")
    conn.execute("CREATE TABLE 全国自然村_预处理 (id INTEGER)")
    conn.execute("CREATE TABLE village_features (id INTEGER)")
    conn.execute("CREATE TABLE char_similarity (id INTEGER)")
    conn.commit()
    conn.close()

    policy = retention_policy_from_config(load_pipeline_config("config/pipeline.national.json"))

    result = apply_retention_policy(str(db_path), policy, dry_run=True)

    assert result.dropped_tables == []
    assert result.missing_tables
    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()
    assert "全国自然村_预处理" in tables
    assert "village_features" in tables
    assert "char_similarity" in tables


def test_apply_retention_policy_drops_targets_and_keeps_raw_and_similarity(tmp_path):
    db_path = tmp_path / "compact.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE 全国自然村 (id INTEGER)")
    conn.execute("CREATE TABLE 全国自然村_预处理 (id INTEGER)")
    conn.execute("CREATE TABLE village_features (id INTEGER)")
    conn.execute("CREATE TABLE char_similarity (id INTEGER)")
    conn.commit()
    conn.close()

    policy = retention_policy_from_config(load_pipeline_config("config/pipeline.national.json"))

    result = apply_retention_policy(str(db_path), policy, dry_run=False)

    assert "全国自然村_预处理" in result.dropped_tables
    assert "village_features" in result.dropped_tables
    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()
    assert "全国自然村" in tables
    assert "char_similarity" in tables
    assert "全国自然村_预处理" not in tables
    assert "village_features" not in tables
