#!/usr/bin/env python3
"""
Phase 14: Semantic Composition Analysis

This script analyzes how semantic categories combine in village names:
1. Extract semantic category sequences
2. Analyze semantic bigrams and trigrams
3. Detect modifier-head patterns
4. Identify semantic conflicts
5. Calculate PMI scores

Approach: Offline-heavy, maximum accuracy, leverages Phase 2 semantic labels
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from semantic_composition import SemanticCompositionAnalyzer
from semantic_composition_schema import create_semantic_composition_tables


def step1_create_tables(db_path: str):
    """Step 1: Create database tables."""
    print("\n" + "="*60)
    print("Step 1: Creating Semantic Composition Tables")
    print("="*60)

    create_semantic_composition_tables(db_path)
    print("[OK] Tables created successfully")


def step2_analyze_compositions(db_path: str):
    """Step 2: Analyze all semantic compositions."""
    print("\n" + "="*60)
    print("Step 2: Analyzing Semantic Compositions")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        print("\nExtracting semantic compositions...")
        compositions = analyzer.analyze_all_compositions()

        # Store bigrams
        print("Storing semantic bigrams...")
        bigrams = compositions['bigrams']
        total_bigrams = sum(bigrams.values())

        for (cat1, cat2), freq in bigrams.items():
            percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_bigrams
                (category1, category2, frequency, percentage)
                VALUES (?, ?, ?, ?)
            """, (cat1, cat2, freq, percentage))

        # Store trigrams
        print("Storing semantic trigrams...")
        trigrams = compositions['trigrams']
        total_trigrams = sum(trigrams.values())

        for (cat1, cat2, cat3), freq in trigrams.items():
            percentage = (freq / total_trigrams * 100) if total_trigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_trigrams
                (category1, category2, category3, frequency, percentage)
                VALUES (?, ?, ?, ?, ?)
            """, (cat1, cat2, cat3, freq, percentage))

        conn.commit()

        # Print statistics
        print(f"\n[OK] Extracted {len(bigrams):,} unique semantic bigrams")
        print(f"[OK] Extracted {len(trigrams):,} unique semantic trigrams")

    conn.close()


def step3_calculate_pmi(db_path: str):
    """Step 3: Calculate PMI scores."""
    print("\n" + "="*60)
    print("Step 3: Calculating PMI Scores")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        # Get bigrams
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
        bigrams = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}

        print("\nCalculating PMI...")
        pmi_scores = analyzer.calculate_pmi(bigrams)

        # Update bigrams table with PMI
        for (cat1, cat2), pmi in pmi_scores.items():
            cursor.execute("""
                UPDATE semantic_bigrams
                SET pmi = ?
                WHERE category1 = ? AND category2 = ?
            """, (pmi, cat1, cat2))

            # Also store in semantic_pmi table
            freq = bigrams.get((cat1, cat2), 0)
            is_positive = 1 if pmi > 0 else 0

            cursor.execute("""
                INSERT OR REPLACE INTO semantic_pmi
                (category1, category2, pmi, frequency, is_positive)
                VALUES (?, ?, ?, ?, ?)
            """, (cat1, cat2, pmi, freq, is_positive))

        conn.commit()
        print(f"[OK] Calculated PMI for {len(pmi_scores):,} bigrams")

    conn.close()


def step4_detect_patterns(db_path: str):
    """Step 4: Detect composition patterns."""
    print("\n" + "="*60)
    print("Step 4: Detecting Composition Patterns")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        # Get bigrams
        from collections import Counter
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
        bigrams = Counter({(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()})

        print("\nDetecting modifier-head patterns...")
        patterns = analyzer.detect_modifier_head_patterns(bigrams)

        total_patterns = sum(p['frequency'] for p in patterns)

        for pattern in patterns:
            percentage = (pattern['frequency'] / total_patterns * 100) if total_patterns > 0 else 0

            cursor.execute("""
                INSERT OR REPLACE INTO semantic_composition_patterns
                (pattern, pattern_type, modifier, head, frequency, percentage, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern['pattern'],
                pattern['type'],
                pattern.get('modifier'),
                pattern.get('head'),
                pattern['frequency'],
                percentage,
                f"{pattern['type']} pattern"
            ))

        conn.commit()
        print(f"[OK] Found {len(patterns):,} composition patterns")

    conn.close()


