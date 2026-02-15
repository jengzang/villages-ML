# -*- coding: utf-8 -*-
"""Unit tests for character set extraction."""

import pytest
import json
import pandas as pd
from src.preprocessing.char_extractor import extract_char_set, process_village_batch


class TestExtractCharSet:
    """Test character set extraction with deduplication."""

    def test_unique_chars(self):
        """Test name with all unique characters."""
        result = extract_char_set('石头村')
        assert result == {'石', '头', '村'}

    def test_repeated_chars(self):
        """Test name with repeated characters - CRITICAL TEST."""
        # This is the key requirement: per-village deduplication
        result = extract_char_set('石石岭岭村')
        assert result == {'石', '岭', '村'}
        assert len(result) == 3  # Not 5

    def test_single_char(self):
        """Test single character name."""
        result = extract_char_set('村')
        assert result == {'村'}

    def test_empty_string(self):
        """Test empty string."""
        result = extract_char_set('')
        assert result == set()

    def test_all_same_char(self):
        """Test name with all same character."""
        result = extract_char_set('石石石')
        assert result == {'石'}
        assert len(result) == 1


class TestProcessVillageBatch:
    """Test batch processing of villages."""

    def test_basic_batch(self):
        """Test processing a basic batch."""
        df = pd.DataFrame({
            '市级': ['广州市', '深圳市'],
            '县区级': ['天河区', '南山区'],
            '乡镇': ['某镇', '某镇'],
            '自然村': ['石头村', '新村']
        })

        result = process_village_batch(df)

        assert len(result) == 2
        assert 'clean_name' in result.columns
        assert 'char_set_json' in result.columns
        assert 'is_valid' in result.columns

        # Check first row
        assert result.iloc[0]['clean_name'] == '石头村'
        assert result.iloc[0]['is_valid'] == True
        char_set = set(json.loads(result.iloc[0]['char_set_json']))
        assert char_set == {'石', '头', '村'}

    def test_batch_with_brackets(self):
        """Test batch with bracketed names."""
        df = pd.DataFrame({
            '市级': ['广州市'],
            '县区级': ['天河区'],
            '乡镇': ['某镇'],
            '自然村': ['大(土布)']
        })

        result = process_village_batch(df)

        assert result.iloc[0]['clean_name'] == '大'
        assert result.iloc[0]['had_brackets'] == True
        assert result.iloc[0]['is_valid'] == True

    def test_batch_with_invalid_names(self):
        """Test batch with invalid names."""
        df = pd.DataFrame({
            '市级': ['广州市', '深圳市', '珠海市'],
            '县区级': ['天河区', '南山区', '香洲区'],
            '乡镇': ['某镇', '某镇', '某镇'],
            '自然村': ['石头村', None, '123']
        })

        result = process_village_batch(df)

        assert len(result) == 3
        assert result.iloc[0]['is_valid'] == True
        assert result.iloc[1]['is_valid'] == False
        assert result.iloc[2]['is_valid'] == False

    def test_char_set_deduplication(self):
        """Test that character sets are properly deduplicated."""
        df = pd.DataFrame({
            '市级': ['广州市'],
            '县区级': ['天河区'],
            '乡镇': ['某镇'],
            '自然村': ['石石岭岭村']
        })

        result = process_village_batch(df)

        # Check deduplication
        assert result.iloc[0]['name_len'] == 5  # Original length
        assert result.iloc[0]['unique_char_cnt'] == 3  # Deduplicated count

        char_set = set(json.loads(result.iloc[0]['char_set_json']))
        assert char_set == {'石', '岭', '村'}

    def test_char_set_json_format(self):
        """Test that char_set_json is properly formatted."""
        df = pd.DataFrame({
            '市级': ['广州市'],
            '县区级': ['天河区'],
            '乡镇': ['某镇'],
            '自然村': ['村新大']
        })

        result = process_village_batch(df)

        char_set_json = result.iloc[0]['char_set_json']

        # Should be valid JSON
        char_list = json.loads(char_set_json)
        assert isinstance(char_list, list)

        # Should be sorted
        assert char_list == sorted(char_list)

        # Should contain correct characters
        assert set(char_list) == {'村', '新', '大'}
