"""Simple validation script for preprocessing modules."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.prefix_cleaner import (
    generate_prefix_candidates,
    flexible_match,
    remove_prefix_conservative,
    remove_administrative_prefix
)
from preprocessing.numbered_village_normalizer import (
    detect_trailing_numeral,
    normalize_numbered_village
)


def test_prefix_cleaner():
    """Test prefix cleaner functionality."""
    print("Testing prefix_cleaner module...")

    # Test 1: Generate prefix candidates
    print("\n1. Testing generate_prefix_candidates:")
    candidates = generate_prefix_candidates("石岭村上村")
    print(f"   Input: 石岭村上村")
    print(f"   Candidates: {candidates}")
    assert len(candidates) > 0, "Should generate candidates"

    # Test 2: Flexible match
    print("\n2. Testing flexible_match:")
    is_match, conf, match_type = flexible_match("石岭", "石岭村")
    print(f"   Match '石岭' with '石岭村': {is_match}, confidence={conf:.2f}, type={match_type}")
    assert is_match, "Should match"
    assert conf >= 0.9, "Should have high confidence"

    # Test 3: Conservative removal
    print("\n3. Testing remove_prefix_conservative:")
    result = remove_prefix_conservative("石岭村上村", "石岭村")
    print(f"   Remove '石岭村' from '石岭村上村': {result}")
    assert result == "上村", f"Expected '上村', got '{result}'"

    # Test 4: Full prefix removal
    print("\n4. Testing remove_administrative_prefix:")
    result = remove_administrative_prefix(
        natural_village="石岭村上村",
        administrative_village="石岭村"
    )
    print(f"   Natural: 石岭村上村")
    print(f"   Admin: 石岭村")
    print(f"   Result: {result.prefix_removed_name}")
    print(f"   Had prefix: {result.had_prefix}")
    print(f"   Removed: {result.removed_prefix}")
    print(f"   Confidence: {result.confidence:.2f}")
    assert result.had_prefix, "Should detect prefix"
    assert result.prefix_removed_name == "上村", f"Expected '上村', got '{result.prefix_removed_name}'"

    # Test 5: No delimiter case
    print("\n5. Testing no delimiter case:")
    result = remove_administrative_prefix(
        natural_village="葵山土头村",
        administrative_village="葵山村"
    )
    print(f"   Natural: 葵山土头村")
    print(f"   Admin: 葵山村")
    print(f"   Result: {result.prefix_removed_name}")
    print(f"   Confidence: {result.confidence:.2f}")
    assert result.had_prefix, "Should detect prefix"
    assert result.prefix_removed_name == "土头村", f"Expected '土头村', got '{result.prefix_removed_name}'"

    # Test 6: Length guard
    print("\n6. Testing length guard:")
    result = remove_administrative_prefix(
        natural_village="上村",
        administrative_village="石岭村",
        min_length=3
    )
    print(f"   Natural: 上村 (too short)")
    print(f"   Result: {result.match_source}")
    assert result.match_source == "too_short", "Should skip short names"

    print("\n[PASS] All prefix_cleaner tests passed!")


def test_numbered_village_normalizer():
    """Test numbered village normalizer functionality."""
    print("\n\nTesting numbered_village_normalizer module...")

    # Test 1: Pattern 1 (村名 + 数字 + 村)
    print("\n1. Testing pattern: 村名 + 数字 + 村")
    has_numeral, base, suffix = detect_trailing_numeral("东村一村")
    print(f"   Input: 东村一村")
    print(f"   Has numeral: {has_numeral}, Base: {base}, Suffix: {suffix}")
    assert has_numeral, "Should detect numeral"
    assert base == "东村", f"Expected '东村', got '{base}'"

    # Test 2: Pattern 2 (村名 + 数字)
    print("\n2. Testing pattern: 村名 + 数字")
    has_numeral, base, suffix = detect_trailing_numeral("南岭二")
    print(f"   Input: 南岭二")
    print(f"   Has numeral: {has_numeral}, Base: {base}, Suffix: {suffix}")
    assert has_numeral, "Should detect numeral"
    assert base == "南岭", f"Expected '南岭', got '{base}'"

    # Test 3: No numeral
    print("\n3. Testing no numeral:")
    has_numeral, base, suffix = detect_trailing_numeral("石岭村")
    print(f"   Input: 石岭村")
    print(f"   Has numeral: {has_numeral}")
    assert not has_numeral, "Should not detect numeral"

    # Test 4: Normalization
    print("\n4. Testing normalization:")
    result = normalize_numbered_village("东村一村")
    print(f"   Input: 东村一村")
    print(f"   Normalized: {result}")
    assert result == "东村", f"Expected '东村', got '{result}'"

    # Test 5: Batch normalization
    print("\n5. Testing batch normalization:")
    names = ["东村一村", "东村二村", "南岭一", "南岭二", "石岭村"]
    normalized = [normalize_numbered_village(name) for name in names]
    print(f"   Input: {names}")
    print(f"   Normalized: {normalized}")
    assert normalized == ["东村", "东村", "南岭", "南岭", "石岭村"], "Batch normalization failed"

    print("\n[PASS] All numbered_village_normalizer tests passed!")


def test_integration():
    """Test integration of both modules."""
    print("\n\nTesting integration...")

    # Test: Prefix removal + numbered normalization
    print("\n1. Testing combined preprocessing:")

    # Step 1: Remove prefix
    result = remove_administrative_prefix(
        natural_village="石岭村上一村",
        administrative_village="石岭村"
    )
    print(f"   Original: 石岭村上一村")
    print(f"   After prefix removal: {result.prefix_removed_name}")

    # Step 2: Normalize numbered village
    normalized = normalize_numbered_village(result.prefix_removed_name)
    print(f"   After normalization: {normalized}")

    assert result.prefix_removed_name == "上一村", "Prefix removal failed"
    assert normalized == "上", "Normalization failed"

    print("\n[PASS] Integration test passed!")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Preprocessing Module Validation")
    print("=" * 60)

    try:
        test_prefix_cleaner()
        test_numbered_village_normalizer()
        test_integration()

        print("\n" + "=" * 60)
        print("[PASS] ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
