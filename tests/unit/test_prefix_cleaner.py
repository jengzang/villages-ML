"""Unit tests for prefix_cleaner module (5-rule system)."""

import pytest
from src.preprocessing.prefix_cleaner import (
    count_chinese_chars,
    remove_delimiters,
    try_rule1_delimiter_removal,
    try_rule2_admin_comparison,
    try_homophone_match,
    remove_administrative_prefix,
    PrefixCleanedName
)


class TestHelperFunctions:
    """Test helper functions."""

    def test_count_chinese_chars(self):
        """Test Chinese character counting."""
        assert count_chinese_chars("霞露村尾厝") == 5
        assert count_chinese_chars("村123号") == 2  # 村 and 号
        assert count_chinese_chars("ABC村") == 1
        assert count_chinese_chars("123") == 0
        assert count_chinese_chars("") == 0

    def test_remove_delimiters(self):
        """Test delimiter removal."""
        assert remove_delimiters("凤北村") == "凤北"
        assert remove_delimiters("石桥社区") == "石桥"
        assert remove_delimiters("龙岗寨") == "龙岗"
        assert remove_delimiters("新村片") == "新"  # Removes both 村 and 片
        assert remove_delimiters("凤北") == "凤北"


class TestRule1DelimiterRemoval:
    """Test Rule 1: Greedy delimiter-based removal."""

    def test_single_delimiter(self):
        """Test single delimiter removal."""
        prefix = try_rule1_delimiter_removal("霞露村尾厝")
        assert prefix == "霞露村"

    def test_multiple_delimiters_greedy(self):
        """Test greedy removal to LAST delimiter."""
        prefix = try_rule1_delimiter_removal("陈家村石桥社区郑厝")
        assert prefix == "陈家村石桥社区"  # Greedy to last delimiter!

    def test_no_delimiter(self):
        """Test no delimiter found."""
        prefix = try_rule1_delimiter_removal("凤北超苟")
        assert prefix == ""

    def test_delimiter_at_start(self):
        """Test delimiter at start (should not remove)."""
        prefix = try_rule1_delimiter_removal("村尾厝")
        assert prefix == ""  # Delimiter at position 0, don't remove

    def test_different_delimiters(self):
        """Test different delimiter types (greedy to LAST delimiter)."""
        assert try_rule1_delimiter_removal("龙岗寨新村") == "龙岗寨新村"  # Last delimiter is 村
        assert try_rule1_delimiter_removal("石桥片东区") == "石桥片"  # Last delimiter is 片
        assert try_rule1_delimiter_removal("凤北社区大院") == "凤北社区"  # Last delimiter is 社区


class TestRule2AdminComparison:
    """Test Rule 2: Admin village comparison."""

    def test_direct_match(self):
        """Test direct match with normalized admin."""
        prefix, _ = try_rule2_admin_comparison("凤北超苟村", "凤北村")
        assert prefix == "凤北"

    def test_match_with_delimiter(self):
        """Test match including delimiter."""
        prefix, _ = try_rule2_admin_comparison("凤北村超苟", "凤北村")
        assert prefix == "凤北村"

    def test_no_match(self):
        """Test no match."""
        prefix, _ = try_rule2_admin_comparison("輋格厝村", "凤新村")
        assert prefix == ""

    def test_admin_without_delimiter(self):
        """Test admin village without delimiter."""
        prefix, _ = try_rule2_admin_comparison("龙岗村新村", "龙岗")
        assert prefix == "龙岗村"  # Should extend with delimiter


class TestRule3ModifierHandling:
    """Test Rule 3: Size/direction modifier handling."""

    def test_size_modifier(self):
        """Test size modifiers (大/小)."""
        prefix, _ = try_rule2_admin_comparison("大松水路头", "松水村")
        assert prefix == "大松水"

        prefix, _ = try_rule2_admin_comparison("小松水路头", "小松村")
        assert prefix == "小松"

    def test_direction_modifier(self):
        """Test direction modifiers (东/西/南/北).

        Note: Some combinations are ambiguous. We match when the pattern is clear.
        """
        # 东凤北 is ambiguous - could be a single name, so no match
        prefix, _ = try_rule2_admin_comparison("东凤北村", "凤北村")
        assert prefix == ""  # No match - 东凤北 is a different name

        # 南龙岗 with 新村 suffix - pattern is clearer, so we match
        prefix, _ = try_rule2_admin_comparison("南龙岗新村", "龙岗村")
        assert prefix == "南龙岗"  # Match - 南 + 龙岗

    def test_new_old_modifier(self):
        """Test new/old modifiers (新/老).

        Note: 新石岭 is ambiguous - could be a single name or 新+石岭.
        We conservatively treat it as a single name (no match).
        """
        prefix, _ = try_rule2_admin_comparison("新石岭村", "石岭村")
        assert prefix == ""  # No match - 新石岭 is a different name

        prefix, _ = try_rule2_admin_comparison("老王家村", "王家村")
        assert prefix == ""  # No match - 老王家 is a different name


