#!/usr/bin/env python3
"""
Phase 14: Semantic Composition Analysis

This script analyzes how semantic categories combine in village names:
1. Extract semantic category sequences
2. Analyze semantic bigrams and trigrams
3. Detect modifier-head patterns
4. Identify semantic conflicts
5. Calculate PMI scores

LEXICON VERSION: v3_expanded (78 subcategories)
- Provides fine-grained semantic analysis
- Matches semantic_bigrams table structure
- Path: data/semantic_lexicon_v3_expanded.json

Approach: Offline-heavy, maximum accuracy, leverages Phase 2 semantic labels
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.semantic_composition import SemanticCompositionAnalyzer
from src.semantic_composition_schema import create_semantic_composition_tables


def step1_create_tables(db_path: str):
    """Step 1: Create database tables."""
    print("\n" + "="*60)
    print("Step 1: Creating Semantic Composition Tables")
    print("="*60)

    create_semantic_composition_tables(db_path)
    print("[OK] Tables created successfully")


def step2_analyze_compositions(db_path: str):
    """Step 2: Analyze all semantic compositions - Generate BOTH basic and detailed tables."""
    print("\n" + "="*60)
    print("Step 2: Analyzing Semantic Compositions (Dual Version)")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ========== Part 1: Generate BASIC tables (9 main categories, v1) ==========
    print("\n[Part 1] Generating BASIC tables (9 main categories, v1)...")

    # Clear existing data from basic tables
    cursor.execute("DELETE FROM semantic_bigrams")
    cursor.execute("DELETE FROM semantic_trigrams")
    conn.commit()

    lexicon_v1 = project_root / 'data' / 'semantic_lexicon_v1.json'

    with SemanticCompositionAnalyzer(db_path, lexicon_path=str(lexicon_v1)) as analyzer:
        print("Extracting semantic compositions (v1)...")
        compositions = analyzer.analyze_all_compositions()

        # Store bigrams (basic)
        print("Storing semantic_bigrams (9 categories)...")
        bigrams = compositions['bigrams']
        total_bigrams = sum(bigrams.values())

        for (cat1, cat2), freq in bigrams.items():
            percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_bigrams
                (category1, category2, frequency, percentage)
                VALUES (?, ?, ?, ?)
            """, (cat1, cat2, freq, percentage))

        # Store trigrams (basic)
        print("Storing semantic_trigrams (9 categories)...")
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
        print(f"[OK] Extracted {len(bigrams):,} unique semantic bigrams (basic)")
        print(f"[OK] Extracted {len(trigrams):,} unique semantic trigrams (basic)")

    # ========== Part 2: Generate DETAILED tables (76 subcategories, v4_hybrid) ==========
    print("\n[Part 2] Generating DETAILED tables (76 subcategories, v4_hybrid)...")

    # Create detailed tables if not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_bigrams_detailed (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            pmi REAL,
            PRIMARY KEY (category1, category2)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_trigrams_detailed (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            category3 TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (category1, category2, category3)
        )
    """)

    # Clear existing data from detailed tables
    cursor.execute("DELETE FROM semantic_bigrams_detailed")
    cursor.execute("DELETE FROM semantic_trigrams_detailed")
    conn.commit()

    lexicon_v4 = project_root / 'data' / 'semantic_lexicon_v4_hybrid.json'

    with SemanticCompositionAnalyzer(db_path, lexicon_path=str(lexicon_v4)) as analyzer:
        print("Extracting semantic compositions (v4_hybrid)...")
        compositions = analyzer.analyze_all_compositions()

        # Store bigrams (detailed)
        print("Storing semantic_bigrams_detailed (76 subcategories)...")
        bigrams = compositions['bigrams']
        total_bigrams = sum(bigrams.values())

        for (cat1, cat2), freq in bigrams.items():
            percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_bigrams_detailed
                (category1, category2, frequency, percentage)
                VALUES (?, ?, ?, ?)
            """, (cat1, cat2, freq, percentage))

        # Store trigrams (detailed)
        print("Storing semantic_trigrams_detailed (76 subcategories)...")
        trigrams = compositions['trigrams']
        total_trigrams = sum(trigrams.values())

        for (cat1, cat2, cat3), freq in trigrams.items():
            percentage = (freq / total_trigrams * 100) if total_trigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_trigrams_detailed
                (category1, category2, category3, frequency, percentage)
                VALUES (?, ?, ?, ?, ?)
            """, (cat1, cat2, cat3, freq, percentage))

        conn.commit()
        print(f"[OK] Extracted {len(bigrams):,} unique semantic bigrams (detailed)")
        print(f"[OK] Extracted {len(trigrams):,} unique semantic trigrams (detailed)")

    conn.close()


def step3_calculate_pmi(db_path: str):
    """Step 3: Calculate PMI scores for BOTH basic and detailed tables."""
    print("\n" + "="*60)
    print("Step 3: Calculating PMI Scores (Dual Version)")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ========== Part 1: Calculate PMI for BASIC tables (9 categories) ==========
    print("\n[Part 1] Calculating PMI for BASIC tables (9 categories)...")

    # Clear existing PMI data
    cursor.execute("DELETE FROM semantic_pmi")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        # Get bigrams from basic table
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
        bigrams = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}

        print("Calculating PMI for basic bigrams...")
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
        print(f"[OK] Calculated PMI for {len(pmi_scores):,} basic bigrams")

    # ========== Part 2: Calculate PMI for DETAILED tables (76 subcategories) ==========
    print("\n[Part 2] Calculating PMI for DETAILED tables (76 subcategories)...")

    # Create detailed PMI table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_pmi_detailed (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            pmi REAL NOT NULL,
            frequency INTEGER NOT NULL,
            is_positive INTEGER NOT NULL,
            PRIMARY KEY (category1, category2)
        )
    """)

    # Clear existing detailed PMI data
    cursor.execute("DELETE FROM semantic_pmi_detailed")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        # Get bigrams from detailed table
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams_detailed")
        bigrams_detailed = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}

        print("Calculating PMI for detailed bigrams...")
        pmi_scores_detailed = analyzer.calculate_pmi(bigrams_detailed)

        # Update detailed bigrams table with PMI
        for (cat1, cat2), pmi in pmi_scores_detailed.items():
            cursor.execute("""
                UPDATE semantic_bigrams_detailed
                SET pmi = ?
                WHERE category1 = ? AND category2 = ?
            """, (pmi, cat1, cat2))

            # Also store in semantic_pmi_detailed table
            freq = bigrams_detailed.get((cat1, cat2), 0)
            is_positive = 1 if pmi > 0 else 0

            cursor.execute("""
                INSERT OR REPLACE INTO semantic_pmi_detailed
                (category1, category2, pmi, frequency, is_positive)
                VALUES (?, ?, ?, ?, ?)
            """, (cat1, cat2, pmi, freq, is_positive))

        conn.commit()
        print(f"[OK] Calculated PMI for {len(pmi_scores_detailed):,} detailed bigrams")

    conn.close()


