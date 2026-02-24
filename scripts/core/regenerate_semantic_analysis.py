#!/usr/bin/env python3
"""
重新生成語義分析數據（使用優化架構）

從 char_regional_analysis 表讀取數據，計算語義 VTF，
寫入 semantic_regional_analysis 表。
"""

import sqlite3
import sys
from pathlib import Path
import pandas as pd
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.semantic.lexicon_loader import SemanticLexicon
from src.semantic.vtf_calculator import VTFCalculator
from src.data.db_writer import write_semantic_regional_analysis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    db_path = project_root / 'data' / 'villages.db'
    lexicon_path = project_root / 'data' / 'semantic_lexicon_v1.json'

    logger.info("=" * 80)
    logger.info("重新生成語義分析數據")
    logger.info("=" * 80)
    logger.info(f"Database: {db_path}")
    logger.info(f"Lexicon: {lexicon_path}")

    # Step 1: Load semantic lexicon
    logger.info("\n[Step 1/4] Loading semantic lexicon...")
    lexicon = SemanticLexicon(str(lexicon_path))
    logger.info(f"Loaded {len(lexicon.list_categories())} categories: {lexicon.list_categories()}")

    # Step 2: Load character frequency data from char_regional_analysis
    logger.info("\n[Step 2/4] Loading character frequency data...")
    conn = sqlite3.connect(db_path)

    # Load global character frequency
    global_char_df = pd.read_sql_query("""
        SELECT
            char as character,
            SUM(village_count) as village_count,
            MAX(total_villages) as total_villages,
            AVG(frequency) as frequency
        FROM char_regional_analysis
        WHERE region_level = 'city'
        GROUP BY char
    """, conn)
    logger.info(f"Loaded {len(global_char_df)} global character frequencies")

    # Load regional character frequency
    regional_char_df = pd.read_sql_query("""
        SELECT
            region_level,
            city,
            county,
            township,
            region_name,
            char as character,
            village_count,
            total_villages,
            frequency
        FROM char_regional_analysis
    """, conn)
    logger.info(f"Loaded {len(regional_char_df)} regional character frequencies")

    # Step 3: Calculate VTF
    logger.info("\n[Step 3/4] Calculating Virtual Term Frequency...")
    vtf_calc = VTFCalculator(lexicon)

    # Global VTF
    global_vtf_df = vtf_calc.calculate_global_vtf(global_char_df)
    logger.info(f"Calculated global VTF for {len(global_vtf_df)} categories")

    # Regional VTF for each level
    all_regional_vtf_dfs = []
    for level in ['city', 'county', 'township']:
        logger.info(f"\nCalculating VTF for {level} level...")
        regional_vtf_df = vtf_calc.calculate_regional_vtf(regional_char_df, level)
        all_regional_vtf_dfs.append(regional_vtf_df)
        logger.info(f"Calculated VTF for {len(regional_vtf_df)} region-category pairs")

    # Combine all regional VTF
    all_regional_vtf_df = pd.concat(all_regional_vtf_dfs, ignore_index=True)
    logger.info(f"Total regional VTF records: {len(all_regional_vtf_df)}")

    # Calculate VTF tendency
    logger.info("\nCalculating VTF tendency...")
    tendency_df = vtf_calc.calculate_vtf_tendency(all_regional_vtf_df, global_vtf_df)
    logger.info(f"Calculated tendency for {len(tendency_df)} region-category pairs")

    # Add missing columns for database write
    tendency_df['rank_within_region'] = tendency_df.groupby(['region_level', 'city', 'county', 'township'])['vtf_count'].rank(
        ascending=False, method='dense'
    ).fillna(0).astype(int)

    tendency_df['global_vtf_count'] = tendency_df['category'].map(
        global_vtf_df.set_index('category')['vtf_count']
    ).fillna(0).astype(int)

    # Calculate overrepresented/underrepresented ranks
    overrep_ranks = tendency_df[tendency_df['lift'] > 1].groupby('region_level')['lift'].rank(
        ascending=False, method='dense'
    )
    tendency_df['rank_overrepresented'] = None
    tendency_df.loc[overrep_ranks.index, 'rank_overrepresented'] = overrep_ranks.astype(int)

    underrep_ranks = tendency_df[tendency_df['lift'] < 1].groupby('region_level')['lift'].rank(
        ascending=True, method='dense'
    )
    tendency_df['rank_underrepresented'] = None
    tendency_df.loc[underrep_ranks.index, 'rank_underrepresented'] = underrep_ranks.astype(int)

    # Step 4: Write results to database
    logger.info("\n[Step 4/4] Writing results to database...")

    # Ensure hierarchical columns are scalar values, not tuples
    for col in ['city', 'county', 'township']:
        if col in tendency_df.columns:
            # Convert any tuple values to strings or None
            tendency_df[col] = tendency_df[col].apply(
                lambda x: x if not isinstance(x, (tuple, list)) else (x[0] if x else None)
            )

    write_semantic_regional_analysis(conn, tendency_df)

    conn.close()

    logger.info("\n" + "=" * 80)
    logger.info("語義分析數據重新生成完成！")
    logger.info("=" * 80)

    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM semantic_regional_analysis").fetchone()[0]
    logger.info(f"semantic_regional_analysis: {count:,} records")
    conn.close()


if __name__ == '__main__':
    main()
