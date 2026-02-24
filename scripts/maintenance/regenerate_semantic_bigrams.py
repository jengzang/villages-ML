#!/usr/bin/env python3
"""
Regenerate semantic_bigrams with expanded lexicon (70+ categories)

This script regenerates semantic bigrams and trigrams using the expanded
semantic lexicon (v3) with 70+ fine-grained categories.
"""

import sqlite3
import sys
from pathlib import Path
from collections import Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.semantic_composition import SemanticCompositionAnalyzer


def main():
    """Main execution function."""
    db_path = 'data/villages.db'
    lexicon_path = 'data/semantic_lexicon_v3_expanded.json'

    print("\n" + "="*60)
    print("Regenerating Semantic Bigrams with Expanded Lexicon")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Lexicon: {lexicon_path}")
    print()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Extract semantic compositions with new lexicon
    print("Step 1: Extracting semantic compositions...")
    print("-" * 60)

    with SemanticCompositionAnalyzer(db_path, lexicon_path=lexicon_path) as analyzer:
        compositions = analyzer.analyze_all_compositions()

        bigrams = compositions['bigrams']
        trigrams = compositions['trigrams']

        print(f"Extracted {len(bigrams):,} unique semantic bigrams")
        print(f"Extracted {len(trigrams):,} unique semantic trigrams")

    # Step 2: Clear old data
    print("\nStep 2: Clearing old semantic bigrams/trigrams...")
    print("-" * 60)

    cursor.execute("DELETE FROM semantic_bigrams")
    cursor.execute("DELETE FROM semantic_trigrams")
    conn.commit()
    print("[OK] Old data cleared")

    # Step 3: Store new bigrams
    print("\nStep 3: Storing new semantic bigrams...")
    print("-" * 60)

    total_bigrams = sum(bigrams.values())

    for (cat1, cat2), freq in bigrams.items():
        percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
        cursor.execute("""
            INSERT OR REPLACE INTO semantic_bigrams
            (category1, category2, frequency, percentage)
            VALUES (?, ?, ?, ?)
        """, (cat1, cat2, freq, percentage))

    conn.commit()
    print(f"[OK] Stored {len(bigrams):,} semantic bigrams")

    # Step 4: Store new trigrams
    print("\nStep 4: Storing new semantic trigrams...")
    print("-" * 60)

    total_trigrams = sum(trigrams.values())

    for (cat1, cat2, cat3), freq in trigrams.items():
        percentage = (freq / total_trigrams * 100) if total_trigrams > 0 else 0
        cursor.execute("""
            INSERT OR REPLACE INTO semantic_trigrams
            (category1, category2, category3, frequency, percentage)
            VALUES (?, ?, ?, ?, ?)
        """, (cat1, cat2, cat3, freq, percentage))

    conn.commit()
    print(f"[OK] Stored {len(trigrams):,} semantic trigrams")

    # Step 5: Statistics
    print("\n" + "="*60)
    print("Statistics")
    print("="*60)

    cursor.execute("SELECT COUNT(DISTINCT category1) FROM semantic_bigrams")
    cat1_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT category2) FROM semantic_bigrams")
    cat2_count = cursor.fetchone()[0]

    print(f"Unique category1: {cat1_count}")
    print(f"Unique category2: {cat2_count}")
    print(f"Total bigrams: {len(bigrams):,}")
    print(f"Total trigrams: {len(trigrams):,}")

    # Top 10 bigrams
    print("\nTop 10 most frequent bigrams:")
    cursor.execute("""
        SELECT category1, category2, frequency
        FROM semantic_bigrams
        ORDER BY frequency DESC
        LIMIT 10
    """)
    for i, (cat1, cat2, freq) in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {cat1} + {cat2}: {freq:,}")

    conn.close()

    print("\n" + "="*60)
    print("Regeneration Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
