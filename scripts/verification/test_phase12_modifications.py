#!/usr/bin/env python3
"""
Test script to verify Phase 12 modifications.

This script tests that the modified phase12_ngram_analysis.py correctly:
1. Only stores significant n-grams (p < 0.05) in ngram_significance
2. Cleans up non-significant data from ngram_tendency and regional_ngram_frequency
3. Maintains data consistency across tables
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_significance_filtering(db_path: str):
    """Test that only significant n-grams are stored."""
    print("=" * 70)
    print("Test 1: Verify only significant n-grams in ngram_significance")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check for non-significant n-grams
    cursor.execute("""
        SELECT COUNT(*)
        FROM ngram_significance
        WHERE p_value >= 0.05
    """)
    non_sig_count = cursor.fetchone()[0]

    if non_sig_count == 0:
        print("[PASS] No non-significant n-grams found in ngram_significance")
    else:
        print(f"[FAIL] Found {non_sig_count} non-significant n-grams (p >= 0.05)")
        return False

    # Check that all records have is_significant = 1
    cursor.execute("""
        SELECT COUNT(*)
        FROM ngram_significance
        WHERE is_significant != 1
    """)
    non_flagged = cursor.fetchone()[0]

    if non_flagged == 0:
        print("[PASS] All records have is_significant = 1")
    else:
        print(f"[FAIL] Found {non_flagged} records with is_significant != 1")
        return False

    conn.close()
    return True


def test_table_consistency(db_path: str):
    """Test that tables are consistent after cleanup."""
    print("\n" + "=" * 70)
    print("Test 2: Verify table consistency")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count unique n-grams in each table
    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_significance")
    sig_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_tendency")
    tend_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM regional_ngram_frequency")
    freq_count = cursor.fetchone()[0]

    print(f"Unique n-grams:")
    print(f"  ngram_significance: {sig_count:,}")
    print(f"  ngram_tendency: {tend_count:,}")
    print(f"  regional_ngram_frequency: {freq_count:,}")

    # Check that tendency and frequency tables only contain significant n-grams
    cursor.execute("""
        SELECT COUNT(*)
        FROM ngram_tendency
        WHERE NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = ngram_tendency.ngram
            AND ngram_significance.level = ngram_tendency.level
            AND ngram_significance.city = ngram_tendency.city
            AND ngram_significance.county = ngram_tendency.county
            AND ngram_significance.township = ngram_tendency.township
        )
    """)
    orphan_tendency = cursor.fetchone()[0]

    if orphan_tendency == 0:
        print("[PASS] All ngram_tendency records have corresponding significance records")
    else:
        print(f"[FAIL] Found {orphan_tendency} orphan records in ngram_tendency")
        return False

    cursor.execute("""
        SELECT COUNT(*)
        FROM regional_ngram_frequency
        WHERE NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = regional_ngram_frequency.ngram
            AND ngram_significance.level = regional_ngram_frequency.level
            AND ngram_significance.city = regional_ngram_frequency.city
            AND ngram_significance.county = regional_ngram_frequency.county
            AND ngram_significance.township = regional_ngram_frequency.township
        )
    """)
    orphan_frequency = cursor.fetchone()[0]

    if orphan_frequency == 0:
        print("[PASS] All regional_ngram_frequency records have corresponding significance records")
    else:
        print(f"[FAIL] Found {orphan_frequency} orphan records in regional_ngram_frequency")
        return False

    conn.close()
    return True


def test_retention_rates(db_path: str):
    """Test retention rates by level."""
    print("\n" + "=" * 70)
    print("Test 3: Check retention rates by level")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    levels = ['city', 'county', 'township']

    for level in levels:
        cursor.execute("""
            SELECT COUNT(*)
            FROM ngram_significance
            WHERE level = ?
        """, (level,))
        count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT MIN(p_value), MAX(p_value), AVG(p_value)
            FROM ngram_significance
            WHERE level = ?
        """, (level,))
        min_p, max_p, avg_p = cursor.fetchone()

        print(f"\n{level}:")
        print(f"  Count: {count:,}")
        print(f"  P-value range: [{min_p:.6f}, {max_p:.6f}]")
        print(f"  P-value avg: {avg_p:.6f}")

        if max_p >= 0.05:
            print(f"  [FAIL] Found p-value >= 0.05")
            return False
        else:
            print(f"  [PASS] All p-values < 0.05")

    conn.close()
    return True


def test_database_size(db_path: str):
    """Check database size."""
    print("\n" + "=" * 70)
    print("Test 4: Database size check")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]

    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]

    size_gb = (page_count * page_size) / (1024**3)

    print(f"Database size: {size_gb:.2f} GB")

    if size_gb < 3.5:
        print("[PASS] Database size is optimized (< 3.5 GB)")
    else:
        print(f"[WARNING] Database size is larger than expected")

    conn.close()
    return True


def main():
    """Run all tests."""
    db_path = 'data/villages.db'

    print("\n" + "=" * 70)
    print("Phase 12 Modification Test Suite")
    print("=" * 70)
    print(f"Database: {db_path}\n")

    tests = [
        ("Significance Filtering", test_significance_filtering),
        ("Table Consistency", test_table_consistency),
        ("Retention Rates", test_retention_rates),
        ("Database Size", test_database_size),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func(db_path)
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
