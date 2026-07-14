"""
Unit tests for future n-gram index generation.
"""

from src.ngram_schema import NGRAM_INDEXES


def test_ngram_indexes_use_space_constrained_query_shapes():
    index_sql = "\n".join(NGRAM_INDEXES)

    assert "idx_ngram_freq_n_position_frequency" in index_sql
    assert "ON ngram_frequency(n, position, frequency DESC)" in index_sql

    assert "idx_regional_ngram_level_n_region_freq" in index_sql
    assert "ON regional_ngram_frequency(level, n, region, frequency DESC)" in index_sql

    assert "idx_ngram_tendency_level_region_lift" in index_sql
    assert "ON ngram_tendency(level, region, lift DESC)" in index_sql


def test_ngram_indexes_keep_baseline_filters_until_benchmarked():
    index_sql = "\n".join(NGRAM_INDEXES)

    assert "idx_regional_ngram_level " in index_sql
    assert "ON regional_ngram_frequency(level)" in index_sql

    assert "idx_regional_ngram_region " in index_sql
    assert "ON regional_ngram_frequency(region)" in index_sql

    assert "idx_ngram_sig_level " in index_sql
    assert "ON ngram_significance(level)" in index_sql


def test_ngram_indexes_do_not_create_redundant_single_column_indexes():
    index_sql = "\n".join(NGRAM_INDEXES)

    redundant_names = [
        "idx_ngram_freq_n ",
        "idx_regional_ngram_city ",
        "idx_regional_ngram_county ",
        "idx_regional_ngram_township ",
        "idx_ngram_tendency_city ",
        "idx_ngram_tendency_county ",
        "idx_ngram_tendency_township ",
        "idx_ngram_tendency_region ",
        "idx_ngram_tendency_lift ",
        "idx_ngram_sig_city ",
        "idx_ngram_sig_county ",
        "idx_ngram_sig_township ",
    ]

    for name in redundant_names:
        assert name not in index_sql
