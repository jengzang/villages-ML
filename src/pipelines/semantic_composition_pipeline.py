"""Semantic composition analysis pipeline.

Analyzes how semantic categories combine within village names:
1. Creates composition tables
2. Analyzes category co-occurrence (bigrams + trigrams, basic + detailed)
3. Calculates PMI for category pairs (basic + detailed)
4. Detects structural composition patterns (basic + detailed)
5. Detects semantic conflicts (basic + detailed)
6. Extracts per-village semantic structures
7. Generates detailed semantic indices
"""

import json
import logging
import sqlite3
import time
from collections import Counter
from pathlib import Path

import pandas as pd

from src.schema import REGION_LEVELS, get_schema
from src.semantic_composition import SemanticCompositionAnalyzer
from src.semantic_composition_schema import create_semantic_composition_tables
from src.semantic.lexicon_loader import SemanticLexicon
from src.semantic.semantic_index import SemanticIndexCalculator
from src.config.semantic_roles import MODIFIER_CATEGORIES, HEAD_CATEGORIES

logger = logging.getLogger(__name__)

_project_root = Path(__file__).parent.parent.parent


def run_semantic_composition_pipeline(
    db_path: str,
    run_id: str = 'semantic_indices_detailed_001',
    basic_lexicon_path: str = 'data/semantic_lexicon_v1.json',
    detailed_lexicon_path: str = '',
    lexicon_path: str = 'data/semantic_lexicon_v4.json',
    conflict_threshold: int = 5,
    region_levels: list[str] | None = None,
    skip_village_structures: bool = False,
    structure_progress_interval: int = 10000,
    schema_name: str = 'guangdong',
    output_dir: str | None = None,
) -> dict:
    """Run the complete semantic composition analysis pipeline."""
    if region_levels is None:
        region_levels = REGION_LEVELS[:3]
    S = get_schema(schema_name)

    logger.info("=" * 60)
    logger.info("Semantic Composition Analysis Pipeline")
    logger.info(f"  Run ID: {run_id}")
    logger.info(f"  Basic lexicon: {basic_lexicon_path}")
    logger.info(f"  Detailed lexicon: {detailed_lexicon_path}")
    logger.info("=" * 60)

    start_time = time.time()

    # Step 1: Create tables
    logger.info("Step 1: Creating composition tables...")
    exclude_tables = {"village_semantic_structure"} if skip_village_structures else set()
    create_semantic_composition_tables(db_path, exclude_tables=exclude_tables)

    # Step 2: Analyze compositions (bigrams + trigrams, basic + detailed)
    logger.info("Step 2: Analyzing compositions...")
    _step2_analyze_compositions(db_path, basic_lexicon_path, detailed_lexicon_path, S)

    # Step 3: Calculate PMI
    logger.info("Step 3: Calculating PMI...")
    _step3_calculate_pmi(db_path, S)

    # Step 4: Detect patterns
    logger.info("Step 4: Detecting patterns...")
    _step4_detect_patterns(db_path, S)

    # Step 5: Detect conflicts
    logger.info("Step 5: Detecting conflicts...")
    _step5_detect_conflicts(db_path, basic_lexicon_path, detailed_lexicon_path, conflict_threshold, S)

    # Step 6: Village structures
    if not skip_village_structures:
        logger.info("Step 6: Extracting village structures...")
        _step6_extract_village_structures(db_path, basic_lexicon_path, structure_progress_interval, S)
    else:
        logger.info("Step 6: SKIPPED (--skip-village-structures)")

    # Step 7: Semantic indices
    logger.info("Step 7: Generating semantic indices...")
    _step7_generate_semantic_indices(db_path, run_id, lexicon_path, region_levels, S)

    elapsed = time.time() - start_time
    logger.info(f"Semantic composition pipeline completed in {elapsed:.1f}s")

    return {
        'run_id': run_id,
        'region_levels': region_levels,
        'runtime_seconds': round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------


def _step2_analyze_compositions(db_path, basic_lexicon_path, detailed_lexicon_path, S):
    """Analyze semantic compositions — basic (v1, 9 categories) + detailed (v4, 53 subcategories)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ---------- Part 1: BASIC tables (v1, 9 main categories) ----------
    logger.info("Part 1: Generating BASIC tables (9 main categories, v1)...")
    cursor.execute("DELETE FROM semantic_bigrams")
    cursor.execute("DELETE FROM semantic_trigrams")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path, lexicon_path=basic_lexicon_path, schema=S) as analyzer:
        logger.info("Extracting semantic compositions (v1)...")
        compositions = analyzer.analyze_all_compositions()

        bigrams = compositions['bigrams']
        total_bigrams = sum(bigrams.values())
        for (cat1, cat2), freq in bigrams.items():
            percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_bigrams (category1, category2, frequency, percentage) "
                "VALUES (?, ?, ?, ?)",
                (cat1, cat2, freq, percentage),
            )

        trigrams = compositions['trigrams']
        total_trigrams = sum(trigrams.values())
        for (cat1, cat2, cat3), freq in trigrams.items():
            percentage = (freq / total_trigrams * 100) if total_trigrams > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_trigrams (category1, category2, category3, frequency, percentage) "
                "VALUES (?, ?, ?, ?, ?)",
                (cat1, cat2, cat3, freq, percentage),
            )
        conn.commit()
        logger.info(f"  {len(bigrams)} unique bigrams, {len(trigrams)} unique trigrams (basic)")

    # ---------- Part 2: DETAILED tables (v4, 53 subcategories) ----------
    logger.info("Part 2: Generating DETAILED tables (53 subcategories, v4)...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_bigrams_detailed (
            category1 TEXT NOT NULL, category2 TEXT NOT NULL,
            frequency INTEGER NOT NULL, percentage REAL NOT NULL, pmi REAL,
            PRIMARY KEY (category1, category2)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_trigrams_detailed (
            category1 TEXT NOT NULL, category2 TEXT NOT NULL, category3 TEXT NOT NULL,
            frequency INTEGER NOT NULL, percentage REAL NOT NULL,
            PRIMARY KEY (category1, category2, category3)
        )
    """)
    cursor.execute("DELETE FROM semantic_bigrams_detailed")
    cursor.execute("DELETE FROM semantic_trigrams_detailed")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path, lexicon_path=detailed_lexicon_path, schema=S) as analyzer:
        logger.info("Extracting semantic compositions (v4)...")
        compositions = analyzer.analyze_all_compositions()

        bigrams = compositions['bigrams']
        total_bigrams = sum(bigrams.values())
        for (cat1, cat2), freq in bigrams.items():
            percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_bigrams_detailed (category1, category2, frequency, percentage) "
                "VALUES (?, ?, ?, ?)",
                (cat1, cat2, freq, percentage),
            )

        trigrams = compositions['trigrams']
        total_trigrams = sum(trigrams.values())
        for (cat1, cat2, cat3), freq in trigrams.items():
            percentage = (freq / total_trigrams * 100) if total_trigrams > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_trigrams_detailed "
                "(category1, category2, category3, frequency, percentage) VALUES (?, ?, ?, ?, ?)",
                (cat1, cat2, cat3, freq, percentage),
            )
        conn.commit()
        logger.info(f"  {len(bigrams)} unique bigrams, {len(trigrams)} unique trigrams (detailed)")

    conn.close()


