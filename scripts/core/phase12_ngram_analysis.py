#!/usr/bin/env python3
"""
Phase 12: N-gram Structure Analysis

This script performs comprehensive n-gram analysis on village names:
1. Extract bigrams and trigrams (全局和區域)
2. Calculate frequency statistics
3. Compute tendency scores (lift, z-score)
4. Statistical significance testing
5. Clean up non-significant data (NEW: 2026-02-25)
6. Detect structural patterns
7. Auto-update active_run_ids (NEW: 2026-02-25)
8. Populate village-level n-grams (NEW: 2026-07-12)

Approach: Offline-heavy, maximum accuracy, full dataset

IMPORTANT (2026-02-25):
- Only statistically significant n-grams (p < 0.05) are stored in the database
- Non-significant n-grams are filtered out during generation to optimize storage
- This reduces database size by ~40% while maintaining analytical quality
- Automatically updates active_run_ids table after completion
"""

import sqlite3
import sys
from pathlib import Path
import json
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ngram_analysis import NgramExtractor, NgramAnalyzer, StructuralPatternDetector
from src.ngram_schema import create_ngram_tables
from src.schema import VillageTableSchema, get_schema

# Make scripts/utils importable for the optional active_run_ids update.
sys.path.insert(0, str(project_root / 'scripts'))


def _parse_int_csv(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(',') if part.strip()]


def _parse_str_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(',') if part.strip()]


LEVEL_NAME_MAP = {
    REGION_LEVELS[0]: '市级',
    REGION_LEVELS[1]: '区县级',
    REGION_LEVELS[2]: '乡镇级',
}


def _parse_thresholds(value: str | None) -> dict[int, int]:
    """Parse ``2:3,3:2`` threshold strings into ``{2: 3, 3: 2}``."""
    if not value:
        return {}

    thresholds: dict[int, int] = {}
    for item in value.split(','):
        item = item.strip()
        if not item:
            continue
        n_text, threshold_text = item.split(':', 1)
        thresholds[int(n_text.strip())] = int(threshold_text.strip())
    return thresholds


def _filter_positions(position_data: dict, positions: list[str]) -> dict:
    requested = set(positions)
    return {position: counter for position, counter in position_data.items() if position in requested}


def step1_create_tables(db_path: str, exclude_tables: set[str] | None = None):
    """Step 1: Create database tables."""
    print("\n" + "="*60)
    print("Step 1: Creating N-gram Analysis Tables")
    print("="*60)

    create_ngram_tables(db_path, exclude_tables=exclude_tables)
    print("[OK] Tables created successfully")


def step2_extract_global_ngrams(
    db_path: str,
    n_values: list[int] | None = None,
    positions: list[str] | None = None,
    schema: VillageTableSchema | None = None,
):
    """Step 2: Extract global n-gram frequencies."""
    n_values = n_values or [2, 3, 4]
    positions = positions or ['all', 'prefix', 'suffix', 'middle']

    print("\n" + "="*60)
    print("Step 2: Extracting Global N-grams")
    print("="*60)

    # Extract n-grams first (read-only operation)
    with NgramExtractor(db_path, schema=schema or get_schema("guangdong")) as extractor:
        ngram_data_by_n = {}
        for n in n_values:
            print(f"\nExtracting {n}-grams...")
            ngram_data_by_n[n] = _filter_positions(
                extractor.extract_all_ngrams(n=n),
                positions,
            )

    # Now open connection for writing (after extractor is closed)
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    for n, position_data in ngram_data_by_n.items():
        print(f"\nStoring {n}-gram frequencies...")
        for position, counter in position_data.items():
            total = sum(counter.values())
            for ngram, freq in counter.items():
                percentage = (freq / total * 100) if total > 0 else 0
                cursor.execute("""
                    INSERT OR REPLACE INTO ngram_frequency
                    (ngram, n, position, frequency, total_count, percentage)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (ngram, n, position, freq, total, percentage))

    conn.commit()

    # Print statistics
    for n in n_values:
        cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_frequency WHERE n = ?", (n,))
        ngram_count = cursor.fetchone()[0]
        print(f"[OK] Extracted {ngram_count:,} unique {n}-grams")

    conn.close()


def step3_extract_regional_ngrams(
    db_path: str,
    n_values: list[int] | None = None,
    regional_levels: list[str] | None = None,
    positions: list[str] | None = None,
    schema: VillageTableSchema | None = None,
):
    """Step 3: Extract regional n-gram frequencies with hierarchical grouping.

    Each row contains full hierarchical path to handle duplicate place names.
    """
    n_values = n_values or [2, 3]
    regional_levels = regional_levels or [REGION_LEVELS[2]]
    positions = positions or ['all', 'prefix', 'suffix', 'middle']

    print("\n" + "="*60)
    print("Step 3: Extracting Regional N-grams")
    print("="*60)

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    with NgramExtractor(db_path, schema=schema or get_schema("guangdong")) as extractor:
        for level_en in regional_levels:
            level = LEVEL_NAME_MAP[level_en]
            print(f"\nProcessing level: {level}")

            for n in n_values:
                print(f"  Extracting {n}-grams for {level}...")
                ngram_data = extractor.extract_regional_ngrams(n=n, level=level_en)

                for hierarchical_key, position_data in ngram_data.items():
                    city, county, township = hierarchical_key
                    region_name = {REGION_LEVELS[0]: city, REGION_LEVELS[1]: county, REGION_LEVELS[2]: township}[level_en]

                    for position, counter in _filter_positions(position_data, positions).items():
                        total = sum(counter.values())
                        for ngram, freq in counter.items():
                            percentage = (freq / total * 100) if total > 0 else 0
                            cursor.execute("""
                                INSERT OR REPLACE INTO regional_ngram_frequency
                                (region_level, city, county, township, region_name, ngram, n, position, frequency, total_count, percentage)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (level_en, city, county, township, region_name, ngram, n, position, freq, total, percentage))

        conn.commit()
        print("  [OK] Completed configured levels")

    print("\n[OK] Regional n-gram extraction complete")
    conn.close()


