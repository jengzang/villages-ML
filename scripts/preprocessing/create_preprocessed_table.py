"""Create preprocessed village table.

This script:
1. Loads raw village data (prefix/suffix cleaned and admin-updated)
2. Applies basic text cleaning (brackets, noise)
3. Computes character counts
4. Stores results in preprocessed table

Steps 2 (prefix removal) and 3 (numbered normalization) are skipped:
prefix/suffix cleaning and admin reassignment are done manually on the raw table.
"""

import sqlite3
import logging
import json
import time
import argparse
from pathlib import Path
import pandas as pd
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.schema import REGION_LEVELS, VillageTableSchema, get_schema
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


def parse_args():
    parser = argparse.ArgumentParser(description="Create preprocessed village table")
    parser.add_argument(
        "--db-path",
        default=str(project_root / "data" / "villages.db"),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--schema",
        default="guangdong",
        choices=["guangdong", "national"],
        help="Village table schema",
    )
    parser.add_argument(
        "--prefix-min-length",
        type=int,
        default=2,
        help="Minimum removable administrative prefix length",
    )
    parser.add_argument(
        "--prefix-confidence-threshold",
        type=float,
        default=0.7,
        help="Confidence threshold for administrative prefix removal",
    )
    parser.add_argument(
        "--metadata-version",
        default="phase0_preprocessing",
        help="Data version stored in metadata materialization tables",
    )
    parser.add_argument(
        "--include-admin-villages",
        action="store_true",
        default=False,
        help="Include deduplicated admin village names as additional rows",
    )
    return parser.parse_args()


def _clean_admin_name(name: str) -> str:
    """Strip administrative suffixes from an admin village name."""
    ADMIN_SUFFIXES = [
        "社区居民委员会", "村民委员会", "居民委员会", "社区居委会",
        "村委会", "居委会", "行政村", "管理区", "社区", "村",
    ]
    for sfx in sorted(ADMIN_SUFFIXES, key=len, reverse=True):
        if name.endswith(sfx) and len(name) > len(sfx):
            core = name[:-len(sfx)]
            if len(core) >= 2:
                return core
    return name


def _insert_admin_village_rows(conn, S):
    """Insert deduplicated admin village names as additional rows.

    Admin rows have 村委会=NULL and coordinates=NULL, so they
    naturally participate in character-level analysis but are
    excluded from village-level and spatial analysis.
    """
    cursor = conn.cursor()

    # Get unique admin names per township from the raw table
    cursor.execute(f"""
        SELECT DISTINCT {S.city_col}, {S.county_col}, {S.township_col}, {S.committee_col_raw}
        FROM {S.raw_table}
        WHERE {S.committee_col_raw} IS NOT NULL AND {S.committee_col_raw} != ''
    """)

    admin_names = cursor.fetchall()
    logger.info(f"Found {len(admin_names)} unique admin village names")

    inserted = 0
    for city, county, township, admin_name in admin_names:
        cleaned = _clean_admin_name(admin_name)
        char_set = extract_char_set(cleaned)

        cursor.execute(f"""
            INSERT INTO {S.preprocessed_table} (
                {S.city_col}, {S.county_col}, {S.township_col},
                {S.committee_col_preprocessed},
                {S.village_name_col_prefix_removed},
                {S.longitude_col}, {S.latitude_col},
                {S.char_count_col}
            ) VALUES (?, ?, ?, NULL, ?, NULL, NULL, ?)
        """, (city, county, township, cleaned, len(char_set)))

        inserted += 1

    conn.commit()
    logger.info(f"Inserted {inserted} admin village rows")