def _step3_calculate_pmi(db_path, S):
    """Calculate PMI for BOTH basic and detailed bigram tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ---------- Part 1: BASIC PMI ----------
    logger.info("Part 1: Calculating PMI for BASIC tables (9 categories)...")
    cursor.execute("DELETE FROM semantic_pmi")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path, schema=S) as analyzer:
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
        bigrams = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}
        pmi_scores = analyzer.calculate_pmi(bigrams)

        for (cat1, cat2), pmi in pmi_scores.items():
            cursor.execute(
                "UPDATE semantic_bigrams SET pmi = ? WHERE category1 = ? AND category2 = ?",
                (pmi, cat1, cat2),
            )
            freq = bigrams.get((cat1, cat2), 0)
            is_positive = 1 if pmi > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_pmi (category1, category2, pmi, frequency, is_positive) "
                "VALUES (?, ?, ?, ?, ?)",
                (cat1, cat2, pmi, freq, is_positive),
            )
        conn.commit()
        logger.info(f"  PMI calculated for {len(pmi_scores)} basic bigrams")

    # ---------- Part 2: DETAILED PMI ----------
    logger.info("Part 2: Calculating PMI for DETAILED tables (53 subcategories)...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_pmi_detailed (
            category1 TEXT NOT NULL, category2 TEXT NOT NULL,
            pmi REAL NOT NULL, frequency INTEGER NOT NULL,
            is_positive INTEGER NOT NULL,
            PRIMARY KEY (category1, category2)
        )
    """)
    cursor.execute("DELETE FROM semantic_pmi_detailed")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path, schema=S) as analyzer:
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams_detailed")
        bigrams_detailed = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}
        pmi_scores_detailed = analyzer.calculate_pmi(bigrams_detailed)

        for (cat1, cat2), pmi in pmi_scores_detailed.items():
            cursor.execute(
                "UPDATE semantic_bigrams_detailed SET pmi = ? WHERE category1 = ? AND category2 = ?",
                (pmi, cat1, cat2),
            )
            freq = bigrams_detailed.get((cat1, cat2), 0)
            is_positive = 1 if pmi > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_pmi_detailed "
                "(category1, category2, pmi, frequency, is_positive) VALUES (?, ?, ?, ?, ?)",
                (cat1, cat2, pmi, freq, is_positive),
            )
        conn.commit()
        logger.info(f"  PMI calculated for {len(pmi_scores_detailed)} detailed bigrams")

    conn.close()


