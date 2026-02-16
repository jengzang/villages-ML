#!/usr/bin/env python
"""
Run tendency analysis with statistical significance testing.

This script performs regional tendency analysis and computes statistical
significance (p-values, chi-square tests, effect sizes) for the results.

Usage:
    python scripts/run_tendency_with_significance.py --run-id tendency_v1
    python scripts/run_tendency_with_significance.py --run-id tendency_v1 --with-ci
"""

import argparse
import logging
import sqlite3
import time
from pathlib import Path

import pandas as pd

from src.data.db_loader import load_villages
from src.analysis.char_frequency import compute_char_frequency
from src.analysis.regional_analysis import (
    compute_regional_tendency,
    compute_tendency_significance
)
from src.data.db_writer import (
    create_analysis_tables,
    create_indexes,
    save_run_metadata,
    save_global_frequency,
    save_regional_frequency,
    save_regional_tendency,
    save_tendency_significance
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_tendency_analysis_with_significance(
    db_path: str,
    run_id: str,
    region_levels: list = None,
    with_ci: bool = True,
    min_global_support: int = 20,
    min_regional_support: int = 5
):
    """
    Run complete tendency analysis with significance testing.

    Args:
        db_path: Path to SQLite database
        run_id: Unique run identifier
        region_levels: List of region levels to analyze
        with_ci: Whether to compute confidence intervals
        min_global_support: Minimum global village count
        min_regional_support: Minimum regional village count
    """
    if region_levels is None:
        region_levels = ['市级', '县区级', '乡镇']

    logger.info(f"Starting tendency analysis with significance testing: run_id={run_id}")
    start_time = time.time()

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Create tables
        logger.info("Creating database tables...")
        create_analysis_tables(conn)
        create_indexes(conn)

        # Step 2: Load village data
        logger.info("Loading village data...")
        villages_df = load_villages(conn)
        logger.info(f"Loaded {len(villages_df)} villages")

        # Step 3: Compute character frequency
        logger.info("Computing character frequency...")
        freq_results = compute_char_frequency(
            villages_df,
            region_levels=region_levels,
            min_global_support=min_global_support,
            min_regional_support=min_regional_support
        )

        # Step 4: Compute tendency analysis
        logger.info("Computing regional tendency...")
        tendency_results = {}
        for level in region_levels:
            if level in freq_results['regional']:
                logger.info(f"Processing {level}...")
                regional_df = freq_results['regional'][level]

                # Compute tendency metrics
                tendency_df = compute_regional_tendency(
                    regional_df,
                    min_global_support=min_global_support,
                    min_regional_support=min_regional_support,
                    compute_z=True
                )

                # Compute statistical significance
                logger.info(f"Computing significance for {level}...")
                tendency_df = compute_tendency_significance(
                    tendency_df,
                    compute_ci=with_ci
                )

                tendency_results[level] = tendency_df

        # Step 5: Save to database
        logger.info("Saving results to database...")

        # Save run metadata
        metadata = {
            'created_at': time.time(),
            'total_villages': len(villages_df),
            'valid_villages': len(villages_df),
            'unique_chars': len(freq_results['global']),
            'config': {
                'region_levels': region_levels,
                'min_global_support': min_global_support,
                'min_regional_support': min_regional_support,
                'with_ci': with_ci
            },
            'status': 'completed'
        }
        save_run_metadata(conn, run_id, metadata)

        # Save global frequency
        save_global_frequency(conn, run_id, freq_results['global'])

        # Save regional frequency and tendency
        for level in region_levels:
            if level in freq_results['regional']:
                # Save regional frequency
                regional_df = freq_results['regional'][level]
                save_regional_frequency(conn, run_id, regional_df)

                # Save tendency results
                tendency_df = tendency_results[level]
                save_regional_tendency(conn, run_id, tendency_df)

                # Save significance results
                save_tendency_significance(conn, run_id, tendency_df)

        elapsed = time.time() - start_time
        logger.info(f"✓ Tendency analysis with significance testing completed in {elapsed:.2f}s")

        # Print summary statistics
        logger.info("\n=== Summary Statistics ===")
        for level in region_levels:
            if level in tendency_results:
                df = tendency_results[level]
                n_total = len(df)
                n_significant = df['is_significant'].sum()
                pct_significant = (n_significant / n_total * 100) if n_total > 0 else 0

                logger.info(f"\n{level}:")
                logger.info(f"  Total char-region pairs: {n_total}")
                logger.info(f"  Significant patterns: {n_significant} ({pct_significant:.1f}%)")

                # Effect size distribution
                effect_counts = df['effect_size_interpretation'].value_counts()
                logger.info(f"  Effect sizes: {dict(effect_counts)}")

                # Top significant patterns
                top_sig = df[df['is_significant']].nlargest(5, 'effect_size')
                if len(top_sig) > 0:
                    logger.info(f"  Top 5 significant patterns:")
                    for _, row in top_sig.iterrows():
                        logger.info(f"    {row['char']} in {row['region_name']}: "
                                  f"p={row['p_value']:.4f}, effect={row['effect_size']:.3f}")

    except Exception as e:
        logger.error(f"Error during tendency analysis: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Run tendency analysis with significance testing')
    parser.add_argument('--run-id', type=str, required=True, help='Unique run identifier')
    parser.add_argument('--db-path', type=str, default='data/villages.db', help='Path to database')
    parser.add_argument('--with-ci', action='store_true', help='Compute confidence intervals')
    parser.add_argument('--min-global-support', type=int, default=20, help='Minimum global village count')
    parser.add_argument('--min-regional-support', type=int, default=5, help='Minimum regional village count')

    args = parser.parse_args()

    run_tendency_analysis_with_significance(
        db_path=args.db_path,
        run_id=args.run_id,
        with_ci=args.with_ci,
        min_global_support=args.min_global_support,
        min_regional_support=args.min_regional_support
    )


if __name__ == '__main__':
    main()
