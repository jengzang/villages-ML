"""Unit tests for text cleaning functionality."""

import pytest
from src.preprocessing.text_cleaner import (
    is_valid_chinese_char,
    remove_parenthetical_notes,
    extract_chinese_chars,
    normalize_village_name
)


class TestIsValidChineseChar:
    """Test Chinese character validation."""

    def test_common_chinese_chars(self):
        """Test common Chinese characters."""
        assert is_valid_chinese_char('村')
        assert is_valid_chinese_char('新')
        assert is_valid_chinese_char('大')
        assert is_valid_chinese_char('石')

    def test_rare_chinese_chars(self):
        """Test rare CJK Extension characters."""
        assert is_valid_chinese_char('㘵')  # CJK Extension A
        assert is_valid_chinese_char('㙟')  # CJK Extension A

    def test_non_chinese_chars(self):
        """Test non-Chinese characters."""
        assert not is_valid_chinese_char('a')
        assert not is_valid_chinese_char('1')
        assert not is_valid_chinese_char('(')
        assert not is_valid_chinese_char(' ')

    def test_empty_string(self):
        """Test empty string."""
        assert not is_valid_chinese_char('')

    def test_multi_char_string(self):
        """Test multi-character string."""
        assert not is_valid_chinese_char('村村')


class TestRemoveParentheticalNotes:
    """Test parenthetical note removal."""

    def test_remove_chinese_brackets(self):
        """Test removal of Chinese brackets."""
        result, had_brackets = remove_parenthetical_notes('大（土布）')
        assert result == '大'
        assert had_brackets is True

    def test_remove_english_brackets(self):
        """Test removal of English brackets."""
        result, had_brackets = remove_parenthetical_notes('大(土布)')
        assert result == '大'
        assert had_brackets is True

    def test_no_brackets(self):
        """Test name without brackets."""
        result, had_brackets = remove_parenthetical_notes('石头村')
        assert result == '石头村'
        assert had_brackets is False

    def test_multiple_brackets(self):
        """Test multiple bracket pairs."""
        result, had_brackets = remove_parenthetical_notes('大(土布)新(村)')
        assert result == '大新'
        assert had_brackets is True

    def test_empty_brackets(self):
        """Test empty brackets."""
        result, had_brackets = remove_parenthetical_notes('村()')
        assert result == '村'
        assert had_brackets is True


class TestExtractChineseChars:
    """Test Chinese character extraction."""

    def test_pure_chinese(self):
        """Test pure Chinese text."""
        assert extract_chinese_chars('石头村') == '石头村'

    def test_mixed_with_numbers(self):
        """Test text with numbers."""
        assert extract_chinese_chars('21公里村') == '公里村'

    def test_mixed_with_letters(self):
        """Test text with English letters."""
        assert extract_chinese_chars('ABC村DEF') == '村'

    def test_mixed_with_punctuation(self):
        """Test text with punctuation."""
        assert extract_chinese_chars('村、新-大') == '村新大'

    def test_rare_chars(self):
        """Test rare CJK Extension characters."""
        assert extract_chinese_chars('㘵丁') == '㘵丁'

    def test_empty_string(self):
        """Test empty string."""
        assert extract_chinese_chars('') == ''

    def test_no_chinese(self):
        """Test text with no Chinese characters."""
        assert extract_chinese_chars('123ABC') == ''


class TestNormalizeVillageName:
    """Test full normalization pipeline."""

    def test_normal_name(self):
        """Test normal village name."""
        result = normalize_village_name('石头村')
        assert result.clean_name == '石头村'
        assert result.is_valid is True
        assert result.had_brackets is False
        assert result.had_noise is False

    def test_name_with_brackets(self):
        """Test name with brackets."""
        result = normalize_village_name('大(土布)')
        assert result.clean_name == '大'
        assert result.is_valid is True
        assert result.had_brackets is True

    def test_name_with_numbers(self):
        """Test name with numbers."""
        result = normalize_village_name('21公里村')
        assert result.clean_name == '公里村'
        assert result.is_valid is True
        assert result.had_noise is True

    def test_null_name(self):
        """Test null name."""
        result = normalize_village_name(None)
        assert result.is_valid is False
        assert result.invalid_reason == 'null_or_empty'

    def test_empty_name(self):
        """Test empty name."""
        result = normalize_village_name('')
        assert result.is_valid is False
        assert result.invalid_reason == 'null_or_empty'

    def test_name_becomes_empty_after_cleaning(self):
        """Test name that becomes empty after cleaning."""
        result = normalize_village_name('123ABC')
        assert result.is_valid is False
        assert result.invalid_reason == 'no_chinese_chars'

    def test_name_too_short(self):
        """Test name that's too short after cleaning."""
        result = normalize_village_name('村', min_name_length=2)
        assert result.is_valid is False
        assert 'too_short' in result.invalid_reason

    def test_keep_all_brackets_mode(self):
        """Test keeping brackets."""
        result = normalize_village_name('大(土布)', bracket_mode='keep_all')
        assert result.clean_name == '大土布'
        assert result.had_brackets is False