def step3_5_calculate_regional_totals_raw(db_path: str):
    """Step 3.5: Calculate and store regional total raw counts (before filtering)."""
    print("\n" + "="*60)
    print("Step 3.5: Calculating Regional Total Raw Counts")
    print("="*60)

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    # Create temporary table to store raw totals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_regional_totals_raw (
            region_level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            total_raw INTEGER NOT NULL,
            PRIMARY KEY (region_level, city, county, township, n, position)
        )
    """)

    # Clear old data
    cursor.execute("DELETE FROM temp_regional_totals_raw")

    # Calculate raw totals for each region-position combination
    cursor.execute("""
        INSERT INTO temp_regional_totals_raw
        SELECT region_level, city, county, township, n, position, COUNT(*) as total_raw
        FROM regional_ngram_frequency
        GROUP BY region_level, city, county, township, n, position
    """)

    rows_inserted = cursor.rowcount
    print(f"  Calculated raw totals for {rows_inserted:,} region-position combinations")

    conn.commit()
    conn.close()

    print("[OK] Regional total raw counts calculated")


def step4_calculate_tendency(
    db_path: str,
    regional_levels: list[str] | None = None,
):
    """Step 4: Calculate tendency scores with hierarchical grouping.
    """
    regional_levels = regional_levels or [REGION_LEVELS[2]]

    print("\n" + "="*60)
    print("Step 4: Calculating Tendency Scores")
    print("="*60)

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    for level_en in regional_levels:
        print(f"\nProcessing level: {level_en}")
        print("  Using optimized JOIN query for better performance...")

        cursor.execute("""
            SELECT
                r.region_level, r.city, r.county, r.township, r.region_name, r.ngram, r.n, r.position,
                r.frequency as regional_count,
                r.total_count as regional_total,
                COALESCE(t.total_raw, r.total_count) as regional_total_raw,
                g.frequency as global_count,
                g.total_count as global_total
            FROM regional_ngram_frequency r
            LEFT JOIN temp_regional_totals_raw t
                ON r.region_level = t.region_level
                AND r.city IS t.city
                AND r.county IS t.county
                AND r.township IS t.township
                AND r.n = t.n
                AND r.position = t.position
            LEFT JOIN ngram_frequency g
                ON r.ngram = g.ngram
                AND r.n = g.n
                AND r.position = g.position
            WHERE r.region_level = ?
        """, (level_en,))

        rows = cursor.fetchall()
        total_rows = len(rows)
        print(f"  Total rows to process: {total_rows:,}")

        batch_size = 1000
        batch_data = []

        for idx, (level_db, city, county, township, region_name, ngram, n, position,
                  regional_count, regional_total, regional_total_raw,
                  global_count, global_total) in enumerate(rows, 1):

            if idx % 10000 == 0:
                print(f"  Progress: {idx:,}/{total_rows:,} ({idx/total_rows*100:.1f}%)")

            if global_count is None or global_total is None:
                continue

            tendency = analyzer.calculate_tendency(
                regional_count, regional_total,
                global_count, global_total
            )

            batch_data.append((
                level_en, city, county, township, region_name, ngram, n, position,
                tendency['lift'], tendency['log_odds'], tendency['z_score'],
                regional_count, regional_total, regional_total_raw, global_count, global_total
            ))

            if len(batch_data) >= batch_size:
                cursor.executemany("""
                    INSERT OR REPLACE INTO ngram_tendency
                    (region_level, city, county, township, region_name, ngram, n, position, lift, log_odds, z_score,
                     regional_count, regional_total, regional_total_raw, global_count, global_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch_data)
                conn.commit()
                batch_data = []

        if batch_data:
            cursor.executemany("""
                INSERT OR REPLACE INTO ngram_tendency
                (region_level, city, county, township, region_name, ngram, n, position, lift, log_odds, z_score,
                 regional_count, regional_total, regional_total_raw, global_count, global_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            conn.commit()

        print(f"  [OK] Completed {level_en}")

    analyzer.__exit__(None, None, None)
    conn.close()
    print("\n[OK] Tendency calculation complete")


def step5_calculate_significance(
    db_path: str,
    regional_levels: list[str] | None = None,
    alpha: float = 0.05,
):
    """Step 5: Calculate statistical significance.

    IMPORTANT: Only stores significant n-grams (p < 0.05) to optimize database size.
    Non-significant n-grams are not stored in ngram_significance table.
    """
    regional_levels = regional_levels or ['township']

    print("\n" + "="*60)
    print("Step 5: Calculating Statistical Significance")
    print("="*60)
    print(f"NOTE: Only storing significant n-grams (p < {alpha})")

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    # Track statistics
    total_tested = 0
    total_significant = 0

    for level_en in regional_levels:
        print(f"\nProcessing level: {level_en}")

        # Get all tendency records with hierarchical columns
        cursor.execute("""
            SELECT region_level, city, county, township, region_name, ngram, n, position,
                   regional_count, regional_total, global_count, global_total
            FROM ngram_tendency
            WHERE region_level = ?
        """, (level_en,))

        rows = cursor.fetchall()
        total_rows = len(rows)
        significant_count = 0

        for idx, row in enumerate(rows, 1):
            if idx % 1000 == 0:
                print(f"  Progress: {idx}/{total_rows} ({significant_count} significant)")

            level_db, city, county, township, region_name, ngram, n, position, regional_count, regional_total, global_count, global_total = row

            # Calculate significance
            sig = analyzer.calculate_significance(
                regional_count, regional_total,
                global_count, global_total
            )

            is_significant = sig['p_value'] < alpha

            # ONLY store significant results (p < 0.05)
            if is_significant:
                # Get total_before_filter from temp table
                cursor.execute("""
                    SELECT total_raw
                    FROM temp_regional_totals_raw
                    WHERE region_level = ? AND city IS ? AND county IS ? AND township IS ?
                      AND n = ? AND position = ?
                """, (level_db, city, county, township, n, position))

                raw_result = cursor.fetchone()
                total_before_filter = raw_result[0] if raw_result else regional_total

                cursor.execute("""
                    INSERT OR REPLACE INTO ngram_significance
                    (region_level, city, county, township, region_name, ngram, n, position, chi2, p_value, cramers_v, is_significant, total_before_filter)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    level_db, city, county, township, region_name, ngram, n, position,
                    sig['chi2'], sig['p_value'], sig['cramers_v'], 1, total_before_filter
                ))
                significant_count += 1

        total_tested += total_rows
        total_significant += significant_count

        conn.commit()
        pct = significant_count / total_rows * 100 if total_rows else 0
        print(f"  [OK] Completed {level_en}: {significant_count}/{total_rows} significant ({pct:.1f}%)")

    analyzer.__exit__(None, None, None)
    conn.close()

    print(f"\n[OK] Significance testing complete")
    print(f"    Total tested: {total_tested:,}")
    total_pct = total_significant / total_tested * 100 if total_tested else 0
    print(f"    Total significant: {total_significant:,} ({total_pct:.1f}%)")
    print(f"    Filtered out: {total_tested - total_significant:,} non-significant n-grams")


