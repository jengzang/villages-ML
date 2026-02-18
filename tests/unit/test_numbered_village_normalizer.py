"""Unit tests for numbered_village_normalizer module."""

import pytest
from src.preprocessing.numbered_village_normalizer import (
    detect_trailing_numeral,
    normalize_numbered_village
)


class TestDetectTrailingNumeral:
    """Test trailing numeral detection."""

    def test_pattern_numeral_village(self):
        """Test pattern: 村名 + 数字 + 村."""
        has_numeral, base, suffix = detect_trailing_numeral("东村一村")
        assert has_numeral
        assert base == "东村"
        assert suffix == "一村"

    def test_pattern_numeral_only(self):
        """Test pattern: 村名 + 数字."""
        has_numeral, base, suffix = detect_trailing_numeral("南岭二")
        assert has_numeral
        assert base == "南岭"
        assert suffix == "二"

    def test_multiple_numerals(self):
        """Test multiple numerals."""
        has_numeral, base, suffix = detect_trailing_numeral("北岗十一村")
        assert has_numeral
        assert base == "北岗"
        assert suffix == "十一村"

    def test_no_numeral(self):
        """Test name without numeral."""
        has_numeral, base, suffix = detect_trailing_numeral("石岭村")
        assert not has_numeral
        assert base == "石岭村"
        assert suffix == ""

    def test_numeral_in_middle(self):
        """Test numeral in middle (not trailing)."""
        has_numeral, base, suffix = detect_trailing_numeral("三角村")
        # Should not detect (numeral not at end)
        # Actually, this will match pattern2 and detect "三角" as base
        # Let's verify the behavior
        has_numeral, base, suffix = detect_trailing_numeral("三角村")
        # The pattern will not match because "三" is at the beginning
        assert not has_numeral

    def test_single_char_base(self):
        """Test single character base name."""
        has_numeral, base, suffix = detect_trailing_numeral("东一")
        assert has_numeral
        assert base == "东"
        assert suffix == "一"

    def test_empty_name(self):
        """Test empty name."""
        has_numeral, base, suffix = detect_trailing_numeral("")
        assert not has_numeral


class TestNormalizeNumberedVillage:
    """Test numbered village normalization."""

    def test_normalize_pattern1(self):
        """Test normalization of pattern 1."""
        result = normalize_numbered_village("东村一村")
        assert result == "东村"

    def test_normalize_pattern2(self):
        """Test normalization of pattern 2."""
        result = normalize_numbered_village("南岭二")
        assert result == "南岭"

    def test_normalize_no_numeral(self):
        """Test normalization of name without numeral."""
        result = normalize_numbered_village("石岭村")
        assert result == "石岭村"

    def test_normalize_multiple_numerals(self):
        """Test normalization with multiple numerals."""
        result = normalize_numbered_village("北岗十一村")
        assert result == "北岗"

    def test_batch_normalization(self):
        """Test batch normalization."""
        names = ["东村一村", "东村二村", "南岭一", "南岭二", "石岭村"]
        normalized = [normalize_numbered_village(name) for name in names]

        assert normalized == ["东村", "东村", "南岭", "南岭", "石岭村"]

    def test_aggregation_effect(self):
        """Test that normalization enables aggregation."""
        names = ["东村一村", "东村二村", "东村三村"]
        normalized = [normalize_numbered_village(name) for name in names]

        # All should normalize to same base
        assert len(set(normalized)) == 1
        assert normalized[0] == "东村"


class TestEdgeCases:
    """Test edge cases."""

    def test_only_numeral(self):
        """Test name that is only a numeral."""
        has_numeral, base, suffix = detect_trailing_numeral("一")
        # Should not match (base would be empty)
        assert not has_numeral

    def test_numeral_village_only(self):
        """Test name that is numeral + 村."""
        has_numeral, base, suffix = detect_trailing_numeral("一村")
        # Should not match (base would be empty)
        assert not has_numeral

    def test_complex_name(self):
        """Test complex name with multiple components."""
        result = normalize_numbered_village("石岭村上村一村")
        # Should remove trailing "一村"
        assert result == "石岭村上村"

    def test_unicode_numerals(self):
        """Test that only Chinese numerals are detected."""
        # Arabic numerals should not be detected
        result = normalize_numbered_village("东村1村")
        assert result == "东村1村"  # No change


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
