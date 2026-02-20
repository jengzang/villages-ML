#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verification script for the new 5-rule prefix cleaning system.

Run this script to verify that the implementation works correctly.
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, '.')

from src.preprocessing.prefix_cleaner import remove_administrative_prefix

def test_user_examples():
    """Test all 9 user-provided examples."""
    print("Testing user-provided examples...")
    print("=" * 80)

    tests = [
        # (natural, admin, expected_remaining, expected_prefix, rule_name)
        ("霞露村尾厝", "霞露村", "尾厝", "霞露村", "Rule 1"),
        ("陈家村石桥社区郑厝", "枫溪一村", "郑厝", "陈家村石桥社区", "Rule 1 (greedy)"),
        ("凤北超苟村", "凤北村", "超苟村", "凤北", "Rule 2"),
        ("湖厦村祠堂前片", "湖下村", "祠堂前片", "湖厦村", "Rule 2 (homophone)"),
        ("輋格厝村", "凤新村", "輋格厝村", "", "Rule 2 (no match)"),
        ("大松水路头", "松水村", "路头", "大松水", "Rule 3"),
        ("小松水路头", "小松村", "水路头", "小松", "Rule 3"),
        ("王家村东", "王家村", "王家村东", "", "Rule 4"),
        ("凤北村", "凤北村", "凤北村", "", "Rule 5"),
    ]

    passed = 0
    failed = 0

    for natural, admin, expected_remaining, expected_prefix, rule_name in tests:
        result = remove_administrative_prefix(natural, admin)

        if result.prefix_removed_name == expected_remaining and result.removed_prefix == expected_prefix:
            print(f"✓ {rule_name:20s} | {natural:25s} → {result.prefix_removed_name:15s} (removed: {result.removed_prefix})")
            passed += 1
        else:
            print(f"✗ {rule_name:20s} | {natural:25s}")
            print(f"  Expected: {expected_remaining} (prefix: {expected_prefix})")
            print(f"  Got:      {result.prefix_removed_name} (prefix: {result.removed_prefix})")
            failed += 1

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")

    return failed == 0


def test_additional_cases():
    """Test additional edge cases."""
    print("\nTesting additional cases...")
    print("=" * 80)

    tests = [
        # Test Rule 1 priority over Rule 2
        ("霞露村尾厝", "霞露村", "尾厝", "霞露村", "Rule 1 has priority"),

        # Test empty admin village - Rule 1 still applies but must satisfy Rule 4
        # 石岭村上村 has last delimiter at end, would leave only 村 (1 char), so no removal
        ("石岭村上村", "", "石岭村上村", "", "Empty admin (no removal - Rule 4)"),

        # Test multiple delimiters (greedy to LAST one)
        ("龙岗寨新村", "龙岗", "新村", "龙岗寨", "Multiple delimiters (greedy)"),

        # Test minimum length validation
        ("王家村东区", "王家村", "东区", "王家村", "Minimum length pass"),

        # Test direction modifiers
        ("东凤北村", "凤北村", "东凤北村", "", "Direction modifier (no match - 东凤北 != 凤北)"),

        # Test new/old modifiers
        ("新石岭村", "石岭村", "新石岭村", "", "New modifier (no match - 新石岭 != 石岭)"),
    ]

    passed = 0
    failed = 0

    for natural, admin, expected_remaining, expected_prefix, description in tests:
        result = remove_administrative_prefix(natural, admin)

        if result.prefix_removed_name == expected_remaining and result.removed_prefix == expected_prefix:
            print(f"✓ {description:35s} | {natural:20s} → {result.prefix_removed_name}")
            passed += 1
        else:
            print(f"✗ {description:35s} | {natural:20s}")
            print(f"  Expected: {expected_remaining} (prefix: {expected_prefix})")
            print(f"  Got:      {result.prefix_removed_name} (prefix: {result.removed_prefix})")
            failed += 1

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")

    return failed == 0


def main():
    """Run all verification tests."""
    print("\n" + "=" * 80)
    print("PREFIX CLEANING VERIFICATION SCRIPT")
    print("=" * 80 + "\n")

    all_passed = True

    # Test user examples
    if not test_user_examples():
        all_passed = False

    # Test additional cases
    if not test_additional_cases():
        all_passed = False

    # Final summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nThe 5-rule prefix cleaning system is working correctly.")
        print("\nNext steps:")
        print("1. Run pytest: python -m pytest tests/unit/test_prefix_cleaner.py -v")
        print("2. Regenerate preprocessed table: python scripts/create_preprocessed_table.py")
        print("3. Verify removal rate is ~6%")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease review the implementation and fix the failing tests.")
        sys.exit(1)

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