def _min_threshold_sql(column: str, thresholds_by_n: dict[int, int], n_column: str = "n") -> tuple[str, list[int]]:
    """Build SQL for per-n support thresholds."""
    if not thresholds_by_n:
        return "1=1", []

    clauses = []
    params: list[int] = []
    for n_value, threshold in sorted(thresholds_by_n.items()):
        clauses.append(f"({n_column} = ? AND {column} >= ?)")
        params.extend([n_value, threshold])
    return "(" + " OR ".join(clauses) + ")", params


def step6_cleanup_insignificant_data(
    db_path: str,
    min_regional_count_by_n: dict[int, int] | None = None,
    min_global_count_by_n: dict[int, int] | None = None,
):
    """Step 6: Clean up non-significant n-grams from tendency and frequency tables.

    This step removes non-significant n-grams from:
    - ngram_significance
    - ngram_tendency
    - regional_ngram_frequency

    Only n-grams that exist in ngram_significance (p < 0.05) and satisfy
    configured support thresholds are retained.
    """
    min_regional_count_by_n = min_regional_count_by_n or {}
    min_global_count_by_n = min_global_count_by_n or {}

    print("\n" + "="*60)
    print("Step 6: Cleaning Up Non-Significant N-grams")
    print("="*60)

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    # Count before cleanup
    cursor.execute("SELECT COUNT(*) FROM ngram_tendency")
    tendency_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regional_ngram_frequency")
    frequency_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ngram_significance")
    significance_before = cursor.fetchone()[0]

    print(f"\nBefore cleanup:")
    print(f"  ngram_significance: {significance_before:,} rows")
    print(f"  ngram_tendency: {tendency_before:,} rows")
    print(f"  regional_ngram_frequency: {frequency_before:,} rows")

    if min_regional_count_by_n or min_global_count_by_n:
        print("\nDeleting low-support n-grams from ngram_significance...")
        regional_sql, regional_params = _min_threshold_sql(
            "nt.regional_count", min_regional_count_by_n, "nt.n"
        )
        global_sql, global_params = _min_threshold_sql(
            "nt.global_count", min_global_count_by_n, "nt.n"
        )
        support_params = regional_params + global_params
        cursor.execute(f"""
            DELETE FROM ngram_significance
            WHERE NOT EXISTS (
                SELECT 1 FROM ngram_tendency nt
                WHERE nt.region_level = ngram_significance.region_level
                AND nt.city IS ngram_significance.city
                AND nt.county IS ngram_significance.county
                AND nt.township IS ngram_significance.township
                AND nt.ngram = ngram_significance.ngram
                AND nt.n = ngram_significance.n
                AND nt.position = ngram_significance.position
                AND {regional_sql}
                AND {global_sql}
            )
        """, support_params)
        print(f"  Deleted {cursor.rowcount:,} low-support significance rows")

    # Delete from ngram_tendency
    print("\nDeleting non-significant n-grams from ngram_tendency...")

    # Process each level separately to handle NULL values correctly
    tendency_deleted = 0

    # City level: only match city
    cursor.execute(f"""
        DELETE FROM ngram_tendency
        WHERE region_level = {REGION_LEVELS[0]}
        AND NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = ngram_tendency.ngram
            AND ngram_significance.region_level = ngram_tendency.region_level
            AND ngram_significance.city = ngram_tendency.city
            AND ngram_significance.n = ngram_tendency.n
            AND ngram_significance.position = ngram_tendency.position
        )
    """)
    tendency_deleted += cursor.rowcount

    # County level: match city and county
    cursor.execute("""
        DELETE FROM ngram_tendency
        WHERE region_level = 'county'
        AND NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = ngram_tendency.ngram
            AND ngram_significance.region_level = ngram_tendency.region_level
            AND ngram_significance.city = ngram_tendency.city
            AND ngram_significance.county = ngram_tendency.county
            AND ngram_significance.n = ngram_tendency.n
            AND ngram_significance.position = ngram_tendency.position
        )
    """)
    tendency_deleted += cursor.rowcount

    # Township level: match city, county and township
    cursor.execute(f"""
        DELETE FROM ngram_tendency
        WHERE region_level = {REGION_LEVELS[2]}
        AND NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = ngram_tendency.ngram
            AND ngram_significance.region_level = ngram_tendency.region_level
            AND ngram_significance.city = ngram_tendency.city
            AND ngram_significance.county = ngram_tendency.county
            AND ngram_significance.township = ngram_tendency.township
            AND ngram_significance.n = ngram_tendency.n
            AND ngram_significance.position = ngram_tendency.position
        )
    """)
    tendency_deleted += cursor.rowcount

    print(f"  Deleted {tendency_deleted:,} rows")

    # Delete from regional_ngram_frequency
    print("\nDeleting non-significant n-grams from regional_ngram_frequency...")

    # Process each level separately to handle NULL values correctly
    frequency_deleted = 0

    # City level: only match city
    cursor.execute("""
        DELETE FROM regional_ngram_frequency
        WHERE region_level = 'city'
        AND NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = regional_ngram_frequency.ngram
            AND ngram_significance.region_level = regional_ngram_frequency.region_level
            AND ngram_significance.city = regional_ngram_frequency.city
            AND ngram_significance.n = regional_ngram_frequency.n
            AND ngram_significance.position = regional_ngram_frequency.position
        )
    """)
    frequency_deleted += cursor.rowcount

    # County level: match city and county
    cursor.execute(f"""
        DELETE FROM regional_ngram_frequency
        WHERE region_level = {REGION_LEVELS[1]}
        AND NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = regional_ngram_frequency.ngram
            AND ngram_significance.region_level = regional_ngram_frequency.region_level
            AND ngram_significance.city = regional_ngram_frequency.city
            AND ngram_significance.county = regional_ngram_frequency.county
            AND ngram_significance.n = regional_ngram_frequency.n
            AND ngram_significance.position = regional_ngram_frequency.position
        )
    """)
    frequency_deleted += cursor.rowcount

    # Township level: match city, county and township
    cursor.execute("""
        DELETE FROM regional_ngram_frequency
        WHERE region_level = 'township'
        AND NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = regional_ngram_frequency.ngram
            AND ngram_significance.region_level = regional_ngram_frequency.region_level
            AND ngram_significance.city = regional_ngram_frequency.city
            AND ngram_significance.county = regional_ngram_frequency.county
            AND ngram_significance.township = regional_ngram_frequency.township
            AND ngram_significance.n = regional_ngram_frequency.n
            AND ngram_significance.position = regional_ngram_frequency.position
        )
    """)
    frequency_deleted += cursor.rowcount

    print(f"  Deleted {frequency_deleted:,} rows")

    conn.commit()

    # Count after cleanup
    cursor.execute("SELECT COUNT(*) FROM ngram_tendency")
    tendency_after = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regional_ngram_frequency")
    frequency_after = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ngram_significance")
    significance_after = cursor.fetchone()[0]

    print(f"\nAfter cleanup:")
    significance_retained = significance_after / significance_before * 100 if significance_before else 0
    tendency_retained = tendency_after / tendency_before * 100 if tendency_before else 0
    frequency_retained = frequency_after / frequency_before * 100 if frequency_before else 0
    print(f"  ngram_significance: {significance_after:,} rows (retained {significance_retained:.1f}%)")
    print(f"  ngram_tendency: {tendency_after:,} rows (retained {tendency_retained:.1f}%)")
    print(f"  regional_ngram_frequency: {frequency_after:,} rows (retained {frequency_retained:.1f}%)")

    print(f"\nTotal space saved: {tendency_deleted + frequency_deleted:,} rows deleted")

    conn.close()
    print("\n[OK] Cleanup complete - only significant n-grams retained")


