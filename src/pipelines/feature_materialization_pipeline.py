"""
Feature materialization pipeline.

Materializes village-level features into database for fast deployment queries.
"""

import sqlite3
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from src.features.feature_extractor import VillageFeatureExtractor
from src.data.db_writer import (
    create_feature_materialization_tables,
    create_feature_materialization_indexes
)
from src.pipelines.region_aggregation import compute_and_write_all_aggregates


logger = logging.getLogger(__name__)


def load_villages(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load all villages from database.

    Args:
        conn: SQLite database connection

    Returns:
        DataFrame with village data
    """
    logger.info("Loading villages from database")

    # Query all columns and rename them
    # Column order: 市级, 县区级, 乡镇, 村委会, 自然村, 拼音, 语言分布, longitude, latitude, 备注, 更新时间, 数据来源
    query = "SELECT * FROM 广东省自然村"

    df = pd.read_sql_query(query, conn)

    # Rename columns to English
    df.columns = ['city', 'county', 'town', 'village_committee', 'village_name', 'pinyin',
                  'language_distribution', 'longitude', 'latitude', 'notes', 'update_time', 'data_source']

    # Keep only needed columns
    df = df[['city', 'county', 'town', 'village_committee', 'village_name', 'pinyin']]

    logger.info(f"Loaded {len(df)} villages")

    return df


def load_cluster_assignments(conn: sqlite3.Connection, run_id: str) -> Dict[str, pd.DataFrame]:
    """
    Load cluster assignments from database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier for clustering results

    Returns:
        Dict mapping algorithm names to DataFrames with cluster assignments
    """
    logger.info(f"Loading cluster assignments for run_id={run_id}")

    assignments = {}

    # Try to load KMeans assignments
    try:
        query = """
            SELECT village_name, cluster_id
            FROM cluster_assignments
            WHERE run_id = ? AND algorithm = 'kmeans'
        """
        df = pd.read_sql_query(query, conn, params=(run_id,))
        if len(df) > 0:
            assignments['kmeans'] = df
            logger.info(f"Loaded {len(df)} KMeans assignments")
    except Exception as e:
        logger.warning(f"Could not load KMeans assignments: {e}")

    # Try to load DBSCAN assignments
    try:
        query = """
            SELECT village_name, cluster_id
            FROM cluster_assignments
            WHERE run_id = ? AND algorithm = 'dbscan'
        """
        df = pd.read_sql_query(query, conn, params=(run_id,))
        if len(df) > 0:
            assignments['dbscan'] = df
            logger.info(f"Loaded {len(df)} DBSCAN assignments")
    except Exception as e:
        logger.warning(f"Could not load DBSCAN assignments: {e}")

    # Try to load GMM assignments
    try:
        query = """
            SELECT village_name, cluster_id
            FROM cluster_assignments
            WHERE run_id = ? AND algorithm = 'gmm'
        """
        df = pd.read_sql_query(query, conn, params=(run_id,))
        if len(df) > 0:
            assignments['gmm'] = df
            logger.info(f"Loaded {len(df)} GMM assignments")
    except Exception as e:
        logger.warning(f"Could not load GMM assignments: {e}")

    return assignments


def merge_cluster_assignments(villages_df: pd.DataFrame, assignments: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Merge cluster assignments into villages DataFrame.

    Args:
        villages_df: DataFrame with village data
        assignments: Dict mapping algorithm names to assignment DataFrames

    Returns:
        DataFrame with cluster assignments merged
    """
    result_df = villages_df.copy()

    # Merge KMeans assignments
    if 'kmeans' in assignments:
        result_df = result_df.merge(
            assignments['kmeans'].rename(columns={'cluster_id': 'kmeans_cluster_id'}),
            on='village_name',
            how='left'
        )
    else:
        result_df['kmeans_cluster_id'] = None

    # Merge DBSCAN assignments
    if 'dbscan' in assignments:
        result_df = result_df.merge(
            assignments['dbscan'].rename(columns={'cluster_id': 'dbscan_cluster_id'}),
            on='village_name',
            how='left'
        )
    else:
        result_df['dbscan_cluster_id'] = None

    # Merge GMM assignments
    if 'gmm' in assignments:
        result_df = result_df.merge(
            assignments['gmm'].rename(columns={'cluster_id': 'gmm_cluster_id'}),
            on='village_name',
            how='left'
        )
    else:
        result_df['gmm_cluster_id'] = None

    return result_df


def write_village_features(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame, batch_size: int = 10000):
    """
    Write village features to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier (kept for backward compatibility, not used)
        df: DataFrame with village features
        batch_size: Batch size for insertion
    """
    # Filter out rows with NULL village names
    df = df[df['village_name'].notna()].copy()

    logger.info(f"Writing {len(df)} village features to database")

    # Get village_id mapping from preprocessed table
    logger.info("Loading village_id mapping from preprocessed table...")
    id_mapping_query = """
    SELECT
        市级, 区县级, 乡镇级, 村委会, 自然村_去前缀,
        village_id
    FROM 广东省自然村_预处理
    WHERE village_id IS NOT NULL
    """
    id_mapping = pd.read_sql(id_mapping_query, conn)

    # Merge village_id into features dataframe
    # Match on: city, county, town, village_committee, village_name
    df = df.merge(
        id_mapping,
        left_on=['city', 'county', 'town', 'village_committee', 'village_name'],
        right_on=['市级', '区县级', '乡镇级', '村委会', '自然村_去前缀'],
        how='left'
    )

    # Drop the Chinese column names from merge
    df = df.drop(columns=['市级', '区县级', '乡镇级', '村委会', '自然村_去前缀'], errors='ignore')

    # Check coverage
    null_count = df['village_id'].isna().sum()
    if null_count > 0:
        logger.warning(f"{null_count} villages could not be mapped to village_id")

    logger.info(f"Successfully mapped village_id for {len(df) - null_count} villages")

    cursor = conn.cursor()

    # Prepare data for insertion (now includes village_id, no run_id/created_at)
    columns = [
        'village_id', 'city', 'county', 'town', 'village_committee', 'village_name', 'pinyin',
        'name_length', 'suffix_1', 'suffix_2', 'suffix_3', 'prefix_1', 'prefix_2', 'prefix_3',
        'sem_mountain', 'sem_water', 'sem_settlement', 'sem_direction', 'sem_clan',
        'sem_symbolic', 'sem_agriculture', 'sem_vegetation', 'sem_infrastructure',
        'kmeans_cluster_id', 'dbscan_cluster_id', 'gmm_cluster_id',
        'has_valid_chars'
    ]

    # Insert in batches
    total_batches = (len(df) + batch_size - 1) // batch_size
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        batch_num = i // batch_size + 1

        # Prepare values
        values = []
        for _, row in batch.iterrows():
            values.append(tuple(row[col] if col in row else None for col in columns))

        # Insert
        placeholders = ','.join(['?' for _ in columns])
        cursor.executemany(f"""
            INSERT OR REPLACE INTO village_features
            ({','.join(columns)})
            VALUES ({placeholders})
        """, values)

        logger.info(f"Inserted batch {batch_num}/{total_batches}")

    conn.commit()
    logger.info(f"Successfully wrote {len(df)} village features")


def run_feature_materialization_pipeline(
    db_path: str,
    run_id: str,
    clustering_run_id: Optional[str] = None,
    lexicon_path: str = 'data/semantic_lexicon_v1.json',
    output_dir: Optional[str] = None
) -> Dict[str, any]:
    """
    Run feature materialization pipeline.

    Args:
        db_path: Path to SQLite database
        run_id: Run identifier for this materialization
        clustering_run_id: Run identifier for clustering results (optional)
        lexicon_path: Path to semantic lexicon JSON file
        output_dir: Output directory for CSV exports (optional)

    Returns:
        Dict with pipeline results and statistics
    """
    logger.info(f"Starting feature materialization pipeline: run_id={run_id}")
    start_time = time.time()

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Create tables
        logger.info("Creating feature materialization tables")
        create_feature_materialization_tables(conn)
        create_feature_materialization_indexes(conn)

        # Load villages
        villages_df = load_villages(conn)

        # Initialize feature extractor
        extractor = VillageFeatureExtractor(lexicon_path)

        # Extract features
        features_df = extractor.extract_batch(villages_df, village_name_col='village_name')

        # Combine with village data
        result_df = pd.concat([villages_df, features_df], axis=1)

        # Load and merge cluster assignments if provided
        if clustering_run_id:
            assignments = load_cluster_assignments(conn, clustering_run_id)
            result_df = merge_cluster_assignments(result_df, assignments)

        # Write to database
        write_village_features(conn, run_id, result_df)

        # Compute and write region aggregates
        logger.info("Computing region aggregates")
        compute_and_write_all_aggregates(conn, run_id)


        # Export CSV if output directory provided
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            csv_path = output_path / f"village_features_{run_id}.csv"
            result_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"Exported CSV to {csv_path}")

        # Calculate statistics
        stats = {
            'run_id': run_id,
            'total_villages': int(len(result_df)),
            'avg_name_length': float(result_df['name_length'].mean()),
            'semantic_tag_counts': {
                'mountain': int(result_df['sem_mountain'].sum()),
                'water': int(result_df['sem_water'].sum()),
                'settlement': int(result_df['sem_settlement'].sum()),
                'direction': int(result_df['sem_direction'].sum()),
                'clan': int(result_df['sem_clan'].sum()),
                'symbolic': int(result_df['sem_symbolic'].sum()),
                'agriculture': int(result_df['sem_agriculture'].sum()),
                'vegetation': int(result_df['sem_vegetation'].sum()),
                'infrastructure': int(result_df['sem_infrastructure'].sum())
            },
            'runtime_seconds': float(time.time() - start_time)
        }

        logger.info(f"Pipeline completed in {stats['runtime_seconds']:.2f} seconds")
        return stats

    finally:
        conn.close()



