#!/usr/bin/env python3
"""
Fix semantic_bigrams PMI values

Problem: semantic_bigrams table has NULL PMI values because the table uses
subcategories (75 categories) but PMI calculation uses main categories (9 categories).

Solution: Recalculate PMI using the actual categories in the table.
"""

import sqlite3
import sys
from pathlib import Path
import math
from collections import Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def calculate_pmi_for_bigrams(db_path: str):
    """Calculate PMI scores for semantic bigrams."""
    print("=" * 60)
    print("Fixing semantic_bigrams PMI values")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all bigrams
    cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
    bigrams = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}

    print(f"\nLoaded {len(bigrams):,} bigrams")

    # Calculate marginal frequencies
    cat1_freq = Counter()
    cat2_freq = Counter()
    total_freq = 0

    for (cat1, cat2), freq in bigrams.items():
        cat1_freq[cat1] += freq
        cat2_freq[cat2] += freq
        total_freq += freq

    print(f"Total frequency: {total_freq:,}")
    print(f"Unique category1: {len(cat1_freq)}")
    print(f"Unique category2: {len(cat2_freq)}")

    # Calculate PMI for each bigram
    pmi_scores = {}
    for (cat1, cat2), freq in bigrams.items():
        # P(cat1, cat2)
        p_joint = freq / total_freq

        # P(cat1) * P(cat2)
        p_cat1 = cat1_freq[cat1] / total_freq
        p_cat2 = cat2_freq[cat2] / total_freq
        p_independent = p_cat1 * p_cat2

        # PMI = log(P(cat1, cat2) / (P(cat1) * P(cat2)))
        if p_independent > 0:
            pmi = math.log(p_joint / p_independent)
        else:
            pmi = 0.0

        pmi_scores[(cat1, cat2)] = pmi

    # Update bigrams table with PMI
    print("\nUpdating semantic_bigrams table...")
    update_count = 0
    for (cat1, cat2), pmi in pmi_scores.items():
        cursor.execute("""
            UPDATE semantic_bigrams
            SET pmi = ?
            WHERE category1 = ? AND category2 = ?
        """, (pmi, cat1, cat2))
        update_count += 1

    conn.commit()
    print(f"[OK] Updated PMI for {update_count:,} bigrams")

    # Verify
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN pmi IS NULL THEN 1 ELSE 0 END) as null_count FROM semantic_bigrams")
    total, null_count = cursor.fetchone()
    print(f"\nVerification: {total - null_count}/{total} bigrams now have PMI values")

    if null_count > 0:
        print(f"[WARNING] {null_count} bigrams still have NULL PMI")
    else:
        print("[OK] All bigrams now have PMI values!")

    # Show sample PMI values
    cursor.execute("""
        SELECT category1, category2, frequency, ROUND(pmi, 4) as pmi
        FROM semantic_bigrams
        ORDER BY pmi DESC
        LIMIT 5
    """)
    print("\nTop 5 bigrams by PMI:")
    for row in cursor.fetchall():
        print(f"  {row[0]} + {row[1]}: freq={row[2]}, pmi={row[3]}")

    conn.close()


def main():
    db_path = project_root / 'data' / 'villages.db'

    print(f"Database: {db_path}\n")

    try:
        calculate_pmi_for_bigrams(str(db_path))

        print("\n" + "=" * 60)
        print("Fix Complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