def step7_detect_patterns(
    db_path: str,
    n_values: list[int] | None = None,
    min_freq_by_n: dict[int, int] | None = None,
):
    """Step 7: Detect structural patterns."""
    n_values = n_values or [2, 3, 4]
    min_freq_by_n = min_freq_by_n or {2: 100, 3: 50, 4: 30}

    print("\n" + "="*60)
    print("Step 7: Detecting Structural Patterns")
    print("="*60)

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    detector = StructuralPatternDetector(db_path)

    from collections import Counter

    for n in n_values:
        cursor.execute("""
            SELECT ngram, frequency
            FROM ngram_frequency
            WHERE n = ? AND position = 'all'
            ORDER BY frequency DESC
        """, (n,))
        ngrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})

        print(f"\nDetecting {n}-gram templates...")
        templates = detector.detect_templates(ngrams, min_freq=min_freq_by_n.get(n, 1))

        for template in templates:
            cursor.execute("""
                INSERT OR REPLACE INTO structural_patterns
                (pattern, pattern_type, n, position, frequency, example, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                template['pattern'],
                template['type'],
                n,
                'all',
                template['frequency'],
                template['example'],
                f"{template['type']} pattern"
            ))

        print(f"  [OK] Found {len(templates)} {n}-gram templates")

    conn.commit()
    conn.close()
    print("\n[OK] Pattern detection complete")


def step8_create_optimization_indexes(db_path: str, schema: VillageTableSchema | None = None):
    """Step 8: Create optimization indexes and regional centroids table.f"""
    print("\n" + "="*60)
    print("Step 8: Creating Optimization Indexes")
    print("="*60)

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()
    S = schema or get_schema("guangdong")

    # Part 1: Create indexes on village preprocessing table
    print("\n[1/3] Creating indexes on village preprocessing table...")
    village_indexes = [
        ('idx_village_township', S.preprocessed_table, S.township_col),
        ('idx_village_county', S.preprocessed_table, S.county_col),
        ('idx_village_city', S.preprocessed_table, S.city_col)
    ]

    for idx_name, table, column in village_indexes:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})')
            print(f"  [OK] {idx_name}")
        except Exception as e:
            print(f"  [SKIP] {idx_name}: {e}")

    # Part 2: Create regional centroids table
    print("\n[2/3] Creating regional centroids table...")

    required_centroid_cols = {
        'region_level', REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2], 'region_name',
        'centroid_lon', 'centroid_lat', 'village_count'
    }
    cursor.execute('PRAGMA table_info(regional_centroids)')
    existing_centroid_cols = {row[1] for row in cursor.fetchall()}
    if existing_centroid_cols and not required_centroid_cols.issubset(existing_centroid_cols):
        cursor.execute('DROP TABLE regional_centroids')
        print("  [OK] Rebuilt legacy regional_centroids schema")

    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS regional_centroids (
        region_region_level TEXT NOT NULL,
        city TEXT,
        county TEXT,
        township TEXT,
        region_name TEXT NOT NULL,
        centroid_lon REAL NOT NULL,
        centroid_lat REAL NOT NULL,
        village_count INTEGER NOT NULL
    )
    ''')
    print("  [OK] Table created")

    # Create index
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_regional_centroids_lookup
    ON regional_centroids(region_level, region_name)
    ''')
    print("  [OK] Index created")

    # Populate data
    print("  Populating data...")
    cursor.execute('DELETE FROM regional_centroids')
    cursor.execute(f'''
    INSERT OR REPLACE INTO regional_centroids (region_level, city, county, township, region_name, centroid_lon, centroid_lat, village_count)
    SELECT
        {REGION_LEVELS[2]} as region_level,
        {S.city_col} as city,
        {S.county_col} as county,
        {S.township_col} as township,
        {S.township_col} as region_name,
        AVG(CAST({S.longitude_col} AS REAL)) as centroid_lon,
        AVG(CAST({S.latitude_col} AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM {S.preprocessed_table}
    WHERE {S.township_col} IS NOT NULL AND {S.longitude_col} IS NOT NULL AND {S.latitude_col} IS NOT NULL
    GROUP BY {S.city_col}, {S.county_col}, {S.township_col}

    UNION ALL

    SELECT
        {REGION_LEVELS[1]} as region_level,
        {S.city_col} as city,
        {S.county_col} as county,
        NULL as township,
        {S.county_col} as region_name,
        AVG(CAST({S.longitude_col} AS REAL)) as centroid_lon,
        AVG(CAST({S.latitude_col} AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM {S.preprocessed_table}
    WHERE {S.county_col} IS NOT NULL AND {S.longitude_col} IS NOT NULL AND {S.latitude_col} IS NOT NULL
    GROUP BY {S.city_col}, {S.county_col}

    UNION ALL

    SELECT
        {REGION_LEVELS[0]} as region_level,
        {S.city_col} as city,
        NULL as county,
        NULL as township,
        {S.city_col} as region_name,
        AVG(CAST({S.longitude_col} AS REAL)) as centroid_lon,
        AVG(CAST({S.latitude_col} AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM {S.preprocessed_table}
    WHERE {S.city_col} IS NOT NULL AND {S.longitude_col} IS NOT NULL AND {S.latitude_col} IS NOT NULL
    GROUP BY {S.city_col}
    ''')

    # Verify data
    cursor.execute('SELECT region_level, COUNT(*) FROM regional_centroids GROUP BY region_level')
    results = cursor.fetchall()
    total = sum(count for _, count in results)
    print(f"  [OK] {total} regions populated")
    for level, count in results:
        print(f"    - {level}: {count}")

    # Part 3: Create query-shaped n-gram indexes.
    # PRIMARY KEY already covers: (region_level, city, county, township, ngram, n, position).
    # Keep this set intentionally small for space-constrained deployments.
    print("\n[3/3] Creating query-shaped n-gram indexes...")
    ngram_indexes = [
        ('idx_ngram_freq_n_position_frequency', 'ngram_frequency', 'n, position, frequency DESC'),
        ('idx_regional_ngram_level_n_region_freq', 'regional_ngram_frequency', 'region_level, n, region_name, frequency DESC'),
        ('idx_regional_ngram_level', 'regional_ngram_frequency', 'region_level'),
        ('idx_regional_ngram_region', 'regional_ngram_frequency', 'region_name'),
        ('idx_ngram_tendency_level_lift', 'ngram_tendency', 'region_level, lift DESC'),
        ('idx_ngram_tendency_level_region_lift', 'ngram_tendency', 'region_level, region_name, lift DESC'),
        ('idx_ngram_sig_level', 'ngram_significance', 'region_level'),
    ]

    for idx_name, table, columns in ngram_indexes:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})')
            print(f"  [OK] {idx_name}")
        except Exception as e:
            print(f"  [SKIP] {idx_name}: {e}")

    conn.commit()
    conn.close()

    print("\n[OK] Query-shaped n-gram indexes created (7 indexes)")
    print("Note: Regional n-gram index uses region display key to limit index size")


def step9_populate_village_ngrams(db_path: str, schema: VillageTableSchema | None = None):
    """Step 9: Populate village-level n-gram data for API endpoints.

    API endpoints that consume this table:
    - GET /api/villages/village/ngrams/{village_id}
    - GET /api/villages/village/complete/{village_id}
    """
    print("\n" + "=" * 60)
    print("Step 9: Populating village_ngrams Table")
    print("=" * 60)

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()
    S = schema or get_schema("guangdong")

    cursor.execute(f"""
        SELECT COUNT(*) FROM {S.preprocessed_table} WHERE {S.char_count_col} > 0
    """)
    total_villages = cursor.fetchone()[0]
    print(f"\nProcessing {total_villages:,} villages...")

    cursor.execute(f"""
        SELECT {S.village_id_col}, {S.committee_col_preprocessed}, {S.village_name_col_prefix_removed}
        FROM {S.preprocessed_table}
        WHERE {S.char_count_col} > 0
    """)
    villages = cursor.fetchall()
    print(f"Loaded {len(villages):,} villages from database")

    batch = []
    processed = 0
    insert_cursor = conn.cursor()

    for row in villages:
        village_id, village_committee, village_name = row

        if not village_name or not village_committee or not village_id:
            continue

        # Extract bigrams
        bigrams_pos = NgramExtractor.extract_positional_ngrams(village_name, n=2)
        bigrams_all = bigrams_pos['all']
        prefix_bigram = bigrams_pos['prefix'][0] if bigrams_pos['prefix'] else None
        suffix_bigram = bigrams_pos['suffix'][0] if bigrams_pos['suffix'] else None

        # Extract trigrams
        trigrams_pos = NgramExtractor.extract_positional_ngrams(village_name, n=3)
        trigrams_all = trigrams_pos['all']
        prefix_trigram = trigrams_pos['prefix'][0] if trigrams_pos['prefix'] else None
        suffix_trigram = trigrams_pos['suffix'][0] if trigrams_pos['suffix'] else None

        bigrams_json = json.dumps(bigrams_all, ensure_ascii=False) if bigrams_all else None
        trigrams_json = json.dumps(trigrams_all, ensure_ascii=False) if trigrams_all else None

        batch.append((
            village_id,
            village_committee,
            village_name,
            2,
            bigrams_json,
            trigrams_json,
            prefix_bigram,
            suffix_bigram,
            prefix_trigram,
            suffix_trigram
        ))

        processed += 1

        if len(batch) >= 1000:
            insert_cursor.executemany("""
                INSERT OR REPLACE INTO village_ngrams
                (village_id, committee, village_name, n, bigrams, trigrams, prefix_bigram, suffix_bigram, prefix_trigram, suffix_trigram)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            batch = []
            print(f"  Progress: {processed:,}/{total_villages:,} ({100*processed/total_villages:.1f}%)")

    # Insert remaining
    if batch:
        insert_cursor.executemany("""
            INSERT OR REPLACE INTO village_ngrams
            (village_id, committee, village_name, n, bigrams, trigrams, prefix_bigram, suffix_bigram, prefix_trigram, suffix_trigram)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM village_ngrams")
    count = cursor.fetchone()[0]
    print(f"\n[OK] Populated village_ngrams table with {count:,} records")
    conn.close()


def main(argv=None):
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Phase 12: N-gram Structure Analysis")
    parser.add_argument("--db-path", default="data/villages.db", help="Path to database")
    parser.add_argument("--schema", default="guangdong", choices=["guangdong", "national"], help="Village table schema")
    parser.add_argument("--run-id", default=None, help="Run ID for active_run_ids metadata")
    parser.add_argument("--n-values", default="2,3", help="Comma-separated n values for regional analysis")
    parser.add_argument("--regional-levels", default=REGION_LEVELS[2], help="Comma-separated regional levels")
    parser.add_argument("--positions", default="all,prefix,suffix,middle", help="Comma-separated positions")
    parser.add_argument("--min-regional-count-by-n", default="", help="Per-n thresholds, e.g. 2:3,3:2")
    parser.add_argument("--min-global-count-by-n", default="", help="Per-n thresholds, e.g. 2:10,3:5")
    parser.add_argument(
        "--skip-village-ngrams",
        action="store_true",
        help="Skip village_ngrams generation for compact profiles",
    )
    args = parser.parse_args(argv)

    db_path = args.db_path
    schema = get_schema(args.schema)
    n_values = _parse_int_csv(args.n_values)
    regional_levels = _parse_str_csv(args.regional_levels)
    positions = _parse_str_csv(args.positions)
    min_regional_count_by_n = _parse_thresholds(args.min_regional_count_by_n)
    min_global_count_by_n = _parse_thresholds(args.min_global_count_by_n)

    print("\n" + "="*60)
    print("Phase 12: N-gram Structure Analysis")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"N values: {n_values}")
    print(f"Regional levels: {regional_levels}")
    print(f"Positions: {positions}")
    if min_regional_count_by_n:
        print(f"Min regional count by n: {min_regional_count_by_n}")
    if min_global_count_by_n:
        print(f"Min global count by n: {min_global_count_by_n}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    # Generate run_id for this analysis
    run_id = args.run_id or f"ngram_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Run ID: {run_id}")

    try:
        exclude_tables = {"village_ngrams"} if args.skip_village_ngrams else set()
        step1_create_tables(db_path, exclude_tables=exclude_tables)
        step2_extract_global_ngrams(db_path, n_values=n_values, positions=positions, schema=schema)
        step3_extract_regional_ngrams(
            db_path,
            n_values=n_values,
            regional_levels=regional_levels,
            positions=positions,
            schema=schema,
        )
        step3_5_calculate_regional_totals_raw(db_path)  # NEW: Calculate raw totals
        step4_calculate_tendency(db_path, regional_levels=regional_levels)
        step5_calculate_significance(db_path, regional_levels=regional_levels)
        step6_cleanup_insignificant_data(
            db_path,
            min_regional_count_by_n=min_regional_count_by_n,
            min_global_count_by_n=min_global_count_by_n,
        )  # NEW: Clean up non-significant data
        step7_detect_patterns(db_path, n_values=n_values)
        step8_create_optimization_indexes(db_path, schema=schema)  # NEW: Create optimization indexes
        if args.skip_village_ngrams:
            print("\n[SKIP] village_ngrams generation disabled by --skip-village-ngrams")
        else:
            step9_populate_village_ngrams(db_path, schema=schema)  # NEW: Per-village n-grams for API

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*60)
        print("Phase 12 Complete!")
        print("="*60)
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print("\nAll n-gram analysis results stored in database.")
        print("NOTE: Only statistically significant n-grams (p < 0.05) are retained.")

        # Auto-update active_run_ids (NEW: 2026-02-25)
        print("\n" + "="*60)
        print("Updating active_run_ids...")
        print("="*60)

        # Count significant n-grams for notes
        conn = sqlite3.connect(db_path, timeout=60.0)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ngram_significance")
        sig_count = cursor.fetchone()[0]
        conn.close()

        try:
            from utils.update_run_id import update_active_run_id

            update_active_run_id(
                analysis_type="ngrams",
                run_id=run_id,
                script_name="phase12_ngram_analysis",
                notes=f"N-gram analysis complete. {sig_count:,} significant n-grams (p < 0.05) stored.",
                db_path=db_path
            )
        except ModuleNotFoundError as e:
            print(f"[WARN] active_run_ids update skipped: missing optional dependency {e.name}")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
