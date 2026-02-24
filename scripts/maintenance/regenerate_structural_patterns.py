#!/usr/bin/env python3
"""
Regenerate structural patterns for trigrams and 4-grams.

This script re-runs pattern detection with the updated detect_templates method
that now supports trigram and 4-gram pattern detection.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from collections import Counter
from src.ngram_analysis import StructuralPatternDetector


def regenerate_patterns(db_path: str):
    """Regenerate structural patterns for all n-gram sizes."""
    print("=" * 60)
    print("Regenerating Structural Patterns")
    print("=" * 60)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    detector = StructuralPatternDetector(db_path)

    # Step 1: Clear existing patterns
    print("Step 1: Clearing existing patterns...")
    cursor.execute("DELETE FROM structural_patterns")
    conn.commit()
    print("[OK] Cleared\n")

    # Step 2: Get bigrams
    print("Step 2: Detecting bigram patterns...")
    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 2 AND position = 'all'
        ORDER BY frequency DESC
    """)
    bigrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})
    print(f"  Loaded {len(bigrams):,} bigrams")

    bigram_templates = detector.detect_templates(bigrams, min_freq=100)
    print(f"  Detected {len(bigram_templates)} templates")

    for template in bigram_templates:
        cursor.execute("""
            INSERT OR REPLACE INTO structural_patterns
            (pattern, pattern_type, n, position, frequency, example, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template['pattern'],
            template['type'],
            2,
            'all',
            template['frequency'],
            template['example'],
            f"{template['type']} pattern"
        ))

    conn.commit()
    print(f"[OK] Stored {len(bigram_templates)} bigram patterns\n")

    # Step 3: Get trigrams
    print("Step 3: Detecting trigram patterns...")
    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 3 AND position = 'all'
        ORDER BY frequency DESC
    """)
    trigrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})
    print(f"  Loaded {len(trigrams):,} trigrams")

    trigram_templates = detector.detect_templates(trigrams, min_freq=50)
    print(f"  Detected {len(trigram_templates)} templates")

    for template in trigram_templates:
        cursor.execute("""
            INSERT OR REPLACE INTO structural_patterns
            (pattern, pattern_type, n, position, frequency, example, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template['pattern'],
            template['type'],
            3,
            'all',
            template['frequency'],
            template['example'],
            f"{template['type']} pattern"
        ))

    conn.commit()
    print(f"[OK] Stored {len(trigram_templates)} trigram patterns\n")

    # Step 4: Get 4-grams
    print("Step 4: Detecting 4-gram patterns...")
    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 4 AND position = 'all'
        ORDER BY frequency DESC
    """)
    fourgrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})
    print(f"  Loaded {len(fourgrams):,} 4-grams")

    fourgram_templates = detector.detect_templates(fourgrams, min_freq=30)
    print(f"  Detected {len(fourgram_templates)} templates")

    for template in fourgram_templates:
        cursor.execute("""
            INSERT OR REPLACE INTO structural_patterns
            (pattern, pattern_type, n, position, frequency, example, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template['pattern'],
            template['type'],
            4,
            'all',
            template['frequency'],
            template['example'],
            f"{template['type']} pattern"
        ))

    conn.commit()
    print(f"[OK] Stored {len(fourgram_templates)} 4-gram patterns\n")

    # Step 5: Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    cursor.execute("SELECT n, COUNT(*) FROM structural_patterns GROUP BY n ORDER BY n")
    for n, count in cursor.fetchall():
        print(f"  n={n}: {count:,} patterns")

    print()
    print("Top 10 patterns by frequency:")
    cursor.execute("""
        SELECT pattern, pattern_type, n, frequency, example
        FROM structural_patterns
        ORDER BY frequency DESC
        LIMIT 10
    """)
    for pattern, ptype, n, freq, example in cursor.fetchall():
        print(f"  {pattern:15s} ({ptype:15s}, n={n}) freq={freq:6d} example={example}")

    conn.close()
    print("\n[OK] Pattern regeneration complete!")


if __name__ == "__main__":
    db_path = "data/villages.db"
    regenerate_patterns(db_path)