def _step4_detect_patterns(db_path, S):
    """Detect composition patterns — basic + detailed."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ---------- Part 1: BASIC patterns ----------
    logger.info("Part 1: Detecting patterns for BASIC tables (9 categories)...")
    with SemanticCompositionAnalyzer(db_path, schema=S) as analyzer:
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
        bigrams = Counter({(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()})

        patterns = analyzer.detect_modifier_head_patterns(bigrams)
        total_patterns = sum(p['frequency'] for p in patterns)

        for pattern in patterns:
            percentage = (pattern['frequency'] / total_patterns * 100) if total_patterns > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_composition_patterns "
                "(pattern, pattern_type, modifier, head, frequency, percentage, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    pattern['pattern'], pattern['type'],
                    pattern.get('modifier'), pattern.get('head'),
                    pattern['frequency'], percentage,
                    f"{pattern['type']} pattern",
                ),
            )
        conn.commit()
        logger.info(f"  {len(patterns)} patterns (basic)")

    # ---------- Part 2: DETAILED patterns ----------
    logger.info("Part 2: Detecting patterns for DETAILED tables (53 subcategories)...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_composition_patterns_detailed (
            pattern TEXT PRIMARY KEY, pattern_type TEXT NOT NULL,
            modifier TEXT, head TEXT,
            frequency INTEGER NOT NULL, percentage REAL NOT NULL, description TEXT
        )
    """)
    cursor.execute("DELETE FROM semantic_composition_patterns_detailed")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path, schema=S) as analyzer:
        cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams_detailed")
        bigrams_detailed = Counter({(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()})

        patterns_detailed = analyzer.detect_modifier_head_patterns(bigrams_detailed)
        total_patterns_detailed = sum(p['frequency'] for p in patterns_detailed)

        for pattern in patterns_detailed:
            percentage = (pattern['frequency'] / total_patterns_detailed * 100) if total_patterns_detailed > 0 else 0
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_composition_patterns_detailed "
                "(pattern, pattern_type, modifier, head, frequency, percentage, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    pattern['pattern'], pattern['type'],
                    pattern.get('modifier'), pattern.get('head'),
                    pattern['frequency'], percentage,
                    f"{pattern['type']} pattern",
                ),
            )
        conn.commit()
        logger.info(f"  {len(patterns_detailed)} patterns (detailed)")

    conn.close()


