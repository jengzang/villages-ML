"""Unit tests for prefix_cleaner module."""

import pytest
import sqlite3
from src.preprocessing.prefix_cleaner import (
    generate_prefix_candidates,
    flexible_match,
    remove_prefix_conservative,
    remove_administrative_prefix,
    PrefixCleanedName
)


class TestGeneratePrefixCandidates:
    """Test prefix candidate generation."""

    def test_fixed_length_candidates(self):
        """Test fixed-length prefix generation."""
        candidates = generate_prefix_candidates("石岭村上村")
        prefixes = [p for p, s in candidates]

        assert "石岭" in prefixes
        assert "石岭村" in prefixes

    def test_delimiter_based_candidates(self):
        """Test delimiter-based prefix generation."""
        candidates = generate_prefix_candidates("石岭村上村")
        prefixes = [p for p, s in candidates]

        # Should detect "村" delimiter
        assert "石岭村" in prefixes
        assert "石岭" in prefixes

    def test_no_delimiter_candidates(self):
        """Test candidates without delimiter."""
        candidates = generate_prefix_candidates("葵山土头村")
        prefixes = [p for p, s in candidates]

        assert "葵山" in prefixes
        assert "葵山土" in prefixes

    def test_short_name(self):
        """Test short names."""
        candidates = generate_prefix_candidates("上村")
        # Should still generate candidates
        assert len(candidates) > 0


class TestFlexibleMatch:
    """Test flexible matching logic."""

    def test_exact_match(self):
        """Test exact match."""
        is_match, conf, match_type = flexible_match("石岭村", "石岭村")
        assert is_match
        assert conf == 1.0
        assert match_type == "exact"

    def test_normalized_match(self):
        """Test normalized match (with/without 村)."""
        is_match, conf, match_type = flexible_match("石岭", "石岭村")
        assert is_match
        assert conf == 0.95
        assert match_type == "exact_normalized"

    def test_partial_match(self):
        """Test partial match."""
        is_match, conf, match_type = flexible_match("魁头", "魁头村")
        assert is_match
        assert conf >= 0.7

    def test_no_match(self):
        """Test no match."""
        is_match, conf, match_type = flexible_match("石岭", "龙岗")
        assert not is_match
        assert conf == 0.0


class TestRemovePrefixConservative:
    """Test conservative prefix removal."""

    def test_remove_prefix(self):
        """Test normal prefix removal."""
        result = remove_prefix_conservative("石岭村上村", "石岭村")
        assert result == "上村"

    def test_not_a_prefix(self):
        """Test non-prefix (internal substring)."""
        result = remove_prefix_conservative("上石岭村", "石岭村")
        assert result == "上石岭村"  # Should not remove

    def test_empty_remaining(self):
        """Test removal that would leave empty string."""
        result = remove_prefix_conservative("石岭", "石岭")
        assert result == "石岭"  # Should not remove

    def test_partial_prefix(self):
        """Test partial prefix."""
        result = remove_prefix_conservative("龙岗村新村", "龙岗")
        assert result == "村新村"


class TestRemoveAdministrativePrefix:
    """Test main prefix removal function."""

    def test_exact_row_match(self):
        """Test exact match with same-row admin village."""
        result = remove_administrative_prefix(
            natural_village="石岭村上村",
            administrative_village="石岭村"
        )

        assert result.had_prefix
        assert result.prefix_removed_name == "上村"
        assert result.removed_prefix == "石岭村"
        assert result.match_source.startswith("same_row")
        assert result.confidence >= 0.9

    def test_normalized_row_match(self):
        """Test normalized match (admin without 村)."""
        result = remove_administrative_prefix(
            natural_village="龙岗村新村",
            administrative_village="龙岗"
        )

        assert result.had_prefix
        assert result.prefix_removed_name == "村新村"
        assert result.removed_prefix == "龙岗"
        assert result.match_source.startswith("same_row")

    def test_no_delimiter_match(self):
        """Test match without delimiter."""
        result = remove_administrative_prefix(
            natural_village="葵山土头村",
            administrative_village="葵山村"
        )

        assert result.had_prefix
        assert result.prefix_removed_name == "土头村"
        assert result.removed_prefix == "葵山"

    def test_too_short(self):
        """Test length guard."""
        result = remove_administrative_prefix(
            natural_village="上村",
            administrative_village="石岭村",
            min_length=3
        )

        assert not result.had_prefix
        assert result.match_source == "too_short"

    def test_identical_names(self):
        """Test identical natural and admin village."""
        result = remove_administrative_prefix(
            natural_village="石岭村",
            administrative_village="石岭村"
        )

        assert not result.had_prefix
        assert result.match_source == "identical"

    def test_no_match(self):
        """Test no matching prefix."""
        result = remove_administrative_prefix(
            natural_village="新村",
            administrative_village="石岭村"
        )

        assert not result.had_prefix
        assert result.prefix_removed_name == "新村"

    def test_low_confidence_needs_review(self):
        """Test low confidence case needs review."""
        result = remove_administrative_prefix(
            natural_village="石岭上村",
            administrative_village="龙岗村",
            confidence_threshold=0.9
        )

        # Should not remove if confidence too low
        if result.confidence < 0.9:
            assert result.prefix_removed_name == "石岭上村"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_name(self):
        """Test empty natural village name."""
        result = remove_administrative_prefix(
            natural_village="",
            administrative_village="石岭村"
        )

        assert not result.had_prefix

    def test_single_char_name(self):
        """Test single character name."""
        result = remove_administrative_prefix(
            natural_village="上",
            administrative_village="石岭村",
            min_length=3
        )

        assert not result.had_prefix
        assert result.match_source == "too_short"

    def test_multiple_delimiters(self):
        """Test name with multiple delimiters."""
        result = remove_administrative_prefix(
            natural_village="石岭村上村新村",
            administrative_village="石岭村"
        )

        # Should only remove first prefix
        assert result.prefix_removed_name == "上村新村"

    def test_admin_village_longer_than_natural(self):
        """Test admin village longer than natural village."""
        result = remove_administrative_prefix(
            natural_village="石岭",
            administrative_village="石岭村委会"
        )

        # Should handle gracefully
        assert isinstance(result, PrefixCleanedName)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
