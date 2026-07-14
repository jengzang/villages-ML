"""Create preprocessed village table with prefix cleaning and normalization.

This script:
1. Loads raw village data
2. Applies basic text cleaning (brackets, noise)
3. Applies administrative prefix removal
4. Applies numbered village normalization
5. Extracts character sets
6. Stores results in preprocessed table
"""

import sqlite3
import logging
import json
import time
from pathlib import Path
import pandas as pd
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.schema import DEFAULT_SCHEMA as S
from src.preprocessing.text_cleaner import normalize_village_name
from src.preprocessing.prefix_cleaner import batch_clean_prefixes
from src.preprocessing.numbered_village_normalizer import (
    normalize_numbered_village,
    detect_trailing_numeral
)
from src.preprocessing.char_extractor import extract_char_set

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def materialize_metadata_stats(
    conn: sqlite3.Connection,
    data_version: str = "phase0_preprocessing",
):
    """Materialize small metadata tables for overview and region list APIs."""
    cursor = conn.cursor()
    generated_at = time.time()

    cursor.execute("DROP TABLE IF EXISTS metadata_overview_stats")
    cursor.execute("""
    CREATE TABLE metadata_overview_stats (
        total_villages INTEGER NOT NULL,
        total_cities INTEGER NOT NULL,
        total_counties INTEGER NOT NULL,
        total_townships INTEGER NOT NULL,
        unique_characters INTEGER NOT NULL,
        generated_at REAL NOT NULL,
        data_version TEXT NOT NULL
    )
    """)

    cursor.execute(f"""
        SELECT
            COUNT(*) as total_villages,
            COUNT(DISTINCT {S.city_col}) as total_cities,
            COUNT(DISTINCT {S.county_col}) as total_counties,
            COUNT(DISTINCT {S.township_col}) as total_townships
        FROM {S.preprocessed_table}
    """)
    total_villages, total_cities, total_counties, total_townships = cursor.fetchone()

    unique_chars = set()
    cursor.execute(f"""
        SELECT {S.char_set_col}
        FROM {S.preprocessed_table}
        WHERE {S.char_set_col} IS NOT NULL AND {S.char_set_col} != ''
    """)
    for (char_set_json,) in cursor.fetchall():
        try:
            unique_chars.update(json.loads(char_set_json))
        except (TypeError, json.JSONDecodeError):
            continue

    cursor.execute("""
        INSERT INTO metadata_overview_stats (
            total_villages,
            total_cities,
            total_counties,
            total_townships,
            unique_characters,
            generated_at,
            data_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        total_villages,
        total_cities,
        total_counties,
        total_townships,
        len(unique_chars),
        generated_at,
        data_version,
    ))

    cursor.execute("DROP TABLE IF EXISTS region_hierarchy_stats")
    cursor.execute("""
    CREATE TABLE region_hierarchy_stats (
        level TEXT NOT NULL,
        name TEXT NOT NULL,
        city TEXT,
        county TEXT,
        township TEXT,
        parent TEXT,
        village_count INTEGER NOT NULL,
        sort_key TEXT,
        generated_at REAL NOT NULL,
        data_version TEXT NOT NULL,
        PRIMARY KEY (level, city, county, township)
    )
    """)

    cursor.execute(f"""
        INSERT INTO region_hierarchy_stats (
            level, name, city, county, township, parent,
            village_count, sort_key, generated_at, data_version
        )
        SELECT
            'city',
            {S.city_col},
            {S.city_col},
            NULL,
            NULL,
            NULL,
            COUNT(*),
            {S.city_col},
            ?,
            ?
        FROM {S.preprocessed_table}
        WHERE {S.city_col} IS NOT NULL AND {S.city_col} != ''
        GROUP BY {S.city_col}
    """, (generated_at, data_version))

    cursor.execute(f"""
        INSERT INTO region_hierarchy_stats (
            level, name, city, county, township, parent,
            village_count, sort_key, generated_at, data_version
        )
        SELECT
            'county',
            {S.county_col},
            {S.city_col},
            {S.county_col},
            NULL,
            {S.city_col},
            COUNT(*),
            {S.city_col} || '|' || {S.county_col},
            ?,
            ?
        FROM {S.preprocessed_table}
        WHERE {S.county_col} IS NOT NULL AND {S.county_col} != ''
        GROUP BY {S.city_col}, {S.county_col}
    """, (generated_at, data_version))

    cursor.execute(f"""
        INSERT INTO region_hierarchy_stats (
            level, name, city, county, township, parent,
            village_count, sort_key, generated_at, data_version
        )
        SELECT
            'township',
            {S.township_col},
            {S.city_col},
            {S.county_col},
            {S.township_col},
            {S.county_col},
            COUNT(*),
            {S.city_col} || '|' || {S.county_col} || '|' || {S.township_col},
            ?,
            ?
        FROM {S.preprocessed_table}
        WHERE {S.township_col} IS NOT NULL AND {S.township_col} != ''
        GROUP BY {S.city_col}, {S.county_col}, {S.township_col}
    """, (generated_at, data_version))

    cursor.execute(
        "CREATE INDEX idx_region_hierarchy_level_sort ON region_hierarchy_stats(level, sort_key)"
    )
    cursor.execute(
        "CREATE INDEX idx_region_hierarchy_parent ON region_hierarchy_stats(level, parent)"
    )

    conn.commit()
    logger.info("Materialized metadata_overview_stats and region_hierarchy_stats")


def create_preprocessed_table(conn: sqlite3.Connection):
    """Create the preprocessed table schema (optimized with only 12 essential columns)."""
    cursor = conn.cursor()

    # Drop if exists
    cursor.execute(f"DROP TABLE IF EXISTS {S.preprocessed_table}")

    # Create table with only essential columns (space-optimized)
    cursor.execute(f"""
    CREATE TABLE {S.preprocessed_table} (
        {S.city_col} TEXT,
        {S.county_col} TEXT,
        {S.township_col} TEXT,
        {S.committee_col_preprocessed} TEXT,
        {S.village_name_col_normalized} TEXT,
        {S.village_name_col_prefix_removed} TEXT,
        {S.longitude_col} REAL,
        {S.latitude_col} REAL,
        {S.language_col_preprocessed} TEXT,
        {S.char_set_col} TEXT,
        {S.char_count_col} INTEGER,
        {S.village_id_col} TEXT
    )
    """)

    # Create indexes
    cursor.execute(f"CREATE INDEX idx_prep_city ON {S.preprocessed_table}({S.city_col})")
    cursor.execute(f"CREATE INDEX idx_prep_county ON {S.preprocessed_table}({S.county_col})")
    cursor.execute(f"CREATE INDEX idx_prep_township ON {S.preprocessed_table}({S.township_col})")
    cursor.execute(f"CREATE INDEX idx_prep_admin ON {S.preprocessed_table}({S.committee_col_preprocessed})")
    cursor.execute(f"CREATE INDEX idx_prep_village_id ON {S.preprocessed_table}({S.village_id_col})")

    conn.commit()
    logger.info(f"Created optimized preprocessed table schema (12 columns)")


def main():
    """Main preprocessing pipeline."""
    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Create preprocessed table
    create_preprocessed_table(conn)

    # Load raw data
    logger.info("Loading raw village data...")
    query = f"SELECT * FROM {S.raw_table}"
    df = pd.read_sql(query, conn)
    logger.info(f"Loaded {len(df)} villages")

    # Rename columns to match known raw table column order
    df.columns = [
        S.city_col, S.county_col, S.township_col, S.committee_col_raw,
        S.village_name_col_raw, S.pinyin_col, S.language_col_raw,
        S.longitude_col, S.latitude_col, '备注', '更新时间', '数据来源'
    ]

    # Convert longitude and latitude to numeric (REAL type)
    logger.info("Converting longitude and latitude to numeric...")
    df[S.longitude_col] = pd.to_numeric(df[S.longitude_col], errors='coerce')
    df[S.latitude_col] = pd.to_numeric(df[S.latitude_col], errors='coerce')

    # Fill county for cities without county-level divisions (Dongguan, Zhongshan)
    logger.info("Filling county for cities without county-level divisions...")
    null_county_mask = df[S.county_col].isna()
    df.loc[null_county_mask, S.county_col] = df.loc[null_county_mask, S.city_col]
    filled_count = null_county_mask.sum()
    logger.info(f"  Filled {filled_count} records")

    # Step 1: Basic text cleaning
    logger.info("Step 1: Basic text cleaning...")
    cleaning_results = []
    for idx, row in df.iterrows():
        if idx % 10000 == 0:
            logger.info(f"  Progress: {idx}/{len(df)}")

        cleaned = normalize_village_name(row[S.village_name_col_raw])
        cleaning_results.append({
            '自然村_基础清洗': cleaned.clean_name,
            '有括号': 1 if cleaned.had_brackets else 0,
            '有噪音': 1 if cleaned.had_noise else 0,
        })

    df_clean = pd.concat([df, pd.DataFrame(cleaning_results)], axis=1)

    # Step 2: Administrative prefix removal
    logger.info("Step 2: Administrative prefix removal...")

    # Prepare input dataframe with required columns
    # batch_clean_prefixes expects columns: 自然村, 村委会
    input_df = pd.DataFrame({
        '自然村': df_clean['自然村_基础清洗'].values,
        '村委会': df_clean[S.committee_col_raw].values
    })

    df_prefix_results = batch_clean_prefixes(
        input_df,
        min_length=2,
        confidence_threshold=0.7
    )

    # Merge results back
    df_combined = df_clean.copy()
    df_combined[S.village_name_col_prefix_removed] = df_prefix_results['自然村_去前缀'].values
    df_combined['有前缀'] = df_prefix_results['有前缀'].values
    df_combined['去除的前缀'] = df_prefix_results['去除的前缀'].values
    df_combined['前缀匹配来源'] = df_prefix_results['前缀匹配来源'].values
    df_combined['前缀置信度'] = df_prefix_results['前缀置信度'].values
    df_combined['需要审核'] = df_prefix_results['需要审核'].values

    # Step 3: Numbered village normalization
    logger.info("Step 3: Numbered village normalization...")
    normalization_results = []
    for idx, row in df_combined.iterrows():
        if idx % 10000 == 0:
            logger.info(f"  Progress: {idx}/{len(df_combined)}")

        has_numeral, base_name, numeral_suffix = detect_trailing_numeral(
            row[S.village_name_col_prefix_removed]
        )
        normalized = row[S.village_name_col_prefix_removed]

        normalization_results.append({
            '自然村_规范化': normalized,
            '有编号后缀': 1 if has_numeral else 0,
            '编号后缀': numeral_suffix
        })

    df_final = pd.concat([df_combined, pd.DataFrame(normalization_results)], axis=1)

    # Step 4: Extract character sets
    logger.info("Step 4: Extracting character sets...")
    char_sets = []
    for idx, row in df_final.iterrows():
        if idx % 10000 == 0:
            logger.info(f"  Progress: {idx}/{len(df_final)}")

        char_set = extract_char_set(row['自然村_规范化'])
        char_sets.append({
            S.char_set_col: json.dumps(list(char_set), ensure_ascii=False),
            S.char_count_col: len(char_set)
        })

    df_final = pd.concat([df_final, pd.DataFrame(char_sets)], axis=1)

    # Select only the 12 essential columns for the optimized table
    logger.info("Selecting essential columns for optimized table...")
    df_optimized = df_final[[
        S.city_col, S.county_col, S.township_col, S.committee_col_raw,
        '自然村_规范化', S.village_name_col_prefix_removed,
        S.longitude_col, S.latitude_col, S.language_col_raw,
        S.char_set_col, S.char_count_col
    ]].copy()

    # Rename: committee (行政村→村委会) and village name (自然村_规范化→自然村_规范名)
    rename_map = {S.committee_col_raw: S.committee_col_preprocessed,
                  '自然村_规范化': S.village_name_col_normalized}
    df_optimized = df_optimized.rename(columns=rename_map)

    # Add village_id column (will be populated after writing to database)
    df_optimized[S.village_id_col] = None

    # Write to database
    logger.info("Writing optimized table to database...")
    df_optimized.to_sql(S.preprocessed_table, conn, if_exists="replace", index=False)

    # Populate village_id using ROWID
    logger.info("Populating village_id...")
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE {S.preprocessed_table}
        SET {S.village_id_col} = 'v_' || ROWID
    """)
    conn.commit()
    logger.info("village_id populated successfully")

    # Materialize lightweight metadata tables for backend overview/regions APIs.
    logger.info("Materializing metadata stats...")
    materialize_metadata_stats(conn)

    # Verify
    cursor.execute(f"SELECT COUNT(*) FROM {S.preprocessed_table}")
    count = cursor.fetchone()[0]
    logger.info(f"Verification: {count} rows written")

    # Statistics
    total_count = len(df_final)
    valid_count = (df_final[S.char_count_col] > 0).sum()
    prefix_count = df_final[df_final[S.char_count_col] > 0]['有前缀'].sum()
    numbered_count = df_final[df_final[S.char_count_col] > 0]['有编号后缀'].sum()

    logger.info(f"\nPreprocessing Statistics:")
    logger.info(f"  Total villages: {total_count}")
    logger.info(f"  Valid villages ({S.char_count_col} > 0): {valid_count}")
    logger.info(f"  Prefixes removed: {prefix_count} ({100*prefix_count/valid_count:.1f}%)")
    logger.info(f"  Numbered villages: {numbered_count} ({100*numbered_count/valid_count:.1f}%)")

    conn.close()
    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
