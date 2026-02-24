"""
Generate village_features table from preprocessed data.

This script:
1. Creates the village_features table
2. Loads villages from the preprocessed table
3. Extracts features for each village
4. Writes features to the database
"""

import sqlite3
import logging
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.features.feature_extractor import VillageFeatureExtractor
from src.data.db_writer import create_feature_materialization_tables
from src.pipelines.feature_materialization_pipeline import write_village_features

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_villages_from_preprocessed(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load villages from preprocessed table.

    Args:
        conn: SQLite database connection

    Returns:
        DataFrame with village data
    """
    logger.info("Loading villages from preprocessed table")

    query = """
    SELECT
        市级 as city,
        区县级 as county,
        乡镇级 as town,
        村委会 as village_committee,
        自然村_去前缀 as village_name,
        village_id
    FROM 广东省自然村_预处理
    WHERE 自然村_去前缀 IS NOT NULL
    """

    df = pd.read_sql_query(query, conn)

    # Add pinyin column (empty for now, can be populated later if needed)
    df['pinyin'] = ''

    logger.info(f"Loaded {len(df)} villages")

    return df


def main():
    db_path = project_root / 'data' / 'villages.db'

    logger.info("=" * 80)
    logger.info("Generating village_features table")
    logger.info("=" * 80)
    logger.info(f"Database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(str(db_path))

    try:
        # Step 1: Create tables
        logger.info("Creating village_features table...")
        create_feature_materialization_tables(conn)
        logger.info("Table created successfully")

        # Step 2: Load villages
        df = load_villages_from_preprocessed(conn)

        # Step 3: Extract features
        logger.info("Extracting features...")
        lexicon_path = project_root / 'data' / 'semantic_lexicon_v1.json'
        extractor = VillageFeatureExtractor(str(lexicon_path))
        features_df = extractor.extract_batch(df, village_name_col='village_name')
        logger.info(f"Extracted features for {len(features_df)} villages")

        # Merge features with original data
        logger.info("Merging features with original data...")
        # Reset index to ensure proper merge
        df_reset = df.reset_index(drop=True)
        features_reset = features_df.reset_index(drop=True)

        # Combine the dataframes
        combined_df = pd.concat([df_reset, features_reset], axis=1)
        logger.info(f"Combined dataframe has {len(combined_df)} rows and {len(combined_df.columns)} columns")

        # Step 4: Write to database
        logger.info("Writing features to database...")

        # Prepare columns for insertion
        columns_to_write = [
            'village_id', 'city', 'county', 'town', 'village_committee', 'village_name', 'pinyin',
            'name_length', 'suffix_1', 'suffix_2', 'suffix_3', 'prefix_1', 'prefix_2', 'prefix_3',
            'sem_mountain', 'sem_water', 'sem_settlement', 'sem_direction', 'sem_clan',
            'sem_symbolic', 'sem_agriculture', 'sem_vegetation', 'sem_infrastructure',
            'has_valid_chars'
        ]

        # Add cluster columns if they exist (they won't for now)
        for col in ['kmeans_cluster_id', 'dbscan_cluster_id', 'gmm_cluster_id']:
            if col not in combined_df.columns:
                combined_df[col] = None

        # Filter to only include rows with village_id
        df_to_write = combined_df[combined_df['village_id'].notna()].copy()
        logger.info(f"Writing {len(df_to_write)} villages with valid village_id")

        # Write in batches
        cursor = conn.cursor()
        batch_size = 10000
        total_batches = (len(df_to_write) + batch_size - 1) // batch_size

        for i in range(0, len(df_to_write), batch_size):
            batch = df_to_write.iloc[i:i+batch_size]
            batch_num = i // batch_size + 1

            # Prepare values for insertion
            values = []
            for _, row in batch.iterrows():
                value_tuple = tuple(row[col] if col in row else None for col in columns_to_write + ['kmeans_cluster_id', 'dbscan_cluster_id', 'gmm_cluster_id'])
                values.append(value_tuple)

            # Insert batch
            placeholders = ','.join(['?' * len(columns_to_write + ['kmeans_cluster_id', 'dbscan_cluster_id', 'gmm_cluster_id'])])
            placeholders = '(' + ','.join(['?'] * len(columns_to_write + ['kmeans_cluster_id', 'dbscan_cluster_id', 'gmm_cluster_id'])) + ')'

            cursor.executemany(f"""
                INSERT OR REPLACE INTO village_features
                ({', '.join(columns_to_write + ['kmeans_cluster_id', 'dbscan_cluster_id', 'gmm_cluster_id'])})
                VALUES {placeholders}
            """, values)

            logger.info(f"Batch {batch_num}/{total_batches} written ({len(batch)} rows)")

        conn.commit()
        logger.info("Features written successfully")

        # Step 5: Verify
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM village_features")
        count = cursor.fetchone()[0]
        logger.info(f"Verification: village_features has {count} rows")

        logger.info("=" * 80)
        logger.info("village_features generation completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == '__main__':
    main()
