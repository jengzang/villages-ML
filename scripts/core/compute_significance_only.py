#!/usr/bin/env python
"""
Compute statistical significance for existing tendency data.

This script reads from the optimized char_regional_analysis table
and computes statistical significance metrics.

Usage:
    python scripts/core/compute_significance_only.py --run-id significance_v1
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def compute_chi_square_test(observed, expected, total_villages):
    """
    Compute chi-square test for character frequency.

    Args:
        observed: Observed frequency in region
        expected: Expected frequency (global rate)
        total_villages: Total villages in region

    Returns:
        tuple: (chi_square, p_value, effect_size)
    """
    # Observed counts
    obs_with_char = observed * total_villages
    obs_without_char = total_villages - obs_with_char

    # Expected counts
    exp_with_char = expected * total_villages
    exp_without_char = total_villages - exp_with_char

    # Avoid division by zero
    if exp_with_char == 0 or exp_without_char == 0:
        return 0.0, 1.0, 0.0

    # Chi-square test
    observed_counts = np.array([obs_with_char, obs_without_char])
    expected_counts = np.array([exp_with_char, exp_without_char])

    chi_square = np.sum((observed_counts - expected_counts) ** 2 / expected_counts)
    p_value = 1 - stats.chi2.cdf(chi_square, df=1)

    # Effect size (Cramer's V for 2x1 table = phi coefficient)
    effect_size = np.sqrt(chi_square / total_villages)

    return chi_square, p_value, effect_size


def compute_significance_from_regional_analysis(
    db_path: str,
    run_id: str,
    significance_level: float = 0.05
):
    """
    Compute significance from char_regional_analysis table.

    Args:
        db_path: Path to database
        run_id: Run identifier for output
        significance_level: Significance threshold (default 0.05)
    """
    logger.info(f"Computing significance from char_regional_analysis...")
    logger.info(f"Output run_id: {run_id}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add significance columns if they don't exist
        logger.info("Ensuring significance columns exist...")
        columns_to_add = [
            ('chi_square_statistic', 'REAL'),
            ('p_value', 'REAL'),
            ('is_significant', 'INTEGER'),
            ('effect_size', 'REAL'),
            ('effect_size_interpretation', 'TEXT')
        ]

        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE char_regional_analysis ADD COLUMN {col_name} {col_type}")
                logger.info(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    pass  # Column already exists
                else:
                    raise
        conn.commit()
        # Load regional analysis data (with hierarchy - 2026-03-01)
        query = """
        SELECT
            region_level,
            city,
            county,
            township,
            region_name,
            char,
            frequency as regional_freq,
            global_frequency,
            village_count as regional_villages,
            z_score
        FROM char_regional_analysis
        WHERE global_frequency IS NOT NULL
        """

        logger.info("Loading regional analysis data...")
        df = pd.read_sql_query(query, conn)
        logger.info(f"Loaded {len(df)} records")

        # Compute significance for each row
        logger.info("Computing significance metrics...")

        chi_squares = []
        p_values = []
        is_significants = []
        effect_sizes = []
        effect_interps = []

        for idx, row in df.iterrows():
            if idx % 10000 == 0:
                logger.info(f"Processing {idx}/{len(df)}...")

            chi_square, p_value, effect_size = compute_chi_square_test(
                observed=row['regional_freq'],
                expected=row['global_frequency'],
                total_villages=row['regional_villages']
            )

            is_significant = 1 if p_value < significance_level else 0

            # Effect size interpretation (Cohen's guidelines)
            if effect_size < 0.1:
                effect_interp = 'negligible'
            elif effect_size < 0.3:
                effect_interp = 'small'
            elif effect_size < 0.5:
                effect_interp = 'medium'
            else:
                effect_interp = 'large'

            chi_squares.append(chi_square)
            p_values.append(p_value)
            is_significants.append(is_significant)
            effect_sizes.append(effect_size)
            effect_interps.append(effect_interp)

        # Add computed columns to dataframe
        df['chi_square_statistic'] = chi_squares
        df['p_value'] = p_values
        df['is_significant'] = is_significants
        df['effect_size'] = effect_sizes
        df['effect_size_interpretation'] = effect_interps

        # Update database with significance values
        logger.info(f"Updating {len(df)} records with significance values...")

        for idx, row in df.iterrows():
            if idx % 10000 == 0:
                logger.info(f"Updating {idx}/{len(df)}...")

            cursor.execute("""
                UPDATE char_regional_analysis
                SET chi_square_statistic = ?,
                    p_value = ?,
                    is_significant = ?,
                    effect_size = ?,
                    effect_size_interpretation = ?
                WHERE region_level = ?
                    AND COALESCE(city, '') = COALESCE(?, '')
                    AND COALESCE(county, '') = COALESCE(?, '')
                    AND COALESCE(township, '') = COALESCE(?, '')
                    AND char = ?
            """, (
                row['chi_square_statistic'],
                row['p_value'],
                row['is_significant'],
                row['effect_size'],
                row['effect_size_interpretation'],
                row['region_level'],
                row['city'] if pd.notna(row['city']) else None,
                row['county'] if pd.notna(row['county']) else None,
                row['township'] if pd.notna(row['township']) else None,
                row['char']
            ))

        conn.commit()

        # Print summary
        logger.info("\n=== Summary Statistics ===")
        for level in df['region_level'].unique():
            level_df = df[df['region_level'] == level]
            n_total = len(level_df)
            n_significant = level_df['is_significant'].sum()
            pct_significant = (n_significant / n_total * 100) if n_total > 0 else 0

            logger.info(f"\n{level}:")
            logger.info(f"  Total char-region pairs: {n_total}")
            logger.info(f"  Significant patterns: {n_significant} ({pct_significant:.1f}%)")

            # Effect size distribution
            effect_counts = level_df['effect_size_interpretation'].value_counts()
            logger.info(f"  Effect sizes: {dict(effect_counts)}")

            # Top significant patterns
            top_sig = level_df[level_df['is_significant'] == 1].nlargest(5, 'effect_size')
            if len(top_sig) > 0:
                logger.info(f"  Top 5 significant patterns:")
                for _, row in top_sig.iterrows():
                    logger.info(f"    {row['char']} in {row['region_name']}: "
                              f"p={row['p_value']:.4f}, effect={row['effect_size']:.3f}")

        logger.info(f"\n✓ Significance computation completed successfully")
        logger.info(f"✓ Updated char_regional_analysis table with significance metrics")

    except Exception as e:
        logger.error(f"Error during significance computation: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Compute statistical significance from existing data')
    parser.add_argument('--run-id', type=str, required=True, help='Run identifier for output')
    parser.add_argument('--db-path', type=str, default='data/villages.db', help='Path to database')
    parser.add_argument('--significance-level', type=float, default=0.05, help='Significance threshold')

    args = parser.parse_args()

    compute_significance_from_regional_analysis(
        db_path=args.db_path,
        run_id=args.run_id,
        significance_level=args.significance_level
    )


if __name__ == '__main__':
    main()