class TestHomophoneMatching:
    """Test homophone matching."""

    def test_homophone_match(self):
        """Test homophone matching (湖下/湖厦)."""
        prefix = try_homophone_match("湖厦村祠堂前片", "湖下")
        assert prefix == "湖厦村"

    def test_no_homophone_match(self):
        """Test no homophone match."""
        prefix = try_homophone_match("凤北村", "龙岗")
        assert prefix == ""


class TestRule4MinimumLength:
    """Test Rule 4: Minimum 2 Chinese characters."""

    def test_minimum_length_validation(self):
        """Test that removal is aborted if remaining < 2 Chinese chars."""
        result = remove_administrative_prefix(
            natural_village="王家村东",
            administrative_village="王家村"
        )
        # Would leave only "东" (1 char), so should NOT remove
        assert not result.had_prefix
        assert result.prefix_removed_name == "王家村东"

    def test_minimum_length_pass(self):
        """Test that removal proceeds if remaining >= 2 Chinese chars."""
        result = remove_administrative_prefix(
            natural_village="王家村东区",
            administrative_village="王家村"
        )
        # Would leave "东区" (2 chars), so should remove
        assert result.had_prefix
        assert result.prefix_removed_name == "东区"


class TestRule5IdenticalNames:
    """Test Rule 5: Identical names."""

    def test_identical_names(self):
        """Test identical natural and admin village."""
        result = remove_administrative_prefix(
            natural_village="凤北村",
            administrative_village="凤北村"
        )
        assert not result.had_prefix
        assert result.prefix_removed_name == "凤北村"
        assert result.match_source == "rule5_identical"


class TestRemoveAdministrativePrefix:
    """Test main prefix removal function with all rules."""

    def test_rule1_example1(self):
        """Rule 1: 霞露村尾厝 → 尾厝."""
        result = remove_administrative_prefix(
            natural_village="霞露村尾厝",
            administrative_village="霞露村"
        )
        assert result.had_prefix
        assert result.prefix_removed_name == "尾厝"
        assert result.removed_prefix == "霞露村"
        assert result.match_source == "rule1_delimiter"

    def test_rule1_example2(self):
        """Rule 1: 陈家村石桥社区郑厝 → 郑厝 (greedy!)."""
        result = remove_administrative_prefix(
            natural_village="陈家村石桥社区郑厝",
            administrative_village="枫溪一村"
        )
        assert result.had_prefix
        assert result.prefix_removed_name == "郑厝"
        assert result.removed_prefix == "陈家村石桥社区"
        assert result.match_source == "rule1_delimiter"

    def test_rule2_example1(self):
        """Rule 2: 凤北超苟村 → 超苟村."""
        result = remove_administrative_prefix(
            natural_village="凤北超苟村",
            administrative_village="凤北村"
        )
        assert result.had_prefix
        assert result.prefix_removed_name == "超苟村"
        assert result.removed_prefix == "凤北"
        assert result.match_source == "rule2_admin_match"

    def test_rule2_example2_no_match(self):
        """Rule 2: 輋格厝村 with admin 凤新村 → no match."""
        result = remove_administrative_prefix(
            natural_village="輋格厝村",
            administrative_village="凤新村"
        )
        assert not result.had_prefix
        assert result.prefix_removed_name == "輋格厝村"

    def test_rule3_example1(self):
        """Rule 3: 大松水路头 → 路头."""
        result = remove_administrative_prefix(
            natural_village="大松水路头",
            administrative_village="松水村"
        )
        assert result.had_prefix
        assert result.prefix_removed_name == "路头"
        assert result.removed_prefix == "大松水"
        assert result.match_source == "rule3_modifier"

    def test_rule3_example2(self):
        """Rule 3: 小松水路头 → 水路头."""
        result = remove_administrative_prefix(
            natural_village="小松水路头",
            administrative_village="小松村"
        )
        assert result.had_prefix
        assert result.prefix_removed_name == "水路头"
        assert result.removed_prefix == "小松"
        assert result.match_source == "rule3_modifier"

    def test_rule4_example(self):
        """Rule 4: 王家村东 → 王家村东 (would leave only 1 char)."""
        result = remove_administrative_prefix(
            natural_village="王家村东",
            administrative_village="王家村"
        )
        assert not result.had_prefix
        assert result.prefix_removed_name == "王家村东"

    def test_rule5_example(self):
        """Rule 5: 凤北村 = 凤北村 → no removal."""
        result = remove_administrative_prefix(
            natural_village="凤北村",
            administrative_village="凤北村"
        )
        assert not result.had_prefix
        assert result.prefix_removed_name == "凤北村"
        assert result.match_source == "rule5_identical"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_natural_village(self):
        """Test empty natural village name."""
        result = remove_administrative_prefix(
            natural_village="",
            administrative_village="石岭村"
        )
        assert not result.had_prefix
        assert result.match_source == "empty_name"

    def test_empty_admin_village(self):
        """Test empty admin village name."""
        result = remove_administrative_prefix(
            natural_village="石岭村上村",
            administrative_village=""
        )
        # Rule 1 tries to remove to last delimiter (村 at end), but would leave nothing
        # So no removal happens
        assert not result.had_prefix
        assert result.prefix_removed_name == "石岭村上村"

    def test_none_admin_village(self):
        """Test None admin village name."""
        result = remove_administrative_prefix(
            natural_village="石岭村上村",
            administrative_village=None
        )
        # Rule 1 tries to remove to last delimiter (村 at end), but would leave nothing
        # So no removal happens
        assert not result.had_prefix
        assert result.prefix_removed_name == "石岭村上村"

    def test_rule1_priority_over_rule2(self):
        """Test that Rule 1 has absolute priority over Rule 2."""
        # Even if admin village matches, Rule 1 should apply first
        result = remove_administrative_prefix(
            natural_village="霞露村尾厝",
            administrative_village="霞露村"
        )
        # Rule 1 should apply (delimiter-based), not Rule 2
        assert result.match_source == "rule1_delimiter"
        assert result.removed_prefix == "霞露村"