def _step5_detect_conflicts(db_path, basic_lexicon_path, detailed_lexicon_path, conflict_threshold, S):
    """Detect semantic conflicts — basic (v1) and detailed (v4)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ---------- Part 1: BASIC conflicts ----------
    logger.info("Part 1: Detecting BASIC conflicts (v1, 9 categories)...")
    cursor.execute("DELETE FROM semantic_conflicts")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path, lexicon_path=basic_lexicon_path, schema=S) as analyzer:
        compositions = analyzer.analyze_all_compositions()
        sequences = compositions['sequences']
        conflicts = analyzer.detect_semantic_conflicts(sequences, threshold=conflict_threshold)

        for conflict in conflicts:
            sequence_str = json.dumps(conflict['sequence'])
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_conflicts (sequence, frequency, conflict_type, description) "
                "VALUES (?, ?, ?, ?)",
                (sequence_str, conflict['frequency'], conflict['conflict_type'], conflict['description']),
            )
        conn.commit()
        logger.info(f"  {len(conflicts)} unusual combinations (basic)")

    # ---------- Part 2: DETAILED conflicts ----------
    logger.info("Part 2: Detecting DETAILED conflicts (v4, 53 subcategories)...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_conflicts_detailed (
            sequence TEXT NOT NULL, frequency INTEGER NOT NULL,
            conflict_type TEXT NOT NULL, description TEXT,
            PRIMARY KEY (sequence, conflict_type)
        )
    """)
    conn.commit()
    cursor.execute("DELETE FROM semantic_conflicts_detailed")
    conn.commit()

    with SemanticCompositionAnalyzer(db_path, lexicon_path=detailed_lexicon_path, schema=S) as analyzer:
        compositions = analyzer.analyze_all_compositions()
        sequences = compositions['sequences']
        conflicts = analyzer.detect_semantic_conflicts(sequences, threshold=conflict_threshold)

        for conflict in conflicts:
            sequence_str = json.dumps(conflict['sequence'])
            cursor.execute(
                "INSERT OR REPLACE INTO semantic_conflicts_detailed "
                "(sequence, frequency, conflict_type, description) VALUES (?, ?, ?, ?)",
                (sequence_str, conflict['frequency'], conflict['conflict_type'], conflict['description']),
            )
        conn.commit()
        logger.info(f"  {len(conflicts)} unusual combinations (detailed)")

    conn.close()


