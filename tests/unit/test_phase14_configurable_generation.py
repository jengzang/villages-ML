import pytest

from scripts.core import phase14_semantic_composition as phase14


def test_skip_village_structures_avoids_village_structure_step(monkeypatch, tmp_path):
    db_path = tmp_path / "phase14.db"
    called = []

    for name in [
        "step1_create_tables",
        "step2_analyze_compositions",
        "step3_calculate_pmi",
        "step4_detect_patterns",
        "step5_detect_conflicts",
        "step7_generate_semantic_indices_detailed",
    ]:
        monkeypatch.setattr(phase14, name, lambda *args, **kwargs: None)

    def fail_if_called(*args, **kwargs):
        called.append((args, kwargs))
        pytest.fail("village_semantic_structure should be skipped")

    monkeypatch.setattr(phase14, "step6_extract_village_structures", fail_if_called)

    phase14.main([
        "--db-path",
        str(db_path),
        "--skip-village-structures",
    ])

    assert called == []


def test_skip_village_structures_does_not_create_empty_village_structure_table(tmp_path):
    db_path = tmp_path / "phase14.db"

    phase14.step1_create_tables(str(db_path), exclude_tables={"village_semantic_structure"})

    import sqlite3

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    indexes = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        if row[0]
    }
    conn.close()

    assert "village_semantic_structure" not in tables
    assert "idx_village_semantic_id" not in indexes
    assert "semantic_bigrams" in tables
