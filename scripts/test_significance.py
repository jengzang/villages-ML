#!/usr/bin/env python
"""
Simple test script for statistical significance testing.

This script tests the significance testing functions by:
1. Loading village data
2. Computing character frequency
3. Computing regional tendency
4. Computing statistical significance
5. Saving results to database
"""

import sys
import logging
import sqlite3
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from src.data.db_loader import load_villages
from src.preprocessing.char_extractor import process_village_batch
from src.analysis.char_frequency import (
    compute_char_frequency_global,
    compute_char_frequency_by_region,
    calculate_lift
)
from src.analysis.regional_analysis import (
    compute_regional_tendency,
    compute_tendency_significance
)
from src.data.db_writer import (
    create_analysis_tables,
    create_indexes,
    save_tendency_significance
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_significance_workflow():
    """Test the complete significance testing workflow."""

    db_path = 'data/villages.db'
    run_id = f'test_sig_{int(time.time())}'

    logger.info(f"Starting significance testing workflow: run_id={run_id}")

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Create tables
        logger.info("Creating database tables...")
        create_analysis_tables(conn)
        create_indexes(conn)

        # Step 2: Load village data
        logger.info("Loading village data...")
        villages_chunks = list(load_villages(conn))
        villages_df = pd.concat(villages_chunks, ignore_index=True)
        logger.info(f"Loaded {len(villages_df)} villages")

        # Step 3: Preprocess villages (clean names and extract character sets)
        logger.info("Preprocessing village names...")
        villages_df = process_village_batch(villages_df)
        logger.info(f"Preprocessed: {villages_df['is_valid'].sum()} valid villages")

        # Step 4: Compute global character frequency
        logger.info("Computing global character frequency...")
        global_freq_df = compute_char_frequency_global(villages_df)
        logger.info(f"Found {len(global_freq_df)} unique characters")

        # Step 5: Compute regional frequency (just one level for testing)
        region_level = 'city'  # City level
        logger.info(f"Computing regional frequency for {region_level}...")
        regional_freq_df = compute_char_frequency_by_region(
            villages_df,
            region_level=region_level
        )
        logger.info(f"Computed frequency for {len(regional_freq_df)} char-region pairs")

        # Step 5.5: Calculate lift (compare regional to global)
        logger.info("Calculating lift values...")
        regional_freq_df = calculate_lift(regional_freq_df, global_freq_df)

        # Step 6: Compute tendency metrics
        logger.info("Computing regional tendency...")
        tendency_df = compute_regional_tendency(
            regional_freq_df,
            min_global_support=20,
            min_regional_support=5,
            compute_z=True
        )
        logger.info(f"Computed tendency for {len(tendency_df)} char-region pairs")

        # Step 7: Compute statistical significance
        logger.info("Computing statistical significance...")
        tendency_df = compute_tendency_significance(
            tendency_df,
            compute_ci=True,
            confidence_level=0.95
        )

        # Step 8: Analyze results
        n_total = len(tendency_df)
        n_significant = tendency_df['is_significant'].sum()
        pct_significant = (n_significant / n_total * 100) if n_total > 0 else 0

        logger.info(f"\n=== Results Summary ===")
        logger.info(f"Total char-region pairs: {n_total}")
        logger.info(f"Significant patterns (p < 0.05): {n_significant} ({pct_significant:.1f}%)")

        # Effect size distribution
        effect_counts = tendency_df['effect_size_interpretation'].value_counts()
        logger.info(f"Effect size distribution:")
        for effect, count in effect_counts.items():
            logger.info(f"  {effect}: {count}")

        # Top significant patterns
        top_sig = tendency_df[tendency_df['is_significant']].nlargest(10, 'effect_size')
        if len(top_sig) > 0:
            logger.info(f"\nTop 10 significant patterns:")
            for i, (_, row) in enumerate(top_sig.iterrows(), 1):
                logger.info(f"  {i}. '{row['char']}' in {row['region_name']}: "
                          f"p={row['p_value']:.6f}, effect={row['effect_size']:.4f} ({row['effect_size_interpretation']}), "
                          f"lift={row['lift']:.2f}")

        # Step 9: Save to database
        logger.info(f"\nSaving results to database...")
        save_tendency_significance(conn, run_id, tendency_df)

        # Verify database write
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tendency_significance WHERE run_id=?", (run_id,))
        count = cursor.fetchone()[0]
        logger.info(f"✓ Saved {count} records to tendency_significance table")

        # Query a sample
        cursor.execute("""
            SELECT char, region_name, p_value, significance_level, effect_size
            FROM tendency_significance
            WHERE run_id=? AND is_significant=1
            ORDER BY effect_size DESC
            LIMIT 5
        """, (run_id,))

        logger.info(f"\nSample from database:")
        for row in cursor.fetchall():
            logger.info(f"  {row[0]} in {row[1]}: p={row[2]:.6f} {row[3]}, effect={row[4]:.4f}")

        logger.info(f"\n✓ Test completed successfully!")
        logger.info(f"Run ID: {run_id}")

    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    test_significance_workflow()