class TestUserProvidedExamples:
    """Test all 9 user-provided examples."""

    def test_example1_rule1(self):
        """霞露村尾厝 → 尾厝."""
        result = remove_administrative_prefix("霞露村尾厝", "霞露村")
        assert result.prefix_removed_name == "尾厝"
        assert result.removed_prefix == "霞露村"

    def test_example2_rule1(self):
        """陈家村石桥社区郑厝 → 郑厝."""
        result = remove_administrative_prefix("陈家村石桥社区郑厝", "枫溪一村")
        assert result.prefix_removed_name == "郑厝"
        assert result.removed_prefix == "陈家村石桥社区"

    def test_example3_rule2(self):
        """凤北超苟村 → 超苟村."""
        result = remove_administrative_prefix("凤北超苟村", "凤北村")
        assert result.prefix_removed_name == "超苟村"
        assert result.removed_prefix == "凤北"

    def test_example4_rule2_homophone(self):
        """湖厦村祠堂前片 → 祠堂前片 (homophone)."""
        result = remove_administrative_prefix("湖厦村祠堂前片", "湖下村")
        assert result.prefix_removed_name == "祠堂前片"
        assert result.removed_prefix == "湖厦村"

    def test_example5_rule2_no_match(self):
        """輋格厝村 → 輋格厝村 (no match)."""
        result = remove_administrative_prefix("輋格厝村", "凤新村")
        assert result.prefix_removed_name == "輋格厝村"
        assert result.removed_prefix == ""

    def test_example6_rule3(self):
        """大松水路头 → 路头."""
        result = remove_administrative_prefix("大松水路头", "松水村")
        assert result.prefix_removed_name == "路头"
        assert result.removed_prefix == "大松水"

    def test_example7_rule3(self):
        """小松水路头 → 水路头."""
        result = remove_administrative_prefix("小松水路头", "小松村")
        assert result.prefix_removed_name == "水路头"
        assert result.removed_prefix == "小松"

    def test_example8_rule4(self):
        """王家村东 → 王家村东 (would leave only 1 char)."""
        result = remove_administrative_prefix("王家村东", "王家村")
        assert result.prefix_removed_name == "王家村东"
        assert result.removed_prefix == ""

    def test_example9_rule5(self):
        """凤北村 → 凤北村 (identical)."""
        result = remove_administrative_prefix("凤北村", "凤北村")
        assert result.prefix_removed_name == "凤北村"
        assert result.removed_prefix == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
