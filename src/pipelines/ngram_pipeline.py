"""
N-gram analysis pipeline for village names.
"""

import json
import logging
import sqlite3
import time
from collections import Counter
from typing import Any

from src.schema import REGION_LEVELS, get_schema
from src.ngram_analysis import NgramExtractor, NgramAnalyzer, StructuralPatternDetector
from src.ngram_schema import create_ngram_tables

logger = logging.getLogger(__name__)

_POSITIONS = ['prefix', 'suffix', 'middle']

# Shorthand aliases — these ARE the ngram table column names which match REGION_LEVELS values.
_L0 = REGION_LEVELS[0]
_L1 = REGION_LEVELS[1]
_L2 = REGION_LEVELS[2]
_L3 = REGION_LEVELS[3]


def _filter_positions(position_data, positions):
    requested = set(positions)
    return {p: c for p, c in position_data.items() if p in requested}


def _min_threshold_sql(column, thresholds_by_n, n_column="n"):
    if not thresholds_by_n:
        return "1=1", []
    clauses = []
    params = []
    for n_val, threshold in sorted(thresholds_by_n.items()):
        clauses.append(f"({n_column} = ? AND {column} >= ?)")
        params.extend([n_val, threshold])
    return "(" + " OR ".join(clauses) + ")", params


# ---------------------------------------------------------------------------
# main pipeline
# ---------------------------------------------------------------------------


