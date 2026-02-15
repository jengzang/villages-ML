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
import pandas as pd

from src.semantic.lexicon_loader import SemanticLexicon
from src.semantic.vtf_calculator import VTFCalculator
from src.semantic.semantic_index import SemanticIndexCalculator
from src.data.db_writer import (
    create_analysis_tables,
    write_semantic_vtf_global,
    write_semantic_vtf_regional,
    write_semantic_tendency,
    write_semantic_indices
)

logger = logging.getLogger(__name__)


def run_semantic_analysis_pipeline(
    db_path: str,
    char_run_id: str,
    output_run_id: str,
    lexicon_path: str = 'data/semantic_lexicon_v1.json',
    region_levels: List[str] = None,
    output_dir: Optional[str] = None
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
    """
    if region_levels is None:
        region_levels = ['city', 'county', 'township']

    logger.info(f"Starting semantic analysis pipeline")
    logger.info(f"  Character run ID: {char_run_id}")
    logger.info(f"  Output run ID: {output_run_id}")
    logger.info(f"  Lexicon: {lexicon_path}")
    logger.info(f"  Region levels: {region_levels}")

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

        # Load global character frequency
        global_char_df = pd.read_sql_query(f"""
            SELECT char as character, village_count, total_villages, frequency
            FROM char_frequency_global
            WHERE run_id = '{char_run_id}'
        """, conn)
        logger.info(f"Loaded {len(global_char_df)} global character frequencies")

        # Load regional character frequency
        regional_char_df = pd.read_sql_query(f"""
            SELECT region_level, region_name, char as character,
                   village_count, total_villages, frequency
            FROM char_frequency_regional
            WHERE run_id = '{char_run_id}'
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
        write_semantic_vtf_regional(conn, output_run_id, all_regional_vtf_df)
        write_semantic_tendency(conn, output_run_id, tendency_df)

        logger.info("Database write completed")

        # Step 6: Export CSV reports (if output_dir specified)
        if output_dir:
            logger.info(f"\\n=== Step 6: Exporting CSV reports to {output_dir} ===")
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Export global VTF
            global_vtf_df.to_csv(output_path / 'semantic_vtf_global.csv',
                                index=False, encoding='utf-8-sig')
            logger.info("Exported semantic_vtf_global.csv")

            # Export regional VTF by level
            for level in region_levels:
                level_df = regional_vtf_dfs[level]
                level_df.to_csv(output_path / f'semantic_vtf_regional_{level}.csv',
                              index=False, encoding='utf-8-sig')
                logger.info(f"Exported semantic_vtf_regional_{level}.csv")

            # Export tendency by level
            for level in region_levels:
                level_tendency_df = tendency_df[tendency_df['region_level'] == level]
                level_tendency_df.to_csv(output_path / f'semantic_tendency_{level}.csv',
                                        index=False, encoding='utf-8-sig')
                logger.info(f"Exported semantic_tendency_{level}.csv")

        elapsed = time.time() - start_time
        logger.info(f"\\n=== Pipeline completed in {elapsed:.2f}s ===")

    except Exception as e:
        logger.error(f"Error in semantic analysis pipeline: {e}")
        raise
    finally:
        conn.close()
