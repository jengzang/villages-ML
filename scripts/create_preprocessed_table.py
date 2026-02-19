"""Create preprocessed village table with prefix cleaning and normalization.

This script:
1. Loads raw village data
2. Applies basic text cleaning (brackets, noise)
3. Applies administrative prefix removal
4. Applies numbered village normalization
5. Extracts character sets
6. Stores results in 广东省自然村_预处理 table
"""

import sqlite3
import logging
import json
from pathlib import Path
import pandas as pd
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.text_cleaner import normalize_village_name
from preprocessing.prefix_cleaner import batch_clean_prefixes
from preprocessing.numbered_village_normalizer import (
    normalize_numbered_village,
    detect_trailing_numeral
)
from preprocessing.char_extractor import extract_char_set

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_preprocessed_table(conn: sqlite3.Connection):
    """Create the preprocessed table schema."""
    cursor = conn.cursor()

    # Drop if exists
    cursor.execute("DROP TABLE IF EXISTS 广东省自然村_预处理")

    # Create table
    cursor.execute("""
    CREATE TABLE 广东省自然村_预处理 (
        -- Original fields
        市级 TEXT,
        区县级 TEXT,
        乡镇级 TEXT,
        行政村 TEXT,
        自然村 TEXT,
        拼音 TEXT,
        语言分布 TEXT,
        longitude TEXT,
        latitude TEXT,
        备注 TEXT,
        更新时间 REAL,
        数据来源 TEXT,

        -- Preprocessing fields
        自然村_基础清洗 TEXT,
        自然村_去前缀 TEXT,
        自然村_规范化 TEXT,
        字符集 TEXT,
        字符数量 INTEGER,

        -- Cleaning metadata
        有括号 INTEGER,
        有噪音 INTEGER,
        有前缀 INTEGER,
        去除的前缀 TEXT,
        前缀匹配来源 TEXT,
        前缀置信度 REAL,
        有编号后缀 INTEGER,
        编号后缀 TEXT,

        -- Validity
        有效 INTEGER,
        无效原因 TEXT
    )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX idx_prep_city ON 广东省自然村_预处理(市级)")
    cursor.execute("CREATE INDEX idx_prep_county ON 广东省自然村_预处理(区县级)")
    cursor.execute("CREATE INDEX idx_prep_township ON 广东省自然村_预处理(乡镇级)")
    cursor.execute("CREATE INDEX idx_prep_admin ON 广东省自然村_预处理(行政村)")
    cursor.execute("CREATE INDEX idx_prep_prefix ON 广东省自然村_预处理(有前缀)")
    cursor.execute("CREATE INDEX idx_prep_valid ON 广东省自然村_预处理(有效)")

    conn.commit()
    logger.info("Created preprocessed table schema")


def main():
    """Main preprocessing pipeline."""
    db_path = Path(__file__).parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Create preprocessed table
    create_preprocessed_table(conn)

    # Load raw data
    logger.info("Loading raw village data...")
    # Use SELECT * to avoid encoding issues with column names
    query = "SELECT * FROM 广东省自然村"
    df = pd.read_sql(query, conn)
    logger.info(f"Loaded {len(df)} villages")

    # Rename columns to avoid encoding issues
    df.columns = ['市级', '区县级', '乡镇级', '行政村', '自然村', '拼音', '语言分布',
                  'longitude', 'latitude', '备注', '更新时间', '数据来源']

    # Step 1: Basic text cleaning
    logger.info("Step 1: Basic text cleaning...")
    cleaning_results = []
    for idx, row in df.iterrows():
        if idx % 10000 == 0:
            logger.info(f"  Progress: {idx}/{len(df)}")

        cleaned = normalize_village_name(row['自然村'])
        cleaning_results.append({
            '自然村_基础清洗': cleaned.clean_name,
            '有括号': 1 if cleaned.had_brackets else 0,
            '有噪音': 1 if cleaned.had_noise else 0,
            '有效': 1 if cleaned.is_valid else 0,
            '无效原因': cleaned.invalid_reason
        })

    df_clean = pd.concat([df, pd.DataFrame(cleaning_results)], axis=1)

    # Step 2: Administrative prefix removal
    logger.info("Step 2: Administrative prefix removal...")
    # Select only valid rows
    valid_df = df_clean[df_clean['有效'] == 1].copy()

    # Prepare input dataframe with required columns
    # batch_clean_prefixes expects columns: 自然村, 行政村
    input_df = pd.DataFrame({
        '自然村': valid_df['自然村_基础清洗'].values,
        '行政村': valid_df['行政村'].values
    })

    df_prefix_results = batch_clean_prefixes(
        input_df,
        min_length=2,  # Changed from 3 to 2 to match new implementation
        confidence_threshold=0.7
    )

    # Merge results back with original valid rows
    df_prefix = valid_df.copy()
    df_prefix['自然村_去前缀'] = df_prefix_results['自然村_去前缀'].values
    df_prefix['有前缀'] = df_prefix_results['有前缀'].values
    df_prefix['去除的前缀'] = df_prefix_results['去除的前缀'].values
    df_prefix['前缀匹配来源'] = df_prefix_results['前缀匹配来源'].values
    df_prefix['前缀置信度'] = df_prefix_results['前缀置信度'].values
    df_prefix['需要审核'] = df_prefix_results['需要审核'].values

    # Merge back with invalid rows
    df_invalid = df_clean[df_clean['有效'] == 0].copy()
    df_invalid['自然村_去前缀'] = df_invalid['自然村_基础清洗']
    df_invalid['有前缀'] = 0
    df_invalid['去除的前缀'] = ""
    df_invalid['前缀匹配来源'] = "invalid"
    df_invalid['前缀置信度'] = 0.0
    df_invalid['需要审核'] = 0

    df_combined = pd.concat([df_prefix, df_invalid], ignore_index=True)

    # Step 3: Numbered village normalization
    logger.info("Step 3: Numbered village normalization...")
    normalization_results = []
    for idx, row in df_combined.iterrows():
        if idx % 10000 == 0:
            logger.info(f"  Progress: {idx}/{len(df_combined)}")

        has_numeral, base_name, numeral_suffix = detect_trailing_numeral(
            row['自然村_去前缀']
        )
        normalized = normalize_numbered_village(row['自然村_去前缀'])

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

        if row['有效'] == 1:
            char_set = extract_char_set(row['自然村_规范化'])
            char_sets.append({
                '字符集': json.dumps(list(char_set), ensure_ascii=False),
                '字符数量': len(char_set)
            })
        else:
            char_sets.append({
                '字符集': "[]",
                '字符数量': 0
            })

    df_final = pd.concat([df_final, pd.DataFrame(char_sets)], axis=1)

    # Write to database
    logger.info("Writing to database...")
    df_final.to_sql("广东省自然村_预处理", conn, if_exists="replace", index=False)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村_预处理")
    count = cursor.fetchone()[0]
    logger.info(f"Verification: {count} rows written")

    # Statistics
    cursor.execute("SELECT SUM(有前缀) FROM 广东省自然村_预处理 WHERE 有效=1")
    prefix_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM 广东省自然村_预处理 WHERE 有效=1")
    valid_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(有编号后缀) FROM 广东省自然村_预处理 WHERE 有效=1")
    numbered_count = cursor.fetchone()[0] or 0

    logger.info(f"\nPreprocessing Statistics:")
    logger.info(f"  Total villages: {count}")
    logger.info(f"  Valid villages: {valid_count}")
    logger.info(f"  Prefixes removed: {prefix_count} ({100*prefix_count/valid_count:.1f}%)")
    logger.info(f"  Numbered villages: {numbered_count} ({100*numbered_count/valid_count:.1f}%)")

    conn.close()
    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
