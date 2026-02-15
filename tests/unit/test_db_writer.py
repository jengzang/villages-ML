"""
Unit tests for database writer module.
"""

import pytest
import sqlite3
import tempfile
import pandas as pd
from pathlib import Path
from src.data.db_writer import (
    create_analysis_tables,
    create_indexes,
    save_run_metadata,
    save_global_frequency,
    save_regional_frequency,
    save_regional_tendency
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    yield conn

    conn.close()
    Path(db_path).unlink()


def test_create_analysis_tables(temp_db):
    """Test table creation."""
    create_analysis_tables(temp_db)

    cursor = temp_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert 'analysis_runs' in tables
    assert 'char_frequency_global' in tables
    assert 'char_frequency_regional' in tables
    assert 'regional_tendency' in tables


def test_create_indexes(temp_db):
    """Test index creation."""
    create_analysis_tables(temp_db)
    create_indexes(temp_db)

    cursor = temp_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}

    # Check some key indexes exist
    assert 'idx_global_char' in indexes
    assert 'idx_regional_level' in indexes
    assert 'idx_tendency_lift' in indexes


def test_save_run_metadata(temp_db):
    """Test saving run metadata."""
    create_analysis_tables(temp_db)

    metadata = {
        'created_at': 1234567890.0,
        'total_villages': 100000,
        'valid_villages': 95000,
        'unique_chars': 3000,
        'config': {'test': 'value'},
        'status': 'completed',
        'notes': 'Test run'
    }

    save_run_metadata(temp_db, 'test_run', metadata)

    cursor = temp_db.cursor()
    cursor.execute("SELECT * FROM analysis_runs WHERE run_id='test_run'")
    row = cursor.fetchone()

    assert row is not None
    assert row[0] == 'test_run'
    assert row[2] == 100000  # total_villages


def test_save_global_frequency(temp_db):
    """Test saving global frequency data."""
    create_analysis_tables(temp_db)

    df = pd.DataFrame({
        'char': ['村', '新', '大'],
        'village_count': [1000, 800, 600],
        'total_villages': [10000, 10000, 10000],
        'frequency': [0.1, 0.08, 0.06],
        'rank': [1, 2, 3]
    })

    save_global_frequency(temp_db, 'test_run', df)

    cursor = temp_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM char_frequency_global WHERE run_id='test_run'")
    count = cursor.fetchone()[0]

    assert count == 3


def test_save_regional_frequency(temp_db):
    """Test saving regional frequency data."""
    create_analysis_tables(temp_db)

    df = pd.DataFrame({
        'region_level': ['city', 'city'],
        'region_name': ['广州市', '深圳市'],
        'char': ['村', '村'],
        'village_count': [500, 400],
        'total_villages': [5000, 4000],
        'frequency': [0.1, 0.1],
        'rank_within_region': [1, 1]
    })

    save_regional_frequency(temp_db, 'test_run', df)

    cursor = temp_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM char_frequency_regional WHERE run_id='test_run'")
    count = cursor.fetchone()[0]

    assert count == 2


def test_save_regional_tendency(temp_db):
    """Test saving regional tendency data."""
    create_analysis_tables(temp_db)

    df = pd.DataFrame({
        'region_level': ['city'],
        'region_name': ['广州市'],
        'char': ['村'],
        'village_count': [500],
        'total_villages': [5000],
        'frequency': [0.1],
        'rank_within_region': [1],
        'global_village_count': [1000],
        'global_frequency': [0.05],
        'lift': [2.0],
        'log_lift': [0.693],
        'log_odds': [0.7],
        'z_score': [5.0],
        'support_flag': [1],
        'rank_overrepresented': [1],
        'rank_underrepresented': [None]
    })

    save_regional_tendency(temp_db, 'test_run', df)

    cursor = temp_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM regional_tendency WHERE run_id='test_run'")
    count = cursor.fetchone()[0]

    assert count == 1