def run_ngram_pipeline(
    db_path: str,
    schema_name: str = 'guangdong',
    n_values: tuple[int, ...] = (2, 3),
    region_levels: list[str] | None = None,
    positions: tuple[str, ...] = ('prefix', 'suffix', 'middle'),
    min_global_freq: int = 10,
    min_regional_freq: dict[int, int] | None = None,
    min_tendency_support: dict[int, int] | None = None,
    exclude_tables: set[str] | None = None,
    skip_village_ngrams: bool = False,
    batch_size: int = 5000,
    output_dir: str | None = None,
) -> dict[str, Any]:
    if region_levels is None:
        region_levels = REGION_LEVELS[:3]
    if min_regional_freq is None:
        min_regional_freq = {2: 3, 3: 2}
    if min_tendency_support is None:
        min_tendency_support = {2: 5, 3: 3}
    if exclude_tables is None:
        exclude_tables = set()

    schema = get_schema(schema_name)
    n_values_list = list(n_values)
    positions_list = list(positions)

    logger.info("=" * 60)
    logger.info("N-gram Analysis Pipeline")
    logger.info(f"  n_values: {n_values}")
    logger.info(f"  region_levels: {region_levels}")
    logger.info(f"  positions: {positions}")
    logger.info("=" * 60)

    start_time = time.time()

    logger.info("Step 1: Creating n-gram tables...")
    create_ngram_tables(db_path, exclude_tables=exclude_tables)
    logger.info("  Tables created")

    logger.info("Step 2: Extracting global n-grams...")
    _step2_extract_global_ngrams(db_path, n_values_list, positions_list, schema)

    logger.info("Step 3: Extracting regional n-grams...")
    _step3_extract_regional_ngrams(db_path, n_values_list, region_levels, positions_list, schema)

    logger.info("Step 3.5: Capturing raw regional totals...")
    _step3_5_calculate_regional_totals_raw(db_path)

    logger.info("Step 4: Calculating tendency...")
    _step4_calculate_tendency(db_path, region_levels)

    logger.info("Step 5: Calculating significance...")
    _step5_calculate_significance(db_path, region_levels)

    logger.info("Step 6: Cleaning up non-significant data...")
    _step6_cleanup_insignificant_data(db_path, min_regional_freq, min_tendency_support)

    logger.info("Step 7: Detecting structural patterns...")
    _step7_detect_patterns(db_path, n_values_list)

    logger.info("Step 8: Creating indexes and centroids...")
    _step8_create_optimization_indexes(db_path, schema)

    if not skip_village_ngrams:
        logger.info("Step 9: Populating village n-grams...")
        _step9_populate_village_ngrams(db_path, schema)

    elapsed = time.time() - start_time
    logger.info(f"N-gram pipeline completed in {elapsed:.2f}s")

    return {
        'n_values': n_values_list,
        'region_levels': region_levels,
        'runtime_seconds': round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# step implementations
# ---------------------------------------------------------------------------


def _step2_extract_global_ngrams(db_path, n_values, positions, schema):
    positions_with_all = positions + ['all']
    with NgramExtractor(db_path, schema=schema) as extractor:
        ngram_data_by_n = {}
        for n in n_values:
            logger.info(f"  Extracting {n}-grams...")
            ngram_data_by_n[n] = _filter_positions(
                extractor.extract_all_ngrams(n=n),
                positions_with_all,
            )

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    for n, position_data in ngram_data_by_n.items():
        for position, counter in position_data.items():
            total = sum(counter.values())
            for ngram, freq in counter.items():
                percentage = (freq / total * 100) if total > 0 else 0
                cursor.execute(
                    "INSERT OR REPLACE INTO ngram_frequency (ngram, n, position, frequency, total_count, percentage) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (ngram, n, position, freq, total, percentage),
                )

    conn.commit()
    for n in n_values:
        cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_frequency WHERE n = ?", (n,))
        logger.info(f"    {n}-grams: {cursor.fetchone()[0]:,} unique")
    conn.close()


def _step3_extract_regional_ngrams(db_path, n_values, regional_levels, positions, schema):
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    with NgramExtractor(db_path, schema=schema) as extractor:
        for level_en in regional_levels:
            logger.info(f"  Extracting for {level_en}...")
            for n in n_values:
                ngram_data = extractor.extract_regional_ngrams(n=n, level=level_en)
                for hierarchical_key, position_data in ngram_data.items():
                    level_idx = REGION_LEVELS.index(level_en)
                    region_name = hierarchical_key[min(level_idx, len(hierarchical_key) - 1)]
                    for position, counter in _filter_positions(position_data, positions + ['all']).items():
                        total = sum(counter.values())
                        for ngram, freq in counter.items():
                            percentage = (freq / total * 100) if total > 0 else 0
                            cursor.execute(
                                f"INSERT OR REPLACE INTO regional_ngram_frequency "
                                f"(region_level, {_L0}, {_L1}, {_L2}, region_name, ngram, n, position, frequency, total_count, percentage) "
                                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (level_en, *hierarchical_key, region_name, ngram, n, position, freq, total, percentage),
                            )

        conn.commit()
        logger.info("    Completed")

    conn.close()


def _step3_5_calculate_regional_totals_raw(db_path):
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS temp_regional_totals_raw (
            region_level TEXT NOT NULL,
            {_L0} TEXT,
            {_L1} TEXT,
            {_L2} TEXT,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            total_raw INTEGER NOT NULL,
            PRIMARY KEY (region_level, {_L0}, {_L1}, {_L2}, n, position)
        )
    """)
    cursor.execute("DELETE FROM temp_regional_totals_raw")
    cursor.execute(f"""
        INSERT INTO temp_regional_totals_raw
        SELECT region_level, {_L0}, {_L1}, {_L2}, n, position, COUNT(*) as total_raw
        FROM regional_ngram_frequency
        GROUP BY region_level, {_L0}, {_L1}, {_L2}, n, position
    """)
    logger.info(f"  Raw totals: {cursor.rowcount:,} region-position combinations")

    conn.commit()
    conn.close()


def _step4_calculate_tendency(db_path, regional_levels):
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    for level_en in regional_levels:
        logger.info(f"  Processing level: {level_en}")
        cursor.execute(f"""
            SELECT
                r.region_level, r.{_L0}, r.{_L1}, r.{_L2}, r.region_name, r.ngram, r.n, r.position,
                r.frequency as regional_count,
                r.total_count as regional_total,
                COALESCE(t.total_raw, r.total_count) as regional_total_raw,
                g.frequency as global_count,
                g.total_count as global_total
            FROM regional_ngram_frequency r
            LEFT JOIN temp_regional_totals_raw t
                ON r.region_level = t.region_level
                AND r.{_L0} IS t.{_L0}
                AND r.{_L1} IS t.{_L1}
                AND r.{_L2} IS t.{_L2}
                AND r.n = t.n
                AND r.position = t.position
            LEFT JOIN ngram_frequency g
                ON r.ngram = g.ngram
                AND r.n = g.n
                AND r.position = g.position
            WHERE r.region_level = ?
        """, (level_en,))

        rows = cursor.fetchall()
        batch = []
        batch_size = 1000

        for idx, row in enumerate(rows, 1):
            if idx % 10000 == 0:
                logger.info(f"    Progress: {idx:,}/{len(rows):,}")

            (level_db, v0, v1, v2, region_name, ngram, n, position,
             regional_count, regional_total, regional_total_raw,
             global_count, global_total) = row

            if global_count is None or global_total is None:
                continue

            tendency = analyzer.calculate_tendency(
                regional_count, regional_total,
                global_count, global_total
            )

            batch.append((
                level_en, v0, v1, v2, region_name, ngram, n, position,
                tendency['lift'], tendency['log_odds'], tendency['z_score'],
                regional_count, regional_total, regional_total_raw, global_count, global_total
            ))

            if len(batch) >= batch_size:
                cursor.executemany(
                    f"INSERT OR REPLACE INTO ngram_tendency "
                    f"(region_level, {_L0}, {_L1}, {_L2}, region_name, ngram, n, position, lift, log_odds, z_score, "
                    f" regional_count, regional_total, regional_total_raw, global_count, global_total) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    batch,
                )
                conn.commit()
                batch = []

        if batch:
            cursor.executemany(
                f"INSERT OR REPLACE INTO ngram_tendency "
                f"(region_level, {_L0}, {_L1}, {_L2}, region_name, ngram, n, position, lift, log_odds, z_score, "
                f" regional_count, regional_total, regional_total_raw, global_count, global_total) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            conn.commit()

        logger.info(f"    {level_en}: done")

    analyzer.__exit__(None, None, None)
    conn.close()


def _step5_calculate_significance(db_path, regional_levels, alpha=0.05):
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    total_tested = 0
    total_significant = 0

    for level_en in regional_levels:
        logger.info(f"  Processing level: {level_en}")

        cursor.execute(f"""
            SELECT region_level, {_L0}, {_L1}, {_L2}, region_name, ngram, n, position,
                   regional_count, regional_total, global_count, global_total
            FROM ngram_tendency
            WHERE region_level = ?
        """, (level_en,))

        rows = cursor.fetchall()
        significant_count = 0

        for idx, row in enumerate(rows, 1):
            if idx % 1000 == 0:
                logger.info(f"    Progress: {idx}/{len(rows)} ({significant_count} significant)")

            (level_db, v0, v1, v2, region_name, ngram, n, position,
             regional_count, regional_total, global_count, global_total) = row

            sig = analyzer.calculate_significance(
                regional_count, regional_total,
                global_count, global_total
            )

            if sig['p_value'] < alpha:
                cursor.execute(f"""
                    SELECT total_raw
                    FROM temp_regional_totals_raw
                    WHERE region_level = ? AND {_L0} IS ? AND {_L1} IS ? AND {_L2} IS ?
                      AND n = ? AND position = ?
                """, (level_db, v0, v1, v2, n, position))
                raw_result = cursor.fetchone()
                total_before_filter = raw_result[0] if raw_result else regional_total

                cursor.execute(
                    f"INSERT OR REPLACE INTO ngram_significance "
                    f"(region_level, {_L0}, {_L1}, {_L2}, region_name, ngram, n, position, chi2, p_value, cramers_v, is_significant, total_before_filter) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (level_db, v0, v1, v2, region_name, ngram, n, position,
                     sig['chi2'], sig['p_value'], sig['cramers_v'], 1, total_before_filter),
                )
                significant_count += 1

        total_tested += len(rows)
        total_significant += significant_count
        conn.commit()
        pct = significant_count / len(rows) * 100 if len(rows) else 0
        logger.info(f"    {level_en}: {significant_count}/{len(rows)} significant ({pct:.1f}%)")

    analyzer.__exit__(None, None, None)
    conn.close()

    logger.info(f"  Total tested: {total_tested:,}")
    total_pct = total_significant / total_tested * 100 if total_tested else 0
    logger.info(f"  Total significant: {total_significant:,} ({total_pct:.1f}%)")


def _step6_cleanup_insignificant_data(db_path, min_regional_count_by_n=None, min_global_count_by_n=None):
    min_regional_count_by_n = min_regional_count_by_n or {}
    min_global_count_by_n = min_global_count_by_n or {}

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM ngram_tendency")
    tendency_before = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM regional_ngram_frequency")
    frequency_before = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ngram_significance")
    significance_before = cursor.fetchone()[0]

    logger.info(f"  Before: significance={significance_before:,}, tendency={tendency_before:,}, regional_freq={frequency_before:,}")

    if min_regional_count_by_n or min_global_count_by_n:
        regional_sql, regional_params = _min_threshold_sql(
            "nt.regional_count", min_regional_count_by_n, "nt.n"
        )
        global_sql, global_params = _min_threshold_sql(
            "nt.global_count", min_global_count_by_n, "nt.n"
        )
        cursor.execute(f"""
            DELETE FROM ngram_significance
            WHERE NOT EXISTS (
                SELECT 1 FROM ngram_tendency nt
                WHERE nt.region_level = ngram_significance.region_level
                AND nt.{_L0} IS ngram_significance.{_L0}
                AND nt.{_L1} IS ngram_significance.{_L1}
                AND nt.{_L2} IS ngram_significance.{_L2}
                AND nt.ngram = ngram_significance.ngram
                AND nt.n = ngram_significance.n
                AND nt.position = ngram_significance.position
                AND {regional_sql}
                AND {global_sql}
            )
        """, regional_params + global_params)
        logger.info(f"  Deleted {cursor.rowcount:,} low-support significance rows")

    # Delete from ngram_tendency — iterate over ALL region levels in the data
    tendency_deleted = 0
    cursor.execute("SELECT DISTINCT region_level FROM ngram_tendency")
    levels_in_data = [row[0] for row in cursor.fetchall()]
    for level in levels_in_data:
        idx = REGION_LEVELS.index(level)
        match_cols = [_L0, _L1, _L2][:min(idx, 2) + 1]
        conditions = " AND ".join(
            f"ngram_significance.{c} = ngram_tendency.{c}" for c in match_cols
        )
        cursor.execute(f"""
            DELETE FROM ngram_tendency
            WHERE region_level = ?
            AND NOT EXISTS (
                SELECT 1 FROM ngram_significance
                WHERE ngram_significance.ngram = ngram_tendency.ngram
                AND ngram_significance.region_level = ngram_tendency.region_level
                AND {conditions}
                AND ngram_significance.n = ngram_tendency.n
                AND ngram_significance.position = ngram_tendency.position
            )
        """, (level,))
        tendency_deleted += cursor.rowcount

    logger.info(f"  Deleted {tendency_deleted:,} tendency rows")

    # Delete from regional_ngram_frequency — same pattern
    frequency_deleted = 0
    cursor.execute("SELECT DISTINCT region_level FROM regional_ngram_frequency")
    levels_in_freq = [row[0] for row in cursor.fetchall()]
    for level in levels_in_freq:
        idx = REGION_LEVELS.index(level)
        match_cols = [_L0, _L1, _L2][:min(idx, 2) + 1]
        conditions = " AND ".join(
            f"ngram_significance.{c} = regional_ngram_frequency.{c}" for c in match_cols
        )
        cursor.execute(f"""
            DELETE FROM regional_ngram_frequency
            WHERE region_level = ?
            AND NOT EXISTS (
                SELECT 1 FROM ngram_significance
                WHERE ngram_significance.ngram = regional_ngram_frequency.ngram
                AND ngram_significance.region_level = regional_ngram_frequency.region_level
                AND {conditions}
                AND ngram_significance.n = regional_ngram_frequency.n
                AND ngram_significance.position = regional_ngram_frequency.position
            )
        """, (level,))
        frequency_deleted += cursor.rowcount

    logger.info(f"  Deleted {frequency_deleted:,} regional frequency rows")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM ngram_tendency")
    tendency_after = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM regional_ngram_frequency")
    frequency_after = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ngram_significance")
    significance_after = cursor.fetchone()[0]

    logger.info(f"  After: significance={significance_after:,}, tendency={tendency_after:,}, regional_freq={frequency_after:,}")
    logger.info(f"  Total space saved: {tendency_deleted + frequency_deleted:,} rows")

    conn.close()


def _step7_detect_patterns(db_path, n_values, min_freq_by_n=None):
    min_freq_by_n = min_freq_by_n or {2: 100, 3: 50, 4: 30}

    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    detector = StructuralPatternDetector(db_path)

    for n in n_values:
        cursor.execute(
            "SELECT ngram, frequency FROM ngram_frequency WHERE n = ? AND position = 'all' ORDER BY frequency DESC",
            (n,),
        )
        ngrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})

        templates = detector.detect_templates(ngrams, min_freq=min_freq_by_n.get(n, 1))

        for template in templates:
            cursor.execute(
                "INSERT OR REPLACE INTO structural_patterns (pattern, pattern_type, n, position, frequency, example, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (template['pattern'], template['type'], n, 'all',
                 template['frequency'], template['example'],
                 f"{template['type']} pattern"),
            )

        logger.info(f"    {n}-gram: {len(templates)} patterns detected")

    conn.commit()
    conn.close()


def _step8_create_optimization_indexes(db_path, schema):
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()
    S = schema

    for idx_name, col in [(f'idx_village_{REGION_LEVELS[2]}', S.township_col),
                           (f'idx_village_{REGION_LEVELS[1]}', S.county_col),
                           (f'idx_village_{REGION_LEVELS[0]}', S.city_col)]:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {S.preprocessed_table} ({col})')
        except Exception:
            pass

    # Regional centroids
    cursor.execute('PRAGMA table_info(regional_centroids)')
    existing_cols = {row[1] for row in cursor.fetchall()}
    required_cols = {'region_level', _L0, _L1, _L2, 'region_name',
                     'centroid_lon', 'centroid_lat', 'village_count'}
    if existing_cols and not required_cols.issubset(existing_cols):
        cursor.execute('DROP TABLE regional_centroids')

    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS regional_centroids (
        region_level TEXT NOT NULL,
        {_L0} TEXT,
        {_L1} TEXT,
        {_L2} TEXT,
        region_name TEXT NOT NULL,
        centroid_lon REAL NOT NULL,
        centroid_lat REAL NOT NULL,
        village_count INTEGER NOT NULL
    )
    ''')
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_regional_centroids_lookup
    ON regional_centroids(region_level, region_name)
    ''')

    cursor.execute('DELETE FROM regional_centroids')
    cursor.execute(f'''
    INSERT OR REPLACE INTO regional_centroids (region_level, {_L0}, {_L1}, {_L2}, region_name, centroid_lon, centroid_lat, village_count)
    SELECT
        '{_L2}' as region_level,
        {S.city_col} as {_L0},
        {S.county_col} as {_L1},
        {S.township_col} as {_L2},
        {S.township_col} as region_name,
        AVG(CAST({S.longitude_col} AS REAL)) as centroid_lon,
        AVG(CAST({S.latitude_col} AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM {S.preprocessed_table}
    WHERE {S.township_col} IS NOT NULL AND {S.longitude_col} IS NOT NULL AND {S.latitude_col} IS NOT NULL
    GROUP BY {S.city_col}, {S.county_col}, {S.township_col}

    UNION ALL

    SELECT
        '{_L1}' as region_level,
        {S.city_col} as {_L0},
        {S.county_col} as {_L1},
        NULL as {_L2},
        {S.county_col} as region_name,
        AVG(CAST({S.longitude_col} AS REAL)) as centroid_lon,
        AVG(CAST({S.latitude_col} AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM {S.preprocessed_table}
    WHERE {S.county_col} IS NOT NULL AND {S.longitude_col} IS NOT NULL AND {S.latitude_col} IS NOT NULL
    GROUP BY {S.city_col}, {S.county_col}

    UNION ALL

    SELECT
        '{_L0}' as region_level,
        {S.city_col} as {_L0},
        NULL as {_L1},
        NULL as {_L2},
        {S.city_col} as region_name,
        AVG(CAST({S.longitude_col} AS REAL)) as centroid_lon,
        AVG(CAST({S.latitude_col} AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM {S.preprocessed_table}
    WHERE {S.city_col} IS NOT NULL AND {S.longitude_col} IS NOT NULL AND {S.latitude_col} IS NOT NULL
    GROUP BY {S.city_col}
    ''')

    cursor.execute('SELECT region_level, COUNT(*) FROM regional_centroids GROUP BY region_level')
    for level, count in cursor.fetchall():
        logger.info(f"    {level}: {count} regions")

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
        except Exception:
            pass

    conn.commit()
    conn.close()
    logger.info("  Indexes and centroids created")


def _step9_populate_village_ngrams(db_path, schema):
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()
    S = schema

    cursor.execute(f"SELECT COUNT(*) FROM {S.preprocessed_table} WHERE {S.char_count_col} > 0")
    total_villages = cursor.fetchone()[0]
    logger.info(f"  Processing {total_villages:,} villages...")

    cursor.execute(f"""
        SELECT {S.village_id_col}, {S.committee_col_preprocessed}, {S.village_name_col_prefix_removed}
        FROM {S.preprocessed_table}
        WHERE {S.char_count_col} > 0
    """)
    villages = cursor.fetchall()

    batch = []
    processed = 0

    for village_id, village_committee, village_name in villages:
        if not village_name or not village_committee or not village_id:
            continue

        bigrams_pos = NgramExtractor.extract_positional_ngrams(village_name, n=2)
        bigrams_all = bigrams_pos['all']
        bigrams_json = json.dumps(bigrams_all, ensure_ascii=False) if bigrams_all else None
        prefix_bigram = bigrams_pos['prefix'][0] if bigrams_pos['prefix'] else None
        suffix_bigram = bigrams_pos['suffix'][0] if bigrams_pos['suffix'] else None

        trigrams_pos = NgramExtractor.extract_positional_ngrams(village_name, n=3)
        trigrams_all = trigrams_pos['all']
        trigrams_json = json.dumps(trigrams_all, ensure_ascii=False) if trigrams_all else None
        prefix_trigram = trigrams_pos['prefix'][0] if trigrams_pos['prefix'] else None
        suffix_trigram = trigrams_pos['suffix'][0] if trigrams_pos['suffix'] else None

        batch.append((
            village_id, village_committee, village_name, 2,
            bigrams_json, trigrams_json,
            prefix_bigram, suffix_bigram,
            prefix_trigram, suffix_trigram,
        ))

        processed += 1

        if len(batch) >= 1000:
            cursor.executemany(
                "INSERT OR REPLACE INTO village_ngrams "
                "(village_id, committee, village_name, n, bigrams, trigrams, prefix_bigram, suffix_bigram, prefix_trigram, suffix_trigram) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            conn.commit()
            batch = []
            logger.info(f"    Progress: {processed:,}/{total_villages:,} ({100*processed/total_villages:.1f}%)")

    if batch:
        cursor.executemany(
            "INSERT OR REPLACE INTO village_ngrams "
            "(village_id, committee, village_name, n, bigrams, trigrams, prefix_bigram, suffix_bigram, prefix_trigram, suffix_trigram) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batch,
        )
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM village_ngrams")
    count = cursor.fetchone()[0]
    logger.info(f"  Village n-grams populated: {count:,} records")
    conn.close()