def materialize_metadata_stats(
    conn: sqlite3.Connection,
    data_version: str = "phase0_preprocessing",
    schema: VillageTableSchema | None = None,
):
    """Materialize small metadata tables for overview and region list APIs."""
    S = schema or get_schema("guangdong")
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
        SELECT {S.village_name_col_prefix_removed}
        FROM {S.preprocessed_table}
        WHERE {S.village_name_col_prefix_removed} IS NOT NULL AND {S.village_name_col_prefix_removed} != ''
    """)
    for (name,) in cursor.fetchall():
        unique_chars.update(c for c in name if '一' <= c <= '鿿')

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
            '{REGION_LEVELS[0]}',
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
            '{REGION_LEVELS[1]}',
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
            '{REGION_LEVELS[2]}',
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

    cursor.execute("DROP TABLE IF EXISTS regional_basic_stats")
    cursor.execute("""
    CREATE TABLE regional_basic_stats (
        region_key TEXT PRIMARY KEY,
        region_level TEXT NOT NULL,
        region_name TEXT NOT NULL,
        city TEXT,
        county TEXT,
        township TEXT,
        village_count INTEGER NOT NULL,
        avg_name_length REAL,
        generated_at REAL NOT NULL,
        data_version TEXT NOT NULL
    )
    """)

    cursor.execute(f"""
        INSERT INTO regional_basic_stats (
            region_key, region_level, region_name, city, county, township,
            village_count, avg_name_length, generated_at, data_version
        )
        SELECT
            '{REGION_LEVELS[0]}|' || {S.city_col},
            '{REGION_LEVELS[0]}',
            {S.city_col},
            {S.city_col},
            NULL,
            NULL,
            COUNT(*),
            AVG(LENGTH({S.village_name_col_prefix_removed})),
            ?,
            ?
        FROM {S.preprocessed_table}
        WHERE {S.city_col} IS NOT NULL AND {S.city_col} != ''
        GROUP BY {S.city_col}
    """, (generated_at, data_version))

    cursor.execute(f"""
        INSERT INTO regional_basic_stats (
            region_key, region_level, region_name, city, county, township,
            village_count, avg_name_length, generated_at, data_version
        )
        SELECT
            '{REGION_LEVELS[1]}|' || {S.city_col} || '|' || {S.county_col},
            '{REGION_LEVELS[1]}',
            {S.county_col},
            {S.city_col},
            {S.county_col},
            NULL,
            COUNT(*),
            AVG(LENGTH({S.village_name_col_prefix_removed})),
            ?,
            ?
        FROM {S.preprocessed_table}
        WHERE {S.county_col} IS NOT NULL AND {S.county_col} != ''
        GROUP BY {S.city_col}, {S.county_col}
    """, (generated_at, data_version))

    cursor.execute(f"""
        INSERT INTO regional_basic_stats (
            region_key, region_level, region_name, city, county, township,
            village_count, avg_name_length, generated_at, data_version
        )
        SELECT
            '{REGION_LEVELS[2]}|' || {S.city_col} || '|' || {S.county_col} || '|' || {S.township_col},
            '{REGION_LEVELS[2]}',
            {S.township_col},
            {S.city_col},
            {S.county_col},
            {S.township_col},
            COUNT(*),
            AVG(LENGTH({S.village_name_col_prefix_removed})),
            ?,
            ?
        FROM {S.preprocessed_table}
        WHERE {S.township_col} IS NOT NULL AND {S.township_col} != ''
        GROUP BY {S.city_col}, {S.county_col}, {S.township_col}
    """, (generated_at, data_version))

    cursor.execute(
        "CREATE INDEX idx_regional_basic_stats_level_count ON regional_basic_stats(region_level, village_count DESC)"
    )
    cursor.execute(
        "CREATE INDEX idx_regional_basic_stats_lookup ON regional_basic_stats(region_level, region_name)"
    )

    conn.commit()
    logger.info("Materialized metadata_overview_stats, region_hierarchy_stats, and regional_basic_stats")


def create_preprocessed_table(conn: sqlite3.Connection, schema: VillageTableSchema | None = None):
    """Create the preprocessed table schema (optimized with only 12 essential columns)."""
    S = schema or get_schema("guangdong")
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
        {S.village_name_col_prefix_removed} TEXT,
        {S.longitude_col} REAL,
        {S.latitude_col} REAL,
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
    logger.info(f"Created optimized preprocessed table schema (9 columns)")


def main():
    """Main preprocessing pipeline."""
    args = parse_args()
    S = get_schema(args.schema)
    db_path = Path(args.db_path)

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Create preprocessed table
    create_preprocessed_table(conn, schema=S)

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

    # Skip Step 2 & 3: administrative prefix removal and numbered village
    # normalization have been done manually on the raw table.
    # Use the cleaned natural village name directly.
    df_combined = df_clean.copy()
    df_combined[S.village_name_col_prefix_removed] = df_clean['自然村_基础清洗']

    # Step 2 (original): Administrative prefix removal
    # --- COMMENTED OUT: prefixes cleaned manually on raw table ---
    # logger.info("Step 2: Administrative prefix removal...")
    # input_df = pd.DataFrame({
    #     '自然村': df_clean['自然村_基础清洗'].values,
    #     '村委会': df_clean[S.committee_col_raw].values
    # })
    # df_prefix_results = batch_clean_prefixes(
    #     input_df,
    #     min_length=args.prefix_min_length,
    #     confidence_threshold=args.prefix_confidence_threshold
    # )
    # df_combined[S.village_name_col_prefix_removed] = df_prefix_results['自然村_去前缀'].values
    # df_combined['有前缀'] = df_prefix_results['有前缀'].values
    # df_combined['去除的前缀'] = df_prefix_results['去除的前缀'].values
    # df_combined['前缀匹配来源'] = df_prefix_results['前缀匹配来源'].values
    # df_combined['前缀置信度'] = df_prefix_results['前缀置信度'].values
    # df_combined['需要审核'] = df_prefix_results['需要审核'].values

    # Step 3 (original): Numbered village normalization
    # --- COMMENTED OUT: normalization was a no-op ---
    # logger.info("Step 3: Numbered village normalization...")
    # normalization_results = []
    # for idx, row in df_combined.iterrows():
    #     if idx % 10000 == 0:
    #         logger.info(f"  Progress: {idx}/{len(df_combined)}")
    #     has_numeral, base_name, numeral_suffix = detect_trailing_numeral(
    #         row[S.village_name_col_prefix_removed]
    #     )
    #     normalized = row[S.village_name_col_prefix_removed]
    #     normalization_results.append({
    #         '自然村_规范化': normalized,
    #         '有编号后缀': 1 if has_numeral else 0,
    #         '编号后缀': numeral_suffix
    #     })
    # df_combined = pd.concat([df_combined, pd.DataFrame(normalization_results)], axis=1)

    # Step 4: Extract character count
    logger.info("Step 4: Computing character counts...")
    char_counts = []
    for idx, row in df_combined.iterrows():
        if idx % 10000 == 0:
            logger.info(f"  Progress: {idx}/{len(df_combined)}")

        char_set = extract_char_set(row[S.village_name_col_prefix_removed])
        char_counts.append({
            S.char_count_col: len(char_set)
        })

    df_final = pd.concat([df_combined, pd.DataFrame(char_counts)], axis=1)

    # Select only the 9 essential columns for the optimized table
    logger.info("Selecting essential columns for optimized table...")
    df_optimized = df_final[[
        S.city_col, S.county_col, S.township_col, S.committee_col_raw,
        S.village_name_col_prefix_removed,
        S.longitude_col, S.latitude_col,
        S.char_count_col
    ]].copy()

    # Rename committee (行政村→村委会)
    rename_map = {S.committee_col_raw: S.committee_col_preprocessed}
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

    # Optionally include admin village names for character-level analysis
    if args.include_admin_villages:
        logger.info("Including admin village names...")
        _insert_admin_village_rows(conn, S)

    # Materialize lightweight metadata tables for backend overview/regions APIs.
    logger.info("Materializing metadata stats...")
    materialize_metadata_stats(conn, data_version=args.metadata_version, schema=S)

    # Verify
    cursor.execute(f"SELECT COUNT(*) FROM {S.preprocessed_table}")
    count = cursor.fetchone()[0]
    logger.info(f"Verification: {count} rows written")

    # Statistics
    total_count = len(df_final)
    valid_count = (df_final[S.char_count_col] > 0).sum()

    logger.info(f"\nPreprocessing Statistics:")
    logger.info(f"  Total villages: {total_count}")
    logger.info(f"  Valid villages ({S.char_count_col} > 0): {valid_count}")

    conn.close()
    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