def _step6_extract_village_structures(db_path, basic_lexicon_path, progress_interval, S):
    """Extract per-village semantic structures."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with SemanticCompositionAnalyzer(db_path, lexicon_path=basic_lexicon_path, schema=S) as analyzer:
        char_labels = analyzer.get_character_labels()

        cursor.execute(f"""
            SELECT {S.village_id_col}, {S.committee_col_preprocessed}, {S.village_name_col_prefix_removed}
            FROM {S.preprocessed_table}
        """)
        all_villages = cursor.fetchall()
        logger.info(f"Loaded {len(all_villages):,} villages from database")

        count = 0
        skipped = 0
        insert_cursor = conn.cursor()

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

            labeled_count = sum(1 for cat in sequence if cat != 'other')
            coverage = labeled_count / len(sequence) if len(sequence) > 0 else 0

            if coverage < 0.5:
                skipped += 1
                continue

            sequence_str = json.dumps(sequence)
            sequence_length = len(sequence)

            parents = {cat.split('_', 1)[0] for cat in sequence}
            has_modifier = 1 if parents & MODIFIER_CATEGORIES else 0
            has_head = 1 if parents & HEAD_CATEGORIES else 0
            has_settlement = 1 if 'settlement' in parents else 0

            insert_cursor.execute(
                "INSERT OR REPLACE INTO village_semantic_structure "
                "(village_id, committee, village_name, semantic_sequence, sequence_length, "
                "has_modifier, has_head, has_settlement) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (village_id, village_committee, village_name, sequence_str, sequence_length,
                 has_modifier, has_head, has_settlement),
            )

            count += 1
            if progress_interval > 0 and count % progress_interval == 0:
                logger.info(f"  Progress: {count:,} villages processed, {skipped:,} skipped")
                conn.commit()

        conn.commit()
        logger.info(f"Extracted structures for {count:,} villages, skipped {skipped:,}")

    conn.close()


def _step7_generate_semantic_indices(db_path, run_id, lexicon_path, region_levels, S):
    """Generate semantic_indices_detailed using v4 lexicon."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_indices_detailed (
            run_id TEXT NOT NULL, region_level TEXT NOT NULL, region_name TEXT NOT NULL,
            category TEXT NOT NULL,
            raw_intensity REAL NOT NULL, normalized_index REAL NOT NULL,
            z_score REAL, rank_within_province INTEGER NOT NULL, village_count INTEGER,
            city TEXT, county TEXT, township TEXT,
            PRIMARY KEY (run_id, region_level, region_name, category)
        )
    """)
    conn.commit()
    cursor.execute("DELETE FROM semantic_indices_detailed")
    conn.commit()

    lexicon = SemanticLexicon(lexicon_path)
    logger.info(f"Loaded v4 lexicon: {len(lexicon.list_categories())} categories")

    villages_df = pd.read_sql_query(f"""
        SELECT {S.city_col}, {S.county_col}, {S.township_col},
               {S.village_name_col_prefix_removed} as 自然村
        FROM {S.preprocessed_table}
    """, conn)
    logger.info(f"Loaded {len(villages_df):,} villages")

    calculator = SemanticIndexCalculator(lexicon)
    all_indices = []
    requested_levels = set(region_levels)

    level_config = [
        (REGION_LEVELS[0], S.city_col, REGION_LEVELS[0]),
        (REGION_LEVELS[1], S.county_col, REGION_LEVELS[1]),
        (REGION_LEVELS[2], S.township_col, REGION_LEVELS[2]),
    ]

    for level, col_name, group_col in level_config:
        if level not in requested_levels:
            continue
        logger.info(f"Processing {level} level...")

        if level == REGION_LEVELS[0]:
            level_df = villages_df[[S.city_col, '自然村']].copy()
            level_df = level_df.rename(columns={S.city_col: REGION_LEVELS[0]})
        elif level == REGION_LEVELS[1]:
            level_df = villages_df[[S.city_col, S.county_col, '自然村']].copy()
            level_df = level_df.rename(columns={S.city_col: REGION_LEVELS[0], S.county_col: REGION_LEVELS[1]})
        else:
            level_df = villages_df[[S.city_col, S.county_col, S.township_col, '自然村']].copy()
            level_df = level_df.rename(columns={
                S.city_col: REGION_LEVELS[0], S.county_col: REGION_LEVELS[1], S.township_col: REGION_LEVELS[2],
            })

        level_df = level_df[level_df[group_col].notna()]
        village_scores = calculator.calculate_semantic_scores(level_df)
        regional_indices = calculator.calculate_regional_indices(village_scores, level_column=group_col)
        regional_indices['region_level'] = level
        regional_indices['run_id'] = run_id
        all_indices.append(regional_indices)
        logger.info(f"  {len(regional_indices)} region-category pairs")

    if not all_indices:
        logger.warning("No semantic index levels selected; skipping detailed indices")
        conn.close()
        return

    combined = pd.concat(all_indices, ignore_index=True)

    col_name_map = {REGION_LEVELS[0]: S.city_col, REGION_LEVELS[1]: S.county_col, REGION_LEVELS[2]: S.township_col}
    village_counts = {}
    for (lvl, rname), grp in combined.groupby(['region_level', 'region_name']):
        col = col_name_map[lvl]
        cursor.execute(f'SELECT COUNT(*) FROM {S.preprocessed_table} WHERE "{col}" = ?', (rname,))
        village_counts[(lvl, rname)] = cursor.fetchone()[0]

    combined['village_count'] = combined.apply(
        lambda r: village_counts.get((r['region_level'], r['region_name']), 0), axis=1,
    )

    logger.info(f"Writing {len(combined):,} records to semantic_indices_detailed...")
    columns = ['run_id', 'region_level', 'region_name', 'category',
               'raw_intensity', 'normalized_index', 'z_score',
               'rank_within_province', 'village_count']
    data = combined[columns].values.tolist()
    cursor.executemany(
        "INSERT OR REPLACE INTO semantic_indices_detailed "
        "(run_id, region_level, region_name, category, raw_intensity, normalized_index, z_score, "
        "rank_within_province, village_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        data,
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM semantic_indices_detailed")
    cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT category) FROM semantic_indices_detailed")
    cats = cursor.fetchone()[0]
    logger.info(f"semantic_indices_detailed: {cnt:,} records, {cats} categories")
    conn.close()
