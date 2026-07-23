"""
Populate semantic_indices table.

This script calculates semantic intensity indices for regions based on village name composition.
It uses the SemanticIndexCalculator to compute normalized semantic scores.

IMPORTANT (2026-02-25):
- Automatically calculates village_count for each region
- Auto-updates active_run_ids table after completion

Usage:
    python scripts/core/populate_semantic_indices.py --output-run-id semantic_indices_001
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.schema import DEFAULT_SCHEMA as S
from src.semantic.lexicon_loader import SemanticLexicon
from src.semantic.semantic_index import SemanticIndexCalculator
from src.data.db_writer import write_semantic_indices

# Import run_id manager for auto-update (NEW: 2026-02-25)
sys.path.insert(0, str(project_root / 'scripts'))
from utils.update_run_id import update_active_run_id

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_villages(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load preprocessed village data from database."""
    logger.info("Loading village data from database...")
    query = f"""
        SELECT {S.city_col}, {S.county_col}, {S.township_col},
               {S.village_name_col_prefix_removed} as 自然村
        FROM {S.preprocessed_table}
    """
    df = pd.read_sql_query(query, conn)
    logger.info(f"Loaded {len(df)} villages")
    return df


def main():
    parser = argparse.ArgumentParser(
        description='Populate semantic_indices table with normalized semantic intensity indices'
    )

    parser.add_argument(
        '--output-run-id',
        type=str,
        required=True,
        help='Output run ID for semantic indices (e.g., semantic_indices_001)'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to SQLite database (default: data/villages.db)'
    )

    parser.add_argument(
        '--lexicon-path',
        type=str,
        default='data/semantic_lexicon_v1.json',
        help='Path to semantic lexicon JSON (default: data/semantic_lexicon_v1.json)'
    )

    parser.add_argument(
        '--region-levels',
        type=str,
        nargs='+',
        default=REGION_LEVELS[:3],
        help='Region levels to analyze (default: city county township)'
    )

    args = parser.parse_args()

    logger.info("Starting semantic indices calculation")
    logger.info(f"Arguments: {vars(args)}")

    start_time = time.time()

    try:
        # Load semantic lexicon
        logger.info(f"\n=== Step 1: Loading semantic lexicon ===")
        lexicon = SemanticLexicon(args.lexicon_path)
        logger.info(f"Loaded lexicon with {len(lexicon.list_categories())} categories")

        # Connect to database
        conn = sqlite3.connect(args.db_path)

        # Load village data
        logger.info(f"\n=== Step 2: Loading village data ===")
        villages_df = load_villages(conn)

        # Initialize calculator
        calculator = SemanticIndexCalculator(lexicon)

        # Process each region level
        all_indices = []

        for level in args.region_levels:
            logger.info(f"\n=== Step 3: Processing {level} level ===")

            # Map level to column name
            if level not in S.level_map:
                logger.warning(f"Unknown region level: {level}, skipping")
                continue

            level_column = S.level_map[level]

            # Prepare data for this level - include hierarchy based on level
            if level == REGION_LEVELS[0]:
                level_df = villages_df[[S.city_col, '自然村']].copy()
                level_df = level_df.rename(columns={S.city_col: REGION_LEVELS[0]})
                level_df['自然村'] = villages_df['自然村']
            elif level == REGION_LEVELS[1]:
                level_df = villages_df[[S.city_col, S.county_col, '自然村']].copy()
                level_df = level_df.rename(columns={S.city_col: REGION_LEVELS[0], S.county_col: REGION_LEVELS[1]})
            elif level == REGION_LEVELS[2]:
                level_df = villages_df[[S.city_col, S.county_col, S.township_col, '自然村']].copy()
                level_df = level_df.rename(columns={S.city_col: REGION_LEVELS[0], S.county_col: REGION_LEVELS[1], S.township_col: REGION_LEVELS[2]})

            # Filter out NULL region names for the current level
            if level == REGION_LEVELS[0]:
                level_df = level_df[level_df[REGION_LEVELS[0]].notna()]
            elif level == REGION_LEVELS[1]:
                level_df = level_df[level_df[REGION_LEVELS[1]].notna()]
            elif level == REGION_LEVELS[2]:
                level_df = level_df[level_df[REGION_LEVELS[2]].notna()]

            logger.info(f"Processing {len(level_df)} villages with valid {level} names")

            # Calculate semantic scores for each village
            logger.info(f"Calculating semantic scores for {len(level_df)} villages...")
            village_scores = calculator.calculate_semantic_scores(level_df)

            # Calculate regional indices
            logger.info(f"Calculating regional indices...")
            # Determine which column to use for grouping based on level
            if level == REGION_LEVELS[0]:
                group_column = REGION_LEVELS[0]
            elif level == REGION_LEVELS[1]:
                group_column = REGION_LEVELS[1]
            elif level == REGION_LEVELS[2]:
                group_column = REGION_LEVELS[2]
            else:
                group_column = 'region_name'

            regional_indices = calculator.calculate_regional_indices(
                village_scores, level_column=group_column
            )

            # Add region level
            regional_indices['region_level'] = level

            logger.info(f"Calculated indices for {len(regional_indices)} region-category pairs")
            all_indices.append(regional_indices)

        # Combine all levels
        logger.info(f"\n=== Step 4: Combining results ===")
        combined_indices = pd.concat(all_indices, ignore_index=True)
        logger.info(f"Total indices: {len(combined_indices)}")

        # Write to database
        logger.info(f"\n=== Step 5: Writing to database ===")
        write_semantic_indices(conn, args.output_run_id, combined_indices)

        conn.close()

        elapsed = time.time() - start_time
        logger.info(f"\n=== Completed in {elapsed:.2f}s ===")
        logger.info(f"Wrote {len(combined_indices)} semantic indices records")

        # Auto-update active_run_ids (NEW: 2026-02-25)
        logger.info(f"\n=== Step 6: Updating active_run_ids ===")

        # Count unique regions for notes
        unique_regions = combined_indices[['region_level', 'region_name']].drop_duplicates()
        region_count = len(unique_regions)

        update_active_run_id(
            analysis_type="semantic_indices",
            run_id=args.output_run_id,
            script_name="populate_semantic_indices",
            notes=f"Semantic indices calculated for {region_count} regions across {len(args.region_levels)} levels.",
            db_path=args.db_path
        )

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