def step5_detect_conflicts(db_path: str):
    """Step 5: Detect semantic conflicts."""
    print("\n" + "="*60)
    print("Step 5: Detecting Semantic Conflicts")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        # Get all sequences
        compositions = analyzer.analyze_all_compositions()
        sequences = compositions['sequences']

        print("\nDetecting unusual combinations...")
        conflicts = analyzer.detect_semantic_conflicts(sequences, threshold=5)

        for conflict in conflicts:
            sequence_str = json.dumps(conflict['sequence'])

            cursor.execute("""
                INSERT OR REPLACE INTO semantic_conflicts
                (sequence, frequency, conflict_type, description)
                VALUES (?, ?, ?, ?)
            """, (
                sequence_str,
                conflict['frequency'],
                conflict['conflict_type'],
                conflict['description']
            ))

        conn.commit()
        print(f"[OK] Found {len(conflicts):,} unusual combinations")

    conn.close()


def step6_extract_village_structures(db_path: str):
    """Step 6: Extract per-village semantic structures."""
    print("\n" + "="*60)
    print("Step 6: Extracting Village Semantic Structures")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        char_labels = analyzer.get_character_labels()

        # Use SELECT * and access by index to avoid encoding issues
        cursor.execute("SELECT * FROM 广东省自然村")

        count = 0
        skipped = 0
        for row in cursor:
            village_committee = row[3]  # 村委会 is at index 3
            village_name = row[4]        # 自然村 is at index 4

            if not village_name:
                continue

            sequence = analyzer.extract_semantic_sequence(village_name, char_labels)

            if len(sequence) == 0:
                skipped += 1
                continue

            # Calculate labeling coverage
            labeled_count = sum(1 for cat in sequence if cat != 'other')
            coverage = labeled_count / len(sequence) if len(sequence) > 0 else 0

            # Only process villages with at least 50% labeled characters
            if coverage < 0.5:
                skipped += 1
                continue

            sequence_str = json.dumps(sequence)
            sequence_length = len(sequence)

            # Check for specific categories
            has_modifier = 1 if any(cat in ['size', 'direction', 'number'] for cat in sequence) else 0
            has_head = 1 if any(cat in ['water', 'mountain', 'landform', 'vegetation'] for cat in sequence) else 0
            has_settlement = 1 if 'settlement' in sequence else 0

            cursor.execute("""
                INSERT OR REPLACE INTO village_semantic_structure
                (村委会, 自然村, semantic_sequence, sequence_length,
                 has_modifier, has_head, has_settlement)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                village_committee, village_name, sequence_str, sequence_length,
                has_modifier, has_head, has_settlement
            ))

            count += 1
            if count % 10000 == 0:
                print(f"  Progress: {count:,} villages processed, {skipped:,} skipped")
                conn.commit()

        conn.commit()
        print(f"\n[OK] Extracted structures for {count:,} villages")
        print(f"     Skipped {skipped:,} villages (< 50% labeled)")

    conn.close()


def main():
    """Main execution function."""
    db_path = 'data/villages.db'

    print("\n" + "="*60)
    print("Phase 14: Semantic Composition Analysis")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    try:
        step1_create_tables(db_path)
        step2_analyze_compositions(db_path)
        step3_calculate_pmi(db_path)
        step4_detect_patterns(db_path)
        step5_detect_conflicts(db_path)
        step6_extract_village_structures(db_path)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*60)
        print("Phase 14 Complete!")
        print("="*60)
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print("\nAll semantic composition results stored in database.")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
