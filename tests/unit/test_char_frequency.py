"""Unit tests for character frequency computation."""

import pytest
import json
import pandas as pd
from src.analysis.char_frequency import (
    compute_char_frequency_global,
    compute_char_frequency_by_region,
    calculate_lift
)


class TestComputeCharFrequencyGlobal:
    """Test global character frequency computation."""

    def test_basic_frequency(self):
        """Test basic frequency computation."""
        # Create test data: 3 villages
        # Village 1: {石, 头, 村}
        # Village 2: {新, 村}
        # Village 3: {大, 村}
        # Expected: 村 appears in 3/3 = 100%, 石 in 1/3 = 33.3%, etc.

        df = pd.DataFrame({
            'is_valid': [True, True, True],
            'char_set_json': [
                json.dumps(['石', '头', '村']),
                json.dumps(['新', '村']),
                json.dumps(['大', '村'])
            ]
        })

        result = compute_char_frequency_global(df)

        # Check structure
        assert 'char' in result.columns
        assert 'village_count' in result.columns
        assert 'frequency' in result.columns
        assert 'rank' in result.columns

        # Check counts
        village_char = result[result['char'] == '村'].iloc[0]
        assert village_char['village_count'] == 3
        assert village_char['frequency'] == 1.0
        assert village_char['rank'] == 1  # Most common

        stone_char = result[result['char'] == '石'].iloc[0]
        assert stone_char['village_count'] == 1
        assert stone_char['frequency'] == pytest.approx(1/3)

    def test_deduplication_effect(self):
        """Test that repeated chars within village are counted once."""
        # Village with repeated chars: 石石岭岭村
        # Should count 石 once, not twice

        df = pd.DataFrame({
            'is_valid': [True, True],
            'char_set_json': [
                json.dumps(['石', '岭', '村']),  # Already deduplicated
                json.dumps(['新', '村'])
            ]
        })

        result = compute_char_frequency_global(df)

        stone_char = result[result['char'] == '石'].iloc[0]
        assert stone_char['village_count'] == 1  # Not 2
        assert stone_char['frequency'] == 0.5

    def test_invalid_villages_excluded(self):
        """Test that invalid villages are excluded."""
        df = pd.DataFrame({
            'is_valid': [True, False, True],
            'char_set_json': [
                json.dumps(['村']),
                json.dumps(['石']),  # Invalid, should be excluded
                json.dumps(['村'])
            ]
        })

        result = compute_char_frequency_global(df)

        # Only 2 valid villages
        village_char = result[result['char'] == '村'].iloc[0]
        assert village_char['total_villages'] == 2
        assert village_char['village_count'] == 2

        # 石 should not appear (was in invalid village)
        assert '石' not in result['char'].values

    def test_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame({
            'is_valid': [],
            'char_set_json': []
        })

        result = compute_char_frequency_global(df)
        assert len(result) == 0


class TestComputeCharFrequencyByRegion:
    """Test regional character frequency computation."""

    def test_city_level_frequency(self):
        """Test city-level frequency computation."""
        df = pd.DataFrame({
            '市级': ['广州市', '广州市', '深圳市'],
            '县区级': ['天河区', '越秀区', '南山区'],
            '乡镇': ['镇1', '镇2', '镇3'],
            'is_valid': [True, True, True],
            'char_set_json': [
                json.dumps(['石', '村']),
                json.dumps(['新', '村']),
                json.dumps(['大', '村'])
            ]
        })

        result = compute_char_frequency_by_region(df, 'city')

        # Check structure
        assert 'region_level' in result.columns
        assert 'region_name' in result.columns
        assert 'char' in result.columns
        assert 'village_count' in result.columns
        assert 'total_villages' in result.columns
        assert 'frequency' in result.columns

        # Check 广州市
        gz_data = result[result['region_name'] == '广州市']
        gz_village = gz_data[gz_data['char'] == '村'].iloc[0]
        assert gz_village['village_count'] == 2
        assert gz_village['total_villages'] == 2
        assert gz_village['frequency'] == 1.0

        # Check 深圳市
        sz_data = result[result['region_name'] == '深圳市']
        sz_village = sz_data[sz_data['char'] == '村'].iloc[0]
        assert sz_village['village_count'] == 1
        assert sz_village['total_villages'] == 1

    def test_rank_within_region(self):
        """Test ranking within each region."""
        df = pd.DataFrame({
            '市级': ['广州市', '广州市', '广州市'],
            '县区级': ['天河区', '越秀区', '海珠区'],
            '乡镇': ['镇1', '镇2', '镇3'],
            'is_valid': [True, True, True],
            'char_set_json': [
                json.dumps(['村']),
                json.dumps(['村']),
                json.dumps(['新'])
            ]
        })

        result = compute_char_frequency_by_region(df, 'city')

        gz_data = result[result['region_name'] == '广州市'].sort_values('rank_within_region')

        # 村 appears in 2/3 villages, should be rank 1
        assert gz_data.iloc[0]['char'] == '村'
        assert gz_data.iloc[0]['rank_within_region'] == 1

        # 新 appears in 1/3 villages, should be rank 2
        assert gz_data.iloc[1]['char'] == '新'
        assert gz_data.iloc[1]['rank_within_region'] == 2


class TestCalculateLift:
    """Test lift calculation."""

    def test_basic_lift(self):
        """Test basic lift calculation."""
        # Global: 村 appears in 50% of villages
        global_freq = pd.DataFrame({
            'char': ['村', '石'],
            'village_count': [50, 25],
            'frequency': [0.5, 0.25]
        })

        # Regional: 村 appears in 80% of villages in this region
        regional_freq = pd.DataFrame({
            'region_name': ['广州市', '广州市'],
            'char': ['村', '石'],
            'village_count': [80, 20],
            'total_villages': [100, 100],
            'frequency': [0.8, 0.2]
        })

        result = calculate_lift(regional_freq, global_freq)

        # Check lift for 村
        village_row = result[result['char'] == '村'].iloc[0]
        assert village_row['global_frequency'] == 0.5
        assert village_row['lift_vs_global'] == pytest.approx(0.8 / 0.5)

        # Check lift for 石
        stone_row = result[result['char'] == '石'].iloc[0]
        assert stone_row['lift_vs_global'] == pytest.approx(0.2 / 0.25)

    def test_lift_greater_than_one(self):
        """Test lift > 1 (overrepresented)."""
        global_freq = pd.DataFrame({
            'char': ['村'],
            'village_count': [50],
            'frequency': [0.5]
        })

        regional_freq = pd.DataFrame({
            'region_name': ['广州市'],
            'char': ['村'],
            'village_count': [80],
            'total_villages': [100],
            'frequency': [0.8]
        })

        result = calculate_lift(regional_freq, global_freq)
        assert result.iloc[0]['lift_vs_global'] > 1.0

    def test_lift_less_than_one(self):
        """Test lift < 1 (underrepresented)."""
        global_freq = pd.DataFrame({
            'char': ['村'],
            'village_count': [50],
            'frequency': [0.5]
        })

        regional_freq = pd.DataFrame({
            'region_name': ['广州市'],
            'char': ['村'],
            'village_count': [20],
            'total_villages': [100],
            'frequency': [0.2]
        })

        result = calculate_lift(regional_freq, global_freq)
        assert result.iloc[0]['lift_vs_global'] < 1.0
