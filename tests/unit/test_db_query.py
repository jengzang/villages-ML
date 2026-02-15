"""
Unit tests for database query module.
"""

import pytest
import sqlite3
import tempfile
import pandas as pd
from pathlib import Path
from src.data.db_writer import (
    create_analysis_tables,
    save_run_metadata,
    save_global_frequency,
    save_regional_frequency,
    save_regional_tendency
)
from src.data.db_query import (
    get_latest_run_id,
    get_global_frequency,
    get_regional_frequency,
    get_char_tendency_by_region,
    get_top_polarized_chars,
    get_region_tendency_profile,
    get_all_runs
)


@pytest.fixture
def populated_db():
    """Create a temporary database with test data."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    create_analysis_tables(conn)

    # Add test run metadata
    metadata = {
        'created_at': 1234567890.0,
        'total_villages': 10000,
        'valid_villages': 9500,
        'unique_chars': 100,
        'config': {},
        'status': 'completed'
    }
    save_run_metadata(conn, 'test_run', metadata)

    # Add global frequency data
    global_df = pd.DataFrame({
        'char': ['村', '新', '大'],
        'village_count': [1000, 800, 600],
        'total_villages': [10000, 10000, 10000],
        'frequency': [0.1, 0.08, 0.06],
        'rank': [1, 2, 3]
    })
    save_global_frequency(conn, 'test_run', global_df)

    # Add regional frequency data
    regional_df = pd.DataFrame({
        'region_level': ['city', 'city', 'city'],
        'region_name': ['广州市', '广州市', '深圳市'],
        'char': ['村', '新', '村'],
        'village_count': [500, 400, 400],
        'total_villages': [5000, 5000, 4000],
        'frequency': [0.1, 0.08, 0.1],
        'rank_within_region': [1, 2, 1]
    })
    save_regional_frequency(conn, 'test_run', regional_df)

    # Add tendency data
    tendency_df = pd.DataFrame({
        'region_level': ['city', 'city'],
        'region_name': ['广州市', '深圳市'],
        'char': ['村', '村'],
        'village_count': [500, 400],
        'total_villages': [5000, 4000],
        'frequency': [0.1, 0.1],
        'rank_within_region': [1, 1],
        'global_village_count': [1000, 1000],
        'global_frequency': [0.1, 0.1],
        'lift': [1.0, 1.0],
        'log_lift': [0.0, 0.0],
        'log_odds': [0.0, 0.0],
        'z_score': [0.0, 0.0],
        'support_flag': [1, 1],
        'rank_overrepresented': [1, 1],
        'rank_underrepresented': [None, None]
    })
    save_regional_tendency(conn, 'test_run', tendency_df)

    yield conn

    conn.close()
    Path(db_path).unlink()


def test_get_latest_run_id(populated_db):
    """Test getting latest run ID."""
    run_id = get_latest_run_id(populated_db)
    assert run_id == 'test_run'


def test_get_global_frequency(populated_db):
    """Test querying global frequency."""
    df = get_global_frequency(populated_db, 'test_run', top_n=2)
    assert len(df) == 2
    assert df.iloc[0]['char'] == '村'
    assert df.iloc[0]['rank'] == 1


def test_get_regional_frequency(populated_db):
    """Test querying regional frequency."""
    # Query all regions
    df = get_regional_frequency(populated_db, 'test_run', 'city')
    assert len(df) == 3

    # Query specific region
    df = get_regional_frequency(populated_db, 'test_run', 'city', '广州市')
    assert len(df) == 2
    assert all(df['region_name'] == '广州市')


def test_get_char_tendency_by_region(populated_db):
    """Test querying character tendency across regions."""
    df = get_char_tendency_by_region(populated_db, 'test_run', '村', 'city')
    assert len(df) == 2
    assert all(df['char'] == '村')


def test_get_top_polarized_chars(populated_db):
    """Test querying top polarized characters."""
    df = get_top_polarized_chars(populated_db, 'test_run', 'city', top_n=2)
    assert len(df) <= 2


def test_get_region_tendency_profile(populated_db):
    """Test querying region tendency profile."""
    df = get_region_tendency_profile(populated_db, 'test_run', 'city', '广州市', top_n=1)
    assert len(df) == 1
    assert df.iloc[0]['char'] == '村'


def test_get_all_runs(populated_db):
    """Test querying all runs."""
    df = get_all_runs(populated_db)
    assert len(df) == 1
    assert df.iloc[0]['run_id'] == 'test_run'