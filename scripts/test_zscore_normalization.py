#!/usr/bin/env python
"""
Test z-score normalization method for tendency analysis.

This script compares the results of percentage-based and z-score-based
normalization methods to demonstrate the differences.

Usage:
    python scripts/test_zscore_normalization.py
"""

import argparse
import json
import logging
import sqlite3
import time
from pathlib import Path

import pandas as pd

from src.data.db_loader import load_villages
from src.preprocessing.char_extractor import extract_char_set
from src.analysis.char_frequency import compute_char_frequency
from src.analysis.regional_analysis import (
    compute_regional_tendency,
    compute_tendency_significance
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def compare_normalization_methods(
    db_path: str,
    region_level: str = '市级',
    sample_region: str = None,
    top_n: int = 10
):
    """
    Compare percentage and z-score normalization methods.

    Args:
        db_path: Path to SQLite database
        region_level: Region level to analyze
        sample_region: Specific region to analyze (None = all regions)
        top_n: Number of top results to display
    """
    logger.info("=== Comparing Normalization Methods ===")
    logger.info(f"Region level: {region_level}")
    logger.info(f"Sample region: {sample_region or 'All regions'}")

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Load village data
        logger.info("Loading village data...")
        villages_chunks = load_villages(conn)
        villages_df = pd.concat(list(villages_chunks), ignore_index=True)
        logger.info(f"Loaded {len(villages_df)} villages")

        # Preprocess: add char_set_json and is_valid columns
        logger.info("Preprocessing village names...")
        villages_df['char_set'] = villages_df['自然村'].apply(lambda x: extract_char_set(x) if pd.notna(x) else set())
        villages_df['char_set_json'] = villages_df['char_set'].apply(lambda x: json.dumps(list(x), ensure_ascii=False))
        villages_df['is_valid'] = villages_df['char_set'].apply(lambda x: len(x) > 0)
        logger.info(f"Valid villages: {villages_df['is_valid'].sum()}/{len(villages_df)}")

        # Compute character frequency
        logger.info("Computing character frequency...")
        freq_results = compute_char_frequency(
            villages_df,
            region_levels=[region_level],
            min_global_support=20,
            min_regional_support=5
        )

        regional_df = freq_results['regional'][region_level]

        # Filter to sample region if specified
        if sample_region:
            regional_df = regional_df[regional_df['region_name'] == sample_region]
            if len(regional_df) == 0:
                logger.error(f"Region '{sample_region}' not found")
                return

        # Method 1: Percentage-based (lift)
        logger.info("\n=== Method 1: Percentage-based (lift) ===")
        tendency_pct = compute_regional_tendency(
            regional_df,
            normalization_method='percentage',
            compute_z=True
        )

        # Method 2: Z-score-based
        logger.info("\n=== Method 2: Z-score-based ===")
        tendency_zscore = compute_regional_tendency(
            regional_df,
            normalization_method='zscore',
            compute_z=True
        )

        # Compare results
        logger.info("\n=== Comparison Results ===")

        if sample_region:
            regions_to_compare = [sample_region]
        else:
            # Pick a few representative regions
            regions_to_compare = regional_df['region_name'].unique()[:3]

        for region in regions_to_compare:
            logger.info(f"\n--- Region: {region} ---")

            # Top overrepresented (percentage method)
            top_pct = tendency_pct[
                (tendency_pct['region_name'] == region) &
                (tendency_pct['support_flag'] == 1)
            ].nlargest(top_n, 'lift')

            # Top overrepresented (z-score method)
            top_zscore = tendency_zscore[
                (tendency_zscore['region_name'] == region) &
                (tendency_zscore['support_flag'] == 1)
            ].nlargest(top_n, 'z_score')

            logger.info(f"\nTop {top_n} overrepresented (Percentage method):")
            logger.info(f"{'Rank':<6} {'Char':<6} {'Lift':<10} {'Z-score':<10} {'Freq':<10}")
            logger.info("-" * 50)
            for idx, (_, row) in enumerate(top_pct.iterrows(), 1):
                logger.info(f"{idx:<6} {row['char']:<6} {row['lift']:<10.2f} "
                          f"{row.get('z_score', 0):<10.2f} {row['frequency']*100:<10.2f}%")

            logger.info(f"\nTop {top_n} overrepresented (Z-score method):")
            logger.info(f"{'Rank':<6} {'Char':<6} {'Z-score':<10} {'Lift':<10} {'Freq':<10}")
            logger.info("-" * 50)
            for idx, (_, row) in enumerate(top_zscore.iterrows(), 1):
                logger.info(f"{idx:<6} {row['char']:<6} {row['z_score']:<10.2f} "
                          f"{row['lift']:<10.2f} {row['frequency']*100:<10.2f}%")

            # Analyze differences
            pct_chars = set(top_pct['char'].tolist())
            zscore_chars = set(top_zscore['char'].tolist())

            common = pct_chars & zscore_chars
            only_pct = pct_chars - zscore_chars
            only_zscore = zscore_chars - pct_chars

            logger.info(f"\nOverlap analysis:")
            logger.info(f"  Common characters: {len(common)}/{top_n}")
            logger.info(f"  Only in percentage: {only_pct if only_pct else 'None'}")
            logger.info(f"  Only in z-score: {only_zscore if only_zscore else 'None'}")

        # Summary statistics
        logger.info("\n=== Summary Statistics ===")
        logger.info(f"Total char-region pairs: {len(tendency_pct)}")
        logger.info(f"Pairs meeting support threshold: {tendency_pct['support_flag'].sum()}")

        # Correlation between lift and z-score
        valid_data = tendency_pct[tendency_pct['support_flag'] == 1]
        if len(valid_data) > 0 and 'z_score' in valid_data.columns:
            correlation = valid_data['lift'].corr(valid_data['z_score'])
            logger.info(f"Correlation between lift and z-score: {correlation:.3f}")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Test z-score normalization method')
    parser.add_argument('--db-path', type=str, default='data/villages.db', help='Path to database')
    parser.add_argument('--region-level', type=str, default='市级',
                        choices=['市级', '县区级', '乡镇'],
                        help='Region level to analyze')
    parser.add_argument('--sample-region', type=str, default=None,
                        help='Specific region to analyze (e.g., "广州市")')
    parser.add_argument('--top-n', type=int, default=10,
                        help='Number of top results to display')

    args = parser.parse_args()

    compare_normalization_methods(
        db_path=args.db_path,
        region_level=args.region_level,
        sample_region=args.sample_region,
        top_n=args.top_n
    )


if __name__ == '__main__':
    main()