def step4_detect_patterns(db_path: str):
    """Step 4: Detect composition patterns for BOTH basic and detailed tables."""
    print("\n" + "="*60)
    print("Step 4: Detecting Composition Patterns (Dual Version)")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ========== Part 1: Detect patterns for BASIC tables (9 categories) ==========
    print("\n[Part 1] Detecting patterns for BASIC tables (9 categories)...")

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        # Get bigrams from basic table
        from collections import Counter
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
        bigrams = Counter({(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()})

        print("Detecting modifier-head patterns...")
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
        print(f"[OK] Found {len(patterns)} composition patterns (basic)")

    # ========== Part 2: Detect patterns for DETAILED tables (76 subcategories) ==========
    print("\n[Part 2] Detecting patterns for DETAILED tables (76 subcategories)...")

    # Create detailed patterns table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_composition_patterns_detailed (
            pattern TEXT PRIMARY KEY,
            pattern_type TEXT NOT NULL,
            modifier TEXT,
            head TEXT,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            description TEXT
        )
    """)

    # Clear existing data
    cursor.execute("DELETE FROM semantic_composition_patterns_detailed")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path) as analyzer:
        # Get bigrams from detailed table
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams_detailed")
        bigrams_detailed = Counter({(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()})

        print("Detecting modifier-head patterns...")
        patterns_detailed = analyzer.detect_modifier_head_patterns(bigrams_detailed)

        total_patterns_detailed = sum(p['frequency'] for p in patterns_detailed)

        for pattern in patterns_detailed:
            percentage = (pattern['frequency'] / total_patterns_detailed * 100) if total_patterns_detailed > 0 else 0

            cursor.execute("""
                INSERT OR REPLACE INTO semantic_composition_patterns_detailed
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
        print(f"[OK] Found {len(patterns_detailed)} composition patterns (detailed)")

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

        # Query from preprocessed table to get village_id
        # Fetch all rows first to avoid cursor issues
        cursor.execute("""
            SELECT village_id, 村委会, 自然村_去前缀
            FROM 广东省自然村_预处理
        """)

        # Fetch all rows into memory
        all_villages = cursor.fetchall()
        print(f"\nLoaded {len(all_villages):,} villages from database")

        count = 0
        skipped = 0
        insert_cursor = conn.cursor()  # Separate cursor for inserts

        for row in all_villages:
            village_id = row[0]
            village_committee = row[1]
            village_name = row[2]

            if not village_name or not village_id:
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

            insert_cursor.execute("""
                INSERT OR REPLACE INTO village_semantic_structure
                (village_id, 村委会, 自然村, semantic_sequence, sequence_length,
                 has_modifier, has_head, has_settlement)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                village_id, village_committee, village_name, sequence_str, sequence_length,
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
