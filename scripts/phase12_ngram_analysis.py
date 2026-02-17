#!/usr/bin/env python3
"""
Phase 12: N-gram Structure Analysis

This script performs comprehensive n-gram analysis on village names:
1. Extract bigrams and trigrams (全局和區域)
2. Calculate frequency statistics
3. Compute tendency scores (lift, z-score)
4. Statistical significance testing
5. Detect structural patterns

Approach: Offline-heavy, maximum accuracy, full dataset
"""

import sqlite3
import sys
from pathlib import Path
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ngram_analysis import NgramExtractor, NgramAnalyzer, StructuralPatternDetector
from ngram_schema import create_ngram_tables


def step1_create_tables(db_path: str):
    """Step 1: Create database tables."""
    print("\n" + "="*60)
    print("Step 1: Creating N-gram Analysis Tables")
    print("="*60)

    create_ngram_tables(db_path)
    print("[OK] Tables created successfully")


def step2_extract_global_ngrams(db_path: str):
    """Step 2: Extract global n-gram frequencies."""
    print("\n" + "="*60)
    print("Step 2: Extracting Global N-grams")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with NgramExtractor(db_path) as extractor:
        # Extract bigrams
        print("\nExtracting bigrams...")
        bigram_data = extractor.extract_all_ngrams(n=2)

        # Extract trigrams
        print("Extracting trigrams...")
        trigram_data = extractor.extract_all_ngrams(n=3)

    # Store bigrams
    print("\nStoring bigram frequencies...")
    for position, counter in bigram_data.items():
        total = sum(counter.values())
        for ngram, freq in counter.items():
            percentage = (freq / total * 100) if total > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_frequency
                (ngram, n, position, frequency, total_count, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ngram, 2, position, freq, total, percentage))

    # Store trigrams
    print("Storing trigram frequencies...")
    for position, counter in trigram_data.items():
        total = sum(counter.values())
        for ngram, freq in counter.items():
            percentage = (freq / total * 100) if total > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_frequency
                (ngram, n, position, frequency, total_count, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ngram, 3, position, freq, total, percentage))

    conn.commit()

    # Print statistics
    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_frequency WHERE n = 2")
    bigram_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_frequency WHERE n = 3")
    trigram_count = cursor.fetchone()[0]

    print(f"\n[OK] Extracted {bigram_count:,} unique bigrams")
    print(f"[OK] Extracted {trigram_count:,} unique trigrams")

    conn.close()


def step3_extract_regional_ngrams(db_path: str):
    """Step 3: Extract regional n-gram frequencies."""
    print("\n" + "="*60)
    print("Step 3: Extracting Regional N-grams")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    levels = ['市级', '县区级', '乡镇']

    with NgramExtractor(db_path) as extractor:
        for level in levels:
            print(f"\nProcessing level: {level}")

            # Bigrams
            print(f"  Extracting bigrams for {level}...")
            bigram_data = extractor.extract_regional_ngrams(n=2, level=level)

            for region, position_data in bigram_data.items():
                for position, counter in position_data.items():
                    total = sum(counter.values())
                    for ngram, freq in counter.items():
                        percentage = (freq / total * 100) if total > 0 else 0
                        cursor.execute("""
                            INSERT OR REPLACE INTO regional_ngram_frequency
                            (region, level, ngram, n, position, frequency, total_count, percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (region, level, ngram, 2, position, freq, total, percentage))

            # Trigrams
            print(f"  Extracting trigrams for {level}...")
            trigram_data = extractor.extract_regional_ngrams(n=3, level=level)

            for region, position_data in trigram_data.items():
                for position, counter in position_data.items():
                    total = sum(counter.values())
                    for ngram, freq in counter.items():
                        percentage = (freq / total * 100) if total > 0 else 0
                        cursor.execute("""
                            INSERT OR REPLACE INTO regional_ngram_frequency
                            (region, level, ngram, n, position, frequency, total_count, percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (region, level, ngram, 3, position, freq, total, percentage))

            conn.commit()
            print(f"  [OK] Completed {level}")

    print("\n[OK] Regional n-gram extraction complete")
    conn.close()


def step4_calculate_tendency(db_path: str):
    """Step 4: Calculate tendency scores."""
    print("\n" + "="*60)
    print("Step 4: Calculating Tendency Scores")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    levels = ['市级', '县区级', '乡镇']

    for level in levels:
        print(f"\nProcessing level: {level}")

        # Get all regional n-grams
        cursor.execute("""
            SELECT DISTINCT region, ngram, n, position
            FROM regional_ngram_frequency
            WHERE level = ?
        """, (level,))

        rows = cursor.fetchall()
        total_rows = len(rows)

        for idx, (region, ngram, n, position) in enumerate(rows, 1):
            if idx % 1000 == 0:
                print(f"  Progress: {idx}/{total_rows}")

            # Get regional counts
            cursor.execute("""
                SELECT frequency, total_count
                FROM regional_ngram_frequency
                WHERE region = ? AND level = ? AND ngram = ? AND n = ? AND position = ?
            """, (region, level, ngram, n, position))

            regional_result = cursor.fetchone()
            if not regional_result:
                continue

            regional_count, regional_total = regional_result

            # Get global counts
            cursor.execute("""
                SELECT frequency, total_count
                FROM ngram_frequency
                WHERE ngram = ? AND n = ? AND position = ?
            """, (ngram, n, position))

            global_result = cursor.fetchone()
            if not global_result:
                continue

            global_count, global_total = global_result

            # Calculate tendency
            tendency = analyzer.calculate_tendency(
                regional_count, regional_total,
                global_count, global_total
            )

            # Store results
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_tendency
                (region, level, ngram, n, position, lift, log_odds, z_score,
                 regional_count, regional_total, global_count, global_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                region, level, ngram, n, position,
                tendency['lift'], tendency['log_odds'], tendency['z_score'],
                regional_count, regional_total, global_count, global_total
            ))

        conn.commit()
        print(f"  [OK] Completed {level}")

    analyzer.__exit__(None, None, None)
    conn.close()
    print("\n[OK] Tendency calculation complete")


