"""
N-gram analysis pipeline for village names.

This pipeline:
1. Creates ngram analysis tables
2. Extracts global n-gram frequencies (bigram, trigram, etc.)
3. Extracts regional n-gram frequencies by hierarchy level
4. Captures raw regional totals (pre-filtering) for significance testing
5. Calculates tendency metrics (lift, log-odds, z-score)
6. Calculates statistical significance (chi-square, p-value)
7. Cleans up non-significant / low-support n-grams
8. Detects structural patterns (templates like "X村", "大XX")
9. Creates optimisation indexes and regional centroids
10. Populates per-village n-gram features
"""

import logging
import sqlite3
import time
from collections import Counter
from typing import Any

from src.schema import REGION_LEVELS, DEFAULT_SCHEMA, VillageTableSchema
from src.ngram_analysis import NgramExtractor, NgramAnalyzer, StructuralPatternDetector
from src.ngram_schema import create_ngram_tables

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_POSITIONS = ['prefix', 'suffix', 'middle']

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
    """Run the complete n-gram analysis pipeline.

    Args:
        db_path: Path to SQLite database.
        schema_name: Village table schema name ('guangdong' or 'national').
        n_values: N-gram sizes to extract (default: (2, 3)).
        region_levels: Region levels to analyse (default: REGION_LEVELS[:3]).
        positions: N-gram positions to track (prefix/suffix/middle).
        min_global_freq: Minimum global frequency threshold.
        min_regional_freq: Per-n minimum regional frequency {n: threshold}.
        min_tendency_support: Per-n minimum support for tendency calculation.
        exclude_tables: Tables to skip creation of.
        skip_village_ngrams: Skip per-village n-gram population.
        batch_size: Batch size for database inserts.
        output_dir: Optional CSV export directory.
    """
    if region_levels is None:
        region_levels = REGION_LEVELS[:3]
    if min_regional_freq is None:
        min_regional_freq = {2: 3, 3: 2}
    if min_tendency_support is None:
        min_tendency_support = {2: 5, 3: 3}
    if exclude_tables is None:
        exclude_tables = set()

    logger.info("=" * 60)
    logger.info("N-gram Analysis Pipeline")
    logger.info(f"  n_values: {n_values}")
    logger.info(f"  region_levels: {region_levels}")
    logger.info(f"  positions: {positions}")
    logger.info("=" * 60)

    start_time = time.time()
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Create tables
        logger.info("Step 1: Creating n-gram tables...")
        create_ngram_tables(db_path, exclude_tables=exclude_tables)
        logger.info("  Tables created")

        # Step 2: Global n-gram frequencies
        logger.info("Step 2: Extracting global n-grams...")
        _extract_global_ngrams(conn, n_values, min_global_freq, batch_size)

        # Step 3: Regional n-gram frequencies
        logger.info("Step 3: Extracting regional n-grams...")
        _extract_regional_ngrams(conn, n_values, region_levels, positions,
                                 min_regional_freq, batch_size)

        # Step 3.5: Raw regional totals
        logger.info("Step 3.5: Capturing raw regional totals...")
        _capture_regional_totals_raw(conn)

        # Step 4: Tendency
        logger.info("Step 4: Calculating tendency...")
        _calculate_tendency(conn, n_values, region_levels, positions,
                           min_tendency_support, batch_size)

        # Step 5: Significance
        logger.info("Step 5: Calculating significance...")
        _calculate_significance(conn, region_levels, batch_size)

        # Step 6: Cleanup
        logger.info("Step 6: Cleaning up non-significant data...")
        _cleanup_insignificant(conn, n_values, min_regional_freq)

        # Step 7: Patterns
        logger.info("Step 7: Detecting structural patterns...")
        _detect_patterns(conn, n_values, min_global_freq)

        # Step 8: Indexes and centroids
        logger.info("Step 8: Creating indexes and centroids...")
        _create_indexes_and_centroids(conn, schema_name)

        # Step 9: Village n-grams
        if not skip_village_ngrams:
            logger.info("Step 9: Populating village n-grams...")
            _populate_village_ngrams(conn, n_values, batch_size)

        elapsed = time.time() - start_time
        logger.info(f"N-gram pipeline completed in {elapsed:.2f}s")

        return {
            'n_values': list(n_values),
            'region_levels': region_levels,
            'runtime_seconds': round(elapsed, 2),
        }

    except Exception:
        logger.error("Error in n-gram pipeline", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# step implementations
# ---------------------------------------------------------------------------


def _extract_global_ngrams(conn, n_values, min_freq, batch_size):
    extractor = NgramExtractor(conn)
    for n in n_values:
        logger.info(f"  Extracting {n}-grams...")
        all_ngrams = extractor.extract_all_ngrams(n)
        _insert_global_ngrams(conn, n, all_ngrams, min_freq, batch_size)
    extractor.close()


def _insert_global_ngrams(conn, n, all_ngrams, min_freq, batch_size):
    cursor = conn.cursor()
    rows = []
    for pos in _POSITIONS:
        for ngram, count in all_ngrams.get(pos, {}).items():
            if count >= min_freq:
                rows.append((n, pos, ngram, count))
    if rows:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            cursor.executemany(
                "INSERT OR REPLACE INTO ngram_frequency (n, position, ngram, frequency) VALUES (?, ?, ?, ?)",
                batch,
            )
    conn.commit()
    logger.info(f"    Inserted {len(rows):,} rows")


def _extract_regional_ngrams(conn, n_values, region_levels, positions, thresholds, batch_size):
    extractor = NgramExtractor(conn)
    pos_set = set(positions)
    for level in region_levels:
        for n in n_values:
            logger.info(f"  Extracting {n}-grams for {level}...")
            regional = extractor.extract_regional_ngrams(n, level)
            _insert_regional_ngrams(conn, n, level, regional, pos_set, thresholds.get(n, 0), batch_size)
    extractor.close()


def _insert_regional_ngrams(conn, n, level, regional, positions, min_freq, batch_size):
    cursor = conn.cursor()
    rows = []
    level_cols = [REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2]]
    for key, pos_data in regional.items():
        city_val = key[0] if len(key) > 0 else None
        county_val = key[1] if len(key) > 1 else None
        township_val = key[2] if len(key) > 2 else None
        region_name = {REGION_LEVELS[0]: city_val, REGION_LEVELS[1]: county_val, REGION_LEVELS[2]: township_val}[level]
        for pos in _POSITIONS:
            if pos not in positions:
                continue
            for ngram, count in pos_data.get(pos, {}).items():
                if count >= min_freq:
                    rows.append((n, level, city_val, county_val, township_val, region_name, pos, ngram, count))
    if rows:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            cursor.executemany(
                "INSERT OR REPLACE INTO regional_ngram_frequency (n, region_level, city, county, township, region_name, position, ngram, frequency) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
    conn.commit()
    logger.info(f"    {level}: {len(rows):,} rows")


def _capture_regional_totals_raw(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS regional_totals_raw")
    cursor.execute("""
        CREATE TABLE regional_totals_raw AS
        SELECT region_level, city, county, township, region_name, position, n,
               SUM(frequency) as total_frequency,
               COUNT(DISTINCT ngram) as distinct_ngrams
        FROM regional_ngram_frequency
        GROUP BY region_level, city, county, township, region_name, position, n
    """)
    conn.commit()
    logger.info("  Raw totals captured")


def _calculate_tendency(conn, n_values, region_levels, positions, thresholds, batch_size):
    cursor = conn.cursor()
    analyzer = NgramAnalyzer(conn)
    # Read global totals
    global_totals = {}
    for n in n_values:
        for pos in _POSITIONS:
            cursor.execute(
                "SELECT SUM(frequency) FROM ngram_frequency WHERE n = ? AND position = ?", (n, pos)
            )
            row = cursor.fetchone()
            global_totals[(n, pos)] = row[0] or 0

    logger.info(f"  Global totals: {global_totals}")

    # Query regional data joined with global
    for level in region_levels:
        for n in n_values:
            if n not in thresholds:
                continue
            for pos in _POSITIONS:
                if pos not in positions:
                    continue
                cursor.execute("""
                    SELECT r.ngram, r.frequency as regional_count,
                           r.region_name, r.city, r.county, r.township,
                           COALESCE(rt.total_frequency, r.frequency) as regional_total,
                           g.frequency as global_count
                    FROM regional_ngram_frequency r
                    JOIN ngram_frequency g ON g.n = r.n AND g.position = r.position AND g.ngram = r.ngram
                    LEFT JOIN regional_totals_raw rt
                        ON rt.region_level = r.region_level AND rt.n = r.n AND rt.position = r.position
                        AND COALESCE(rt.city, '') = COALESCE(r.city, '')
                        AND COALESCE(rt.county, '') = COALESCE(r.county, '')
                        AND COALESCE(rt.township, '') = COALESCE(r.township, '')
                    WHERE r.n = ? AND r.region_level = ? AND r.position = ?
                """, (n, level, pos))

                rows_to_insert = []
                global_total = global_totals.get((n, pos), 0)
                for row_data in cursor.fetchall():
                    ngram, reg_count, reg_name, city_v, county_v, township_v, reg_total, glob_count = row_data
                    if reg_count < thresholds[n]:
                        continue
                    tendency = analyzer.calculate_tendency(
                        reg_count, reg_total, glob_count or 0, global_total
                    )
                    rows_to_insert.append((
                        n, level, city_v, county_v, township_v, reg_name, pos,
                        ngram, reg_count, reg_total, glob_count or 0, global_total,
                        tendency['lift'], tendency['log_odds'], tendency['z_score'],
                    ))

                if rows_to_insert:
                    for i in range(0, len(rows_to_insert), batch_size):
                        batch = rows_to_insert[i:i + batch_size]
                        cursor.executemany("""
                            INSERT OR REPLACE INTO ngram_tendency
                            (n, region_level, city, county, township, region_name, position,
                             ngram, regional_count, regional_total, global_count, global_total,
                             lift, log_odds, z_score)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, batch)
                    conn.commit()
                logger.info(f"    {level}/{n}-gram/{pos}: {len(rows_to_insert):,} rows")
    analyzer.close()


def _calculate_significance(conn, region_levels, batch_size):
    cursor = conn.cursor()
    analyzer = NgramAnalyzer(conn)
    for level in region_levels:
        cursor.execute("""
            SELECT n, position, ngram, regional_count, regional_total,
                   global_count, global_total, city, county, township, region_name
            FROM ngram_tendency
            WHERE region_level = ?
        """, (level,))
        rows_to_insert = []
        for row_data in cursor.fetchall():
            n_v, pos, ngram, reg_cnt, reg_tot, glob_cnt, glob_tot, *hier = row_data
            sig = analyzer.calculate_significance(reg_cnt, reg_tot, glob_cnt, glob_tot)
            if sig['p_value'] < 0.05:
                city_v, county_v, township_v, reg_name = hier
                rows_to_insert.append((
                    n_v, level, city_v, county_v, township_v, reg_name, pos,
                    ngram, reg_cnt, reg_tot, glob_cnt, glob_tot,
                    sig['chi2'], sig['p_value'], sig['cramers_v'],
                ))
        if rows_to_insert:
            for i in range(0, len(rows_to_insert), batch_size):
                batch = rows_to_insert[i:i + batch_size]
                cursor.executemany("""
                    INSERT OR REPLACE INTO ngram_significance
                    (n, region_level, city, county, township, region_name, position,
                     ngram, regional_count, regional_total, global_count, global_total,
                     chi2, p_value, cramers_v)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
            conn.commit()
        logger.info(f"    {level}: {len(rows_to_insert):,} significant (p<0.05)")
    analyzer.close()


def _cleanup_insignificant(conn, n_values, thresholds):
    cursor = conn.cursor()
    # Remove from ngram_significance where regional_count < threshold
    for n, thresh in thresholds.items():
        if thresh:
            cursor.execute(
                "DELETE FROM ngram_significance WHERE n = ? AND regional_count < ?", (n, thresh)
            )
    # Remove orphaned from ngram_tendency (not in significance)
    cursor.execute("""
        DELETE FROM ngram_tendency
        WHERE NOT EXISTS (
            SELECT 1 FROM ngram_significance s
            WHERE s.ngram = ngram_tendency.ngram
              AND s.n = ngram_tendency.n
              AND s.position = ngram_tendency.position
              AND s.region_level = ngram_tendency.region_level
              AND COALESCE(s.city, '') = COALESCE(ngram_tendency.city, '')
              AND COALESCE(s.county, '') = COALESCE(ngram_tendency.county, '')
              AND COALESCE(s.township, '') = COALESCE(ngram_tendency.township, '')
        )
    """)
    # Remove orphaned from regional_ngram_frequency
    for n, thresh in thresholds.items():
        if thresh:
            cursor.execute(
                "DELETE FROM regional_ngram_frequency WHERE n = ? AND frequency < ?", (n, thresh)
            )
    conn.commit()
    logger.info("  Cleanup complete")


def _detect_patterns(conn, n_values, min_freq):
    detector = StructuralPatternDetector()
    cursor = conn.cursor()
    for n in n_values:
        if n < 2:
            continue
        cursor.execute(
            "SELECT ngram, frequency FROM ngram_frequency WHERE n = ?", (n,)
        )
        counts = Counter({row[0]: row[1] for row in cursor.fetchall() if row[1] >= min_freq})
        if not counts:
            continue
        patterns = detector.detect_templates(counts, min_freq)
        if patterns:
            for p in patterns:
                cursor.execute(
                    "INSERT OR REPLACE INTO structural_patterns (n, pattern, type, example, frequency) VALUES (?, ?, ?, ?, ?)",
                    (n, p['pattern'], p['type'], p['example'], p['frequency']),
                )
            conn.commit()
        logger.info(f"    {n}-gram: {len(patterns)} patterns detected")


def _create_indexes_and_centroids(conn, schema_name):
    from src.schema import get_schema
    S = get_schema(schema_name)
    cursor = conn.cursor()
    # Indexes on preprocessed table columns
    for col in [S.city_col, S.county_col, S.township_col]:
        try:
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS idx_preprocessed_{col} ON \"{S.preprocessed_table}\" (\"{col}\")"
            )
        except sqlite3.OperationalError:
            pass

    # Regional centroids
    cursor.execute("DROP TABLE IF EXISTS regional_centroids")
    cursor.execute("""
        CREATE TABLE regional_centroids (
            region_level TEXT, city TEXT, county TEXT, township TEXT,
            region_name TEXT, centroid_lon REAL, centroid_lat REAL, village_count INTEGER
        )
    """)

    centroids_sql = f"""
    INSERT OR REPLACE INTO regional_centroids (region_level, city, county, township, region_name, centroid_lon, centroid_lat, village_count)
    SELECT
        '{REGION_LEVELS[2]}' as region_level,
        "{S.city_col}" as city,
        "{S.county_col}" as county,
        "{S.township_col}" as township,
        "{S.township_col}" as region_name,
        AVG(CAST("{S.longitude_col}" AS REAL)) as centroid_lon,
        AVG(CAST("{S.latitude_col}" AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM "{S.preprocessed_table}"
    WHERE "{S.township_col}" IS NOT NULL
      AND "{S.longitude_col}" IS NOT NULL AND "{S.latitude_col}" IS NOT NULL
    GROUP BY "{S.city_col}", "{S.county_col}", "{S.township_col}"

    UNION ALL

    SELECT
        '{REGION_LEVELS[1]}' as region_level,
        "{S.city_col}" as city,
        "{S.county_col}" as county,
        NULL as township,
        "{S.county_col}" as region_name,
        AVG(CAST("{S.longitude_col}" AS REAL)) as centroid_lon,
        AVG(CAST("{S.latitude_col}" AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM "{S.preprocessed_table}"
    WHERE "{S.county_col}" IS NOT NULL
      AND "{S.longitude_col}" IS NOT NULL AND "{S.latitude_col}" IS NOT NULL
    GROUP BY "{S.city_col}", "{S.county_col}"

    UNION ALL

    SELECT
        '{REGION_LEVELS[0]}' as region_level,
        "{S.city_col}" as city,
        NULL as county,
        NULL as township,
        "{S.city_col}" as region_name,
        AVG(CAST("{S.longitude_col}" AS REAL)) as centroid_lon,
        AVG(CAST("{S.latitude_col}" AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM "{S.preprocessed_table}"
    WHERE "{S.city_col}" IS NOT NULL
      AND "{S.longitude_col}" IS NOT NULL AND "{S.latitude_col}" IS NOT NULL
    GROUP BY "{S.city_col}"
    """
    cursor.execute(centroids_sql)
    conn.commit()
    logger.info("  Indexes and centroids created")


def _populate_village_ngrams(conn, n_values, batch_size):
    from src.schema import DEFAULT_SCHEMA as S
    extractor = NgramExtractor(conn)
    cursor = conn.cursor()

    all_villages = extractor._cursor.execute(
        f'SELECT "{S.committee_col_preprocessed}", "{S.village_name_col_prefix_removed}" FROM "{S.preprocessed_table}"'
    ).fetchall()

    rows = []
    for committee, vname in all_villages:
        if not vname:
            continue
        for n in n_values:
            pos_ngrams = extractor.extract_positional_ngrams(vname, n)
            for pos in _POSITIONS:
                for ng in pos_ngrams.get(pos, []):
                    rows.append((n, committee, vname, pos, ng))
        if len(rows) >= batch_size:
            cursor.executemany(
                "INSERT OR REPLACE INTO village_ngrams (n, committee, village_name, position, ngram) VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            rows = []

    if rows:
        cursor.executemany(
            "INSERT OR REPLACE INTO village_ngrams (n, committee, village_name, position, ngram) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()

    extractor.close()
    logger.info(f"  Village n-grams populated")
