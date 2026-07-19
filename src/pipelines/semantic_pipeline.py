"""
Semantic analysis pipeline for village names.

This pipeline:
1. Loads semantic lexicon
2. Calculates Virtual Term Frequency (VTF) for semantic categories
3. Calculates regional semantic tendency
4. Calculates semantic intensity indices
5. Persists results to database
6. Exports CSV reports
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from src.schema import get_schema
from src.semantic.lexicon_loader import SemanticLexicon
from src.semantic.vtf_calculator import VTFCalculator
from src.semantic.semantic_index import SemanticIndexCalculator
from src.data.db_writer import (
    create_analysis_tables,
    create_semantic_tables,
    write_semantic_vtf_global,
    write_semantic_indices,
    write_semantic_regional_analysis,
)

logger = logging.getLogger(__name__)


def run_semantic_analysis_pipeline(
    db_path: str,
    char_run_id: str,
    output_run_id: str,
    lexicon_path: str = 'data/semantic_lexicon_v1.json',
    region_levels: List[str] = None,
    output_dir: Optional[str] = None,
    schema_name: str = 'guangdong',
) -> None:
    """
    Run complete semantic analysis pipeline.

    Args:
        db_path: Path to SQLite database
        char_run_id: Reference to character frequency run
        output_run_id: New run ID for semantic analysis
        lexicon_path: Path to semantic lexicon JSON
        region_levels: List of region levels to analyze
        output_dir: Directory for CSV exports (optional)
        schema_name: Village table schema name
    """
    if region_levels is None:
        region_levels = ['city', 'county', 'township']

    logger.info(f"Starting semantic analysis pipeline")
    logger.info(f"  Character run ID: {char_run_id}")
    logger.info(f"  Output run ID: {output_run_id}")
    logger.info(f"  Lexicon: {lexicon_path}")
    logger.info(f"  Region levels: {region_levels}")
    logger.info(f"  Schema: {schema_name}")

    start_time = time.time()

    # Step 1: Load semantic lexicon
    logger.info("\\n=== Step 1: Loading semantic lexicon ===")
    lexicon = SemanticLexicon(lexicon_path)
    logger.info(f"Loaded lexicon: {lexicon}")
    logger.info(f"Categories: {lexicon.list_categories()}")

    # Step 2: Connect to database and load character frequency data
    logger.info("\\n=== Step 2: Loading character frequency data ===")
    conn = sqlite3.connect(db_path)

    try:
        # Create tables if needed
        create_analysis_tables(conn)
        create_semantic_tables(conn)

        # Load global character frequency (no run_id after database optimization)
        global_char_df = pd.read_sql_query("""
            SELECT char as character, village_count, total_villages, frequency
            FROM char_frequency_global
        """, conn)
        logger.info(f"Loaded {len(global_char_df)} global character frequencies")

        # Load regional character frequency (from char_regional_analysis after optimization)
        regional_char_df = pd.read_sql_query("""
            SELECT region_level, region_name, char as character,
                   village_count, total_villages, frequency
            FROM char_regional_analysis
        """, conn)
        logger.info(f"Loaded {len(regional_char_df)} regional character frequencies")

        # Step 3: Calculate VTF
        logger.info("\\n=== Step 3: Calculating Virtual Term Frequency ===")
        vtf_calc = VTFCalculator(lexicon)

        # Global VTF
        global_vtf_df = vtf_calc.calculate_global_vtf(global_char_df)
        logger.info(f"Calculated global VTF for {len(global_vtf_df)} categories")
        logger.info(f"Top 3 categories:\\n{global_vtf_df.head(3)}")

        # Regional VTF for each level
        regional_vtf_dfs = {}
        for level in region_levels:
            logger.info(f"\\nCalculating VTF for {level} level...")
            regional_vtf_df = vtf_calc.calculate_regional_vtf(regional_char_df, level)
            regional_vtf_dfs[level] = regional_vtf_df
            logger.info(f"Calculated VTF for {len(regional_vtf_df)} region-category pairs")

        # Combine all regional VTF
        all_regional_vtf_df = pd.concat(regional_vtf_dfs.values(), ignore_index=True)
        logger.info(f"Total regional VTF records: {len(all_regional_vtf_df)}")

        # Step 4: Calculate VTF tendency
        logger.info("\\n=== Step 4: Calculating VTF tendency ===")
        tendency_df = vtf_calc.calculate_vtf_tendency(all_regional_vtf_df, global_vtf_df)
        logger.info(f"Calculated tendency for {len(tendency_df)} region-category pairs")

        # Step 5: Write results to database
        logger.info("\\n=== Step 5: Writing results to database ===")
        write_semantic_vtf_global(conn, output_run_id, global_vtf_df)

        logger.info("Database write completed")

        # Step 5b: Calculate and write semantic indices
        logger.info("\\n=== Step 5b: Calculating semantic indices ===")
        index_calculator = SemanticIndexCalculator(lexicon)

        S = get_schema(schema_name)
        villages_df = pd.read_sql_query(f"""
            SELECT {S.city_col}, {S.county_col}, {S.township_col},
                   {S.village_name_col_prefix_removed} as 自然村
            FROM {S.preprocessed_table}
        """, conn)
        logger.info(f"Loaded {len(villages_df)} villages for index calculation")

        all_indices = []
        level_config = [
            ('city', S.city_col, 'city'),
            ('county', S.county_col, 'county'),
            ('township', S.township_col, 'township'),
        ]
        for level, col_name, group_col in level_config:
            logger.info(f"Processing {level} level...")
            if level == 'city':
                level_df = villages_df[[S.city_col, '自然村']].copy()
                level_df = level_df.rename(columns={S.city_col: 'city'})
                count_df = villages_df.groupby(S.city_col).size().reset_index(name='village_count')
                count_df = count_df.rename(columns={S.city_col: 'region_name'})
                merge_keys = ['region_name']
            elif level == 'county':
                level_df = villages_df[[S.city_col, S.county_col, '自然村']].copy()
                level_df = level_df.rename(columns={S.city_col: 'city', S.county_col: 'county'})
                count_df = villages_df.groupby(S.county_col).size().reset_index(name='village_count')
                count_df = count_df.rename(columns={S.county_col: 'region_name'})
                merge_keys = ['region_name']
            else:
                level_df = villages_df[[S.city_col, S.county_col, S.township_col, '自然村']].copy()
                level_df = level_df.rename(columns={S.city_col: 'city', S.county_col: 'county', S.township_col: 'township'})
                # Township names can be duplicates across counties — use full hierarchy
                count_df = villages_df.groupby([S.city_col, S.county_col, S.township_col]).size().reset_index(name='village_count')
                count_df = count_df.rename(columns={S.city_col: 'city', S.county_col: 'county', S.township_col: 'region_name'})
                merge_keys = ['city', 'county', 'region_name']

            level_df = level_df[level_df[group_col].notna()]

            village_scores = index_calculator.calculate_semantic_scores(level_df)
            regional_indices = index_calculator.calculate_regional_indices(
                village_scores, level_column=group_col
            )
            regional_indices['region_level'] = level
            regional_indices = regional_indices.merge(count_df, on=merge_keys, how='left')
            regional_indices['village_count'] = regional_indices['village_count'].fillna(0).astype(int)
            all_indices.append(regional_indices)
            logger.info(f"  {len(regional_indices)} region-category pairs")

        combined_indices = pd.concat(all_indices, ignore_index=True)
        write_semantic_indices(conn, output_run_id, combined_indices)
        logger.info(f"Wrote {len(combined_indices)} semantic indices records")

        # Step 5c: Write semantic_regional_analysis (for backward compat with external backend)
        logger.info("\\n=== Step 5c: Writing semantic_regional_analysis ===")
        regional_df = combined_indices.copy()
        regional_df['vtf_count'] = (regional_df['raw_intensity'] * regional_df['village_count']).round().astype(int)
        regional_df['total_villages'] = regional_df['village_count']
        regional_df['frequency'] = regional_df['raw_intensity']
        regional_df['global_vtf_count'] = None
        regional_df['global_frequency'] = None
        regional_df['lift'] = regional_df['normalized_index']
        regional_df['log_lift'] = np.log(regional_df['normalized_index'].clip(lower=1e-10))
        regional_df['log_odds'] = 0.0
        regional_df['support_flag'] = 1
        regional_df['rank_within_region'] = regional_df['rank_within_province']
        regional_df['rank_overrepresented'] = None
        regional_df['rank_underrepresented'] = None
        write_semantic_regional_analysis(conn, regional_df)
        logger.info(f"Wrote {len(regional_df)} semantic_regional_analysis records")

        # Step 6: Export CSV reports (if output_dir specified)
        if output_dir:
            logger.info(f"\\n=== Step 6: Exporting CSV reports to {output_dir} ===")
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Export global VTF
            global_vtf_df.to_csv(output_path / 'semantic_vtf_global.csv',
                                index=False, encoding='utf-8-sig')
            logger.info("Exported semantic_vtf_global.csv")

        elapsed = time.time() - start_time
        logger.info(f"\\n=== Pipeline completed in {elapsed:.2f}s ===")

    except Exception as e:
        logger.error(f"Error in semantic analysis pipeline: {e}")
        raise
    finally:
        conn.close()