def step5_calculate_significance(db_path: str):
    """Step 5: Calculate statistical significance."""
    print("\n" + "="*60)
    print("Step 5: Calculating Statistical Significance")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    levels = ['市级', '县区级', '乡镇']
    alpha = 0.05  # Significance level

    for level in levels:
        print(f"\nProcessing level: {level}")

        # Get all tendency records
        cursor.execute("""
            SELECT region, ngram, n, position,
                   regional_count, regional_total, global_count, global_total
            FROM ngram_tendency
            WHERE level = ?
        """, (level,))

        rows = cursor.fetchall()
        total_rows = len(rows)

        for idx, row in enumerate(rows, 1):
            if idx % 1000 == 0:
                print(f"  Progress: {idx}/{total_rows}")

            region, ngram, n, position, regional_count, regional_total, global_count, global_total = row

            # Calculate significance
            sig = analyzer.calculate_significance(
                regional_count, regional_total,
                global_count, global_total
            )

            is_significant = 1 if sig['p_value'] < alpha else 0

            # Store results
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_significance
                (region, level, ngram, n, position, chi2, p_value, cramers_v, is_significant)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                region, level, ngram, n, position,
                sig['chi2'], sig['p_value'], sig['cramers_v'], is_significant
            ))

        conn.commit()
        print(f"  [OK] Completed {level}")

    analyzer.__exit__(None, None, None)
    conn.close()
    print("\n[OK] Significance testing complete")


def step6_detect_patterns(db_path: str):
    """Step 6: Detect structural patterns."""
    print("\n" + "="*60)
    print("Step 6: Detecting Structural Patterns")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    detector = StructuralPatternDetector(db_path)

    # Get bigrams and trigrams
    from collections import Counter

    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 2 AND position = 'all'
        ORDER BY frequency DESC
    """)
    bigrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})

    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 3 AND position = 'all'
        ORDER BY frequency DESC
    """)
    trigrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})

    # Detect bigram templates
    print("\nDetecting bigram templates...")
    bigram_templates = detector.detect_templates(bigrams, min_freq=100)

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

    print(f"  [OK] Found {len(bigram_templates)} bigram templates")

    # Detect trigram templates
    print("Detecting trigram templates...")
    trigram_templates = detector.detect_templates(trigrams, min_freq=50)

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

    print(f"  [OK] Found {len(trigram_templates)} trigram templates")

    conn.commit()
    conn.close()
    print("\n[OK] Pattern detection complete")


def main():
    """Main execution function."""
    db_path = 'data/villages.db'

    print("\n" + "="*60)
    print("Phase 12: N-gram Structure Analysis")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    try:
        step1_create_tables(db_path)
        step2_extract_global_ngrams(db_path)
        step3_extract_regional_ngrams(db_path)
        step4_calculate_tendency(db_path)
        step5_calculate_significance(db_path)
        step6_detect_patterns(db_path)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*60)
        print("Phase 12 Complete!")
        print("="*60)
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print("\nAll n-gram analysis results stored in database.")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

