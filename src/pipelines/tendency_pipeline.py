"""
Regional tendency analysis pipeline with statistical significance testing.

This pipeline:
1. Creates analysis tables and indexes
2. Loads preprocessed village data
3. Computes character frequency (global + regional)
4. Computes regional tendency metrics (lift, z-score)
5. Computes statistical significance (p-values, chi-square, effect sizes)
6. Persists all results to database
"""

import logging
import sqlite3
import time
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from src.schema import REGION_LEVELS, get_schema
from src.data.db_loader import load_villages
from src.analysis.char_frequency import compute_char_frequency
from src.analysis.regional_analysis import (
    compute_regional_tendency,
    compute_tendency_significance,
)
from src.data.db_writer import (
    create_analysis_tables,
    create_indexes,
    create_tendency_significance_table,
    save_run_metadata,
    save_global_frequency,
    save_regional_frequency,
    save_regional_tendency,
    save_tendency_significance,
)

logger = logging.getLogger(__name__)


def run_tendency_pipeline(
    db_path: str,
    run_id: str,
    region_levels: list[str] | None = None,
    with_ci: bool = True,
    min_global_support: int = 20,
    min_regional_support: int = 5,
    normalization_method: str = 'percentage',
    schema_name: str = 'guangdong',
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Run tendency analysis with significance testing.

    Args:
        db_path: Path to SQLite database.
        run_id: Unique run identifier.
        region_levels: Region levels to analyse (default: REGION_LEVELS[:3]).
        with_ci: Compute confidence intervals.
        min_global_support: Minimum global village count for a character.
        min_regional_support: Minimum regional village count for a character.
        normalization_method: 'percentage' (lift) or 'zscore'.
        schema_name: Village table schema name.
        output_dir: Optional CSV export directory.
    """
    if region_levels is None:
        region_levels = REGION_LEVELS[:3]

    logger.info("=" * 60)
    logger.info("Starting tendency analysis with significance testing")
    logger.info(f"  Run ID: {run_id}")
    logger.info(f"  Region levels: {region_levels}")
    logger.info(f"  Normalization: {normalization_method}")
    logger.info("=" * 60)

    start_time = time.time()
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Create tables and indexes
        logger.info("Creating database tables...")
        create_analysis_tables(conn)
        create_indexes(conn)

        # Step 2: Load village data
        logger.info("Loading village data...")
        villages_chunks = load_villages(conn)
        villages_df = pd.concat(villages_chunks, ignore_index=True)
        logger.info(f"Loaded {len(villages_df):,} villages")

        # Step 3: Compute character frequency — counts unique villages per char,
        # deduplicating repeated characters within a single village name via set()
        logger.info("Computing character frequency...")
        freq_results = compute_char_frequency(
            villages_df,
            region_levels=region_levels,
            min_global_support=min_global_support,
            min_regional_support=min_regional_support,
        )
        logger.info(f"  Global: {len(freq_results['global']):,} unique characters")
        for lv in region_levels:
            if lv in freq_results['regional']:
                logger.info(f"  {lv}: {len(freq_results['regional'][lv]):,} char-region pairs")

        # Step 4: Per-level tendency + significance.
        # Tendency = lift (regional% / global%) or z-score of the proportion.
        # Significance = chi-square test, p-value, effect size for each char-region pair.
        tendency_results: dict[str, pd.DataFrame] = {}
        for level in region_levels:
            if level not in freq_results['regional']:
                continue

            logger.info(f"Computing tendency for {level}...")
            regional_df = freq_results['regional'][level]

            tendency_df = compute_regional_tendency(
                regional_df,
                min_global_support=min_global_support,
                min_regional_support=min_regional_support,
                compute_z=True,
                normalization_method=normalization_method,
            )
            logger.info(f"  {len(tendency_df):,} char-region pairs")

            logger.info(f"Computing significance for {level}...")
            tendency_df = compute_tendency_significance(tendency_df, compute_ci=with_ci)
            n_sig = int(tendency_df['is_significant'].sum())
            logger.info(f"  {n_sig:,} significant ({n_sig/max(len(tendency_df),1)*100:.1f}%)")
            tendency_results[level] = tendency_df

        # Step 5: Persist to database
        logger.info("Saving results to database...")
        metadata = {
            'created_at': time.time(),
            'total_villages': len(villages_df),
            'valid_villages': len(villages_df),
            'unique_chars': len(freq_results['global']),
            'config': {
                'region_levels': region_levels,
                'min_global_support': min_global_support,
                'min_regional_support': min_regional_support,
                'with_ci': with_ci,
                'normalization_method': normalization_method,
            },
            'status': 'completed',
        }
        save_run_metadata(conn, run_id, metadata)
        save_global_frequency(conn, run_id, freq_results['global'])

        for level in region_levels:
            if level not in freq_results['regional']:
                continue
            regional_df = freq_results['regional'][level]
            save_regional_frequency(conn, run_id, regional_df)

            tendency_df = tendency_results[level]
            save_regional_tendency(conn, run_id, tendency_df)
            save_tendency_significance(conn, run_id, tendency_df)

        # Step 6: Summary
        logger.info("=" * 60)
        logger.info("Summary Statistics")
        logger.info("=" * 60)
        for level in region_levels:
            if level not in tendency_results:
                continue
            df = tendency_results[level]
            n_total = len(df)
            n_significant = int(df['is_significant'].sum())
            pct = (n_significant / n_total * 100) if n_total > 0 else 0
            logger.info(f"\n{level}:")
            logger.info(f"  Total char-region pairs: {n_total:,}")
            logger.info(f"  Significant patterns: {n_significant:,} ({pct:.1f}%)")

            effect_counts = df['effect_size_interpretation'].value_counts()
            logger.info(f"  Effect sizes: {dict(effect_counts)}")

            top_sig = df[df['is_significant']].nlargest(5, 'effect_size')
            if len(top_sig) > 0:
                logger.info("  Top 5 significant patterns:")
                for _, row in top_sig.iterrows():
                    logger.info(
                        f"    {row['char']} in {row['region_name']}: "
                        f"p={row['p_value']:.4f}, effect={row['effect_size']:.3f}"
                    )

        elapsed = time.time() - start_time
        logger.info(f"\nPipeline completed in {elapsed:.2f}s")

        return {
            'run_id': run_id,
            'total_villages': len(villages_df),
            'unique_chars': len(freq_results['global']),
            'region_levels': region_levels,
            'runtime_seconds': round(elapsed, 2),
        }

    except Exception:
        logger.error("Error during tendency analysis", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def _chi_square_test(observed: float, expected: float, total_villages: int) -> tuple[float, float, float]:
    """Chi-square test for a single character-region pair.

    Compares observed character frequency in a region against the expected
    frequency under the null hypothesis of no regional preference.

    Returns (chi_square_statistic, p_value, cramers_v_effect_size).
    """
    obs_with = observed * total_villages
    obs_without = total_villages - obs_with
    exp_with = expected * total_villages
    exp_without = total_villages - exp_with

    # Guard against division by zero — expected counts may be zero for rare chars
    if exp_with == 0 or exp_without == 0:
        return 0.0, 1.0, 0.0

    # 2x2 chi-square: (O-E)²/E for both cells
    chi_square = ((obs_with - exp_with) ** 2) / exp_with + ((obs_without - exp_without) ** 2) / exp_without
    # df=1: comparing one observed proportion against expected
    p_value = 1 - stats.chi2.cdf(chi_square, df=1)
    # Cramér's V for 2x2 table simplifies to sqrt(chi²/N)
    effect_size = np.sqrt(chi_square / total_villages)

    return chi_square, p_value, effect_size


def _effect_interpretation(effect_size: float) -> str:
    """Cohen's (1988) guidelines for Cramér's V effect size interpretation.

    thresholds: <0.1 negligible, <0.3 small, <0.5 medium, >=0.5 large
    """
    if effect_size < 0.1:
        return 'negligible'
    elif effect_size < 0.3:
        return 'small'
    elif effect_size < 0.5:
        return 'medium'
    return 'large'


def run_significance_pipeline(
    db_path: str,
    run_id: str,
    significance_level: float = 0.05,
) -> dict[str, Any]:
    """Compute significance metrics from existing char_regional_analysis data.

    Reads pre-computed regional frequency/tendency, adds chi-square p-values
    and effect sizes, and persists to both char_regional_analysis (in-place
    column update) and tendency_significance (dedicated table).
    """
    logger.info("=" * 60)
    logger.info("Computing significance from char_regional_analysis")
    logger.info(f"  Run ID: {run_id}")
    logger.info("=" * 60)

    start_time = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        for col_name, col_type in [
            ('chi_square_statistic', 'REAL'),
            ('p_value', 'REAL'),
            ('is_significant', 'INTEGER'),
            ('effect_size', 'REAL'),
            ('effect_size_interpretation', 'TEXT'),
        ]:
            try:
                cursor.execute(f"ALTER TABLE char_regional_analysis ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
        conn.commit()

        # Step 2: Compute significance for each char-region pair already in DB.
        # Adds chi_square_statistic, p_value, is_significant, effect_size,
        # effect_size_interpretation columns to the existing char_regional_analysis rows.
        create_tendency_significance_table(conn)

        df = pd.read_sql_query("""
            SELECT region_level, city, county, township, region_name, char,
                   frequency as regional_freq, global_frequency,
                   village_count as regional_villages, z_score
            FROM char_regional_analysis
            WHERE global_frequency IS NOT NULL
        """, conn)
        logger.info(f"Loaded {len(df):,} records")

        logger.info("Computing significance metrics...")
        chi_sqs, p_vals, is_sigs, eff_sizes, eff_interps = [], [], [], [], []

        for idx, row in df.iterrows():
            if idx % 10000 == 0:
                logger.info(f"Processing {idx}/{len(df)}...")

            chi_sq, p_val, eff = _chi_square_test(
                row['regional_freq'], row['global_frequency'], row['regional_villages']
            )
            chi_sqs.append(chi_sq)
            p_vals.append(p_val)
            is_sigs.append(1 if p_val < significance_level else 0)
            eff_sizes.append(eff)
            eff_interps.append(_effect_interpretation(eff))

        df['chi_square_statistic'] = chi_sqs
        df['p_value'] = p_vals
        df['is_significant'] = is_sigs
        df['effect_size'] = eff_sizes
        df['effect_size_interpretation'] = eff_interps

        logger.info(f"Updating {len(df):,} records...")
        for idx, row in df.iterrows():
            if idx % 10000 == 0:
                logger.info(f"Updating {idx}/{len(df)}...")
            cursor.execute("""
                UPDATE char_regional_analysis
                SET chi_square_statistic = ?, p_value = ?, is_significant = ?,
                    effect_size = ?, effect_size_interpretation = ?
                WHERE region_level = ?
                    AND COALESCE(city, '') = COALESCE(?, '')
                    AND COALESCE(county, '') = COALESCE(?, '')
                    AND COALESCE(township, '') = COALESCE(?, '')
                    AND char = ?
            """, (
                row['chi_square_statistic'], row['p_value'], row['is_significant'],
                row['effect_size'], row['effect_size_interpretation'],
                row['region_level'],
                row[REGION_LEVELS[0]] if pd.notna(row[REGION_LEVELS[0]]) else '',
                row[REGION_LEVELS[1]] if pd.notna(row[REGION_LEVELS[1]]) else '',
                row[REGION_LEVELS[2]] if pd.notna(row[REGION_LEVELS[2]]) else '',
                row['char'],
            ))
        conn.commit()

        logger.info("Saving to tendency_significance table...")
        df['significance_level'] = significance_level
        save_tendency_significance(conn, run_id, df)

        for level in sorted(df['region_level'].unique()):
            ld = df[df['region_level'] == level]
            n_sig = int(ld['is_significant'].sum())
            logger.info(f"  {level}: {n_sig:,}/{len(ld):,} significant ({n_sig/max(len(ld),1)*100:.1f}%)")

        elapsed = time.time() - start_time
        logger.info(f"Significance pipeline completed in {elapsed:.2f}s")

        return {
            'run_id': run_id,
            'total_pairs': len(df),
            'significant_pairs': int(df['is_significant'].sum()),
            'runtime_seconds': round(elapsed, 2),
        }

    except Exception:
        logger.error("Error during significance computation", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()
