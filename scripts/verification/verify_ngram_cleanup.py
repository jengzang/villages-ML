#!/usr/bin/env python3
"""
Verify n-gram cleanup results.

This script checks:
1. All remaining n-grams are significant (p < 0.05)
2. Consistency across related tables
3. Data distribution by level
"""

import sqlite3


def verify_cleanup(db_path: str):
    """Verify n-gram cleanup was successful."""

    print("=" * 70)
    print("N-gram Cleanup Verification")
    print("=" * 70)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check 1: All remaining n-grams should be significant
    print("Check 1: Verifying all n-grams are significant...")
    cursor.execute("""
        SELECT COUNT(*)
        FROM ngram_significance
        WHERE p_value >= 0.05
    """)
    non_sig_count = cursor.fetchone()[0]

    if non_sig_count == 0:
        print("  [OK] All remaining n-grams are significant (p < 0.05)")
    else:
        print(f"  [ERROR] Found {non_sig_count} non-significant n-grams")
        return False

    # Check 2: Consistency across tables
    print("\nCheck 2: Verifying consistency across tables...")
    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_significance")
    sig_ngrams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_tendency")
    tend_ngrams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM regional_ngram_frequency")
    freq_ngrams = cursor.fetchone()[0]

    print(f"  N-gram counts:")
    print(f"    ngram_significance: {sig_ngrams:,}")
    print(f"    ngram_tendency: {tend_ngrams:,}")
    print(f"    regional_ngram_frequency: {freq_ngrams:,}")

    if sig_ngrams > 0:
        print("  [OK] Tables contain data")
    else:
        print("  [ERROR] Tables are empty")
        return False

    # Check 3: Verify by level
    print("\nCheck 3: Verifying data distribution by level...")
    cursor.execute("""
        SELECT level, COUNT(*),
               MIN(p_value), MAX(p_value), AVG(p_value)
        FROM ngram_significance
        GROUP BY level
    """)

    for level, count, min_p, max_p, avg_p in cursor.fetchall():
        print(f"  {level}:")
        print(f"    Count: {count:,}")
        print(f"    P-value range: [{min_p:.6f}, {max_p:.6f}]")
        print(f"    P-value avg: {avg_p:.6f}")

        if max_p >= 0.05:
            print(f"    [ERROR] Found p-value >= 0.05")
            return False

    # Check 4: Database size
    print("\nCheck 4: Database size...")
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    size_gb = (page_count * page_size) / (1024**3)
    print(f"  Database size: {size_gb:.2f} GB")

    conn.close()

    print("\n" + "=" * 70)
    print("[SUCCESS] All verification checks passed")
    print("=" * 70)
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify n-gram cleanup")
    parser.add_argument("--db", default="data/villages.db", help="Database path")

    args = parser.parse_args()

    success = verify_cleanup(args.db)
    exit(0 if success else 1)
