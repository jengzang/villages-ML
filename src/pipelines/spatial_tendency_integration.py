"""
Spatial-Tendency Integration Pipeline.

Integrates character tendency analysis with spatial clustering to identify
geographic patterns in village naming preferences.

Extracted from scripts/experimental/spatial_tendency_integration.py and fixed
to read from char_regional_analysis (post-DB-optimization schema).
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from src.data.db_writer import (
    create_spatial_tendency_table,
    create_spatial_tendency_indexes,
    write_spatial_tendency_integration,
)

logger = logging.getLogger(__name__)


def load_tendency_results(
    conn: sqlite3.Connection,
    tendency_run_id: str,
    region_level: str = 'county'
) -> pd.DataFrame:
    """
    Load tendency analysis results from char_regional_analysis table.

    Args:
        conn: Database connection
        tendency_run_id: Run ID for tendency analysis (unused - table has no run_id)
        region_level: Region level ('city', 'county', 'township')

    Returns:
        DataFrame with tendency results including significance
    """
    logger.info(f"Loading tendency results from char_regional_analysis, level={region_level}")

    query = """
        SELECT
            region_name,
            char,
            frequency as regional_frequency,
            global_frequency,
            lift,
            log_lift,
            log_odds,
            z_score,
            village_count,
            total_villages,
            chi_square_statistic as p_value_tmp,
            p_value,
            is_significant,
            effect_size
        FROM char_regional_analysis
        WHERE region_level = ?
    """
    # Note: tendency_run_id is kept for API compatibility but char_regional_analysis
    # uses the optimized schema without run_id

    df = pd.read_sql_query(query, conn, params=[region_level])
    logger.info(f"Loaded {len(df)} tendency records")

    return df


def load_spatial_features(
    conn: sqlite3.Connection,
    spatial_run_id: str
) -> pd.DataFrame:
    """
    Load spatial features from database.

    Args:
        conn: Database connection
        spatial_run_id: Run ID for spatial analysis

    Returns:
        DataFrame with spatial features
    """
    logger.info(f"Loading spatial features for run_id={spatial_run_id}")

    query = """
        SELECT
            village_id,
            village_name,
            city,
            county,
            town,
            longitude,
            latitude,
            spatial_cluster_id,
            cluster_size,
            nn_distance_1,
            local_density_1km,
            isolation_score,
            is_isolated
        FROM village_spatial_features
        WHERE run_id = ?
    """

    df = pd.read_sql_query(query, conn, params=[spatial_run_id])
    logger.info(f"Loaded {len(df)} village spatial features")

    return df


def load_villages_with_chars(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load village data with character sets.

    Args:
        conn: Database connection

    Returns:
        DataFrame with village names and their character sets
    """
    logger.info("Loading village data with character sets")

    query = """
        SELECT
            ROWID as row_id,
            自然村_去前缀 as village_name,
            市级 as city,
            区县级 as county,
            乡镇级 as town
        FROM 广东省自然村_预处理
        WHERE 字符数量 > 0
    """

    df = pd.read_sql_query(query, conn)
    logger.info(f"Loaded {len(df)} villages")

    df['village_id'] = 'v_' + df['row_id'].astype(str)
    df = df.drop(columns=['row_id'])

    df['char_set'] = df['village_name'].apply(lambda x: set(x) if pd.notna(x) else set())

    return df


def calculate_spatial_coherence(coords: np.ndarray) -> float:
    """
    Calculate spatial coherence of a cluster.

    Coherence is measured as the inverse of the normalized standard deviation
    of distances from the centroid.

    Args:
        coords: Array of shape (n, 2) with [longitude, latitude]

    Returns:
        Coherence score (0-1, higher is more coherent)
    """
    if len(coords) < 2:
        return 1.0

    centroid = coords.mean(axis=0)
    distances = np.linalg.norm(coords - centroid, axis=1)
    std = distances.std()

    return 1 / (1 + std)


def integrate_spatial_tendency(
    tendency_df: pd.DataFrame,
    spatial_df: pd.DataFrame,
    villages_df: pd.DataFrame,
    character: str,
    tendency_run_id: str,
    spatial_run_id: str
) -> pd.DataFrame:
    """
    Integrate spatial and tendency data for a specific character.

    Args:
        tendency_df: Tendency analysis results
        spatial_df: Spatial features
        villages_df: Village data with character sets
        character: Character to analyze
        tendency_run_id: Tendency analysis run ID
        spatial_run_id: Spatial analysis run ID

    Returns:
        DataFrame with integrated results
    """
    logger.info(f"Integrating spatial-tendency data for character '{character}'")

    char_tendency = tendency_df[tendency_df['char'] == character].copy()

    if len(char_tendency) == 0:
        logger.warning(f"No tendency data found for character '{character}'")
        return pd.DataFrame()

    villages_with_char = villages_df[
        villages_df['char_set'].apply(lambda s: character in s)
    ].copy()

    logger.info(f"Found {len(villages_with_char)} villages with character '{character}'")

    char_spatial = villages_with_char.merge(
        spatial_df,
        on='village_id',
        how='inner',
        suffixes=('_village', '_spatial')
    )

    logger.info(f"Matched {len(char_spatial)} villages with spatial features")

    char_spatial = char_spatial[char_spatial['spatial_cluster_id'] != -1]

    logger.info(f"After removing noise: {len(char_spatial)} villages in clusters")

    if len(char_spatial) == 0:
        logger.warning(f"No villages with character '{character}' in spatial clusters")
        return pd.DataFrame()

    cluster_stats = []
    n_clusters = char_spatial['spatial_cluster_id'].nunique()
    logger.info(f"Processing {n_clusters} clusters...")

    for idx, (cluster_id, cluster_df) in enumerate(char_spatial.groupby('spatial_cluster_id')):
        if idx % 100 == 0:
            logger.info(f"  Processed {idx}/{n_clusters} clusters...")

        coords = cluster_df[['longitude', 'latitude']].values

        centroid_lon = coords[:, 0].mean()
        centroid_lat = coords[:, 1].mean()

        coherence = calculate_spatial_coherence(coords)

        city_mode = cluster_df['city_spatial'].mode()
        dominant_city = city_mode.iloc[0] if len(city_mode) > 0 else None

        county_mode = cluster_df['county_spatial'].mode()
        dominant_county = county_mode.iloc[0] if len(county_mode) > 0 else None

        region_tendency = char_tendency[char_tendency['region_name'] == dominant_county]

        if len(region_tendency) > 0:
            tendency_mean = region_tendency['lift'].mean()
            p_value = region_tendency['p_value'].mean() if 'p_value' in region_tendency.columns else None
            is_significant = region_tendency['is_significant'].any() if 'is_significant' in region_tendency.columns else False
        else:
            tendency_mean = None
            p_value = None
            is_significant = False

        if len(coords) > 1:
            centroid = np.array([centroid_lon, centroid_lat])
            distances_from_centroid = np.linalg.norm(coords - centroid, axis=1) * 111
            avg_distance_km = distances_from_centroid.mean()
        else:
            avg_distance_km = 0

        cluster_stats.append({
            'tendency_run_id': tendency_run_id,
            'spatial_run_id': spatial_run_id,
            'character': character,
            'cluster_id': int(cluster_id),
            'cluster_size': int(cluster_df['cluster_size'].iloc[0]),
            'n_villages_with_char': len(cluster_df),
            'cluster_tendency_mean': tendency_mean,
            'cluster_tendency_std': None,
            'centroid_lon': centroid_lon,
            'centroid_lat': centroid_lat,
            'avg_distance_km': avg_distance_km,
            'spatial_coherence': coherence,
            'dominant_city': dominant_city,
            'dominant_county': dominant_county,
            'is_significant': is_significant,
            'avg_p_value': p_value
        })

    result_df = pd.DataFrame(cluster_stats)
    logger.info(f"Generated {len(result_df)} cluster-level integration records")

    return result_df


def run_integration(
    db_path: str,
    tendency_run_id: str,
    spatial_run_id: str,
    output_run_id: str,
    characters: List[str],
    region_level: str = 'county'
) -> pd.DataFrame:
    """
    Run spatial-tendency integration for a list of characters.

    Args:
        db_path: Path to database
        tendency_run_id: Run ID for tendency analysis
        spatial_run_id: Run ID for spatial analysis
        output_run_id: Run ID for this integration output
        characters: List of characters to analyze
        region_level: Region level for tendency analysis

    Returns:
        Combined DataFrame with all integration results
    """
    logger.info(f"Starting spatial-tendency integration for {len(characters)} character(s)")
    logger.info(f"Tendency run: {tendency_run_id}")
    logger.info(f"Spatial run: {spatial_run_id}")
    logger.info(f"Output run: {output_run_id}")

    start_time = time.time()

    conn = sqlite3.connect(db_path)

    try:
        create_spatial_tendency_table(conn)
        create_spatial_tendency_indexes(conn)

        logger.info("Loading tendency results...")
        tendency_df = load_tendency_results(conn, tendency_run_id, region_level)

        logger.info("Loading spatial features...")
        spatial_df = load_spatial_features(conn, spatial_run_id)

        logger.info("Loading village data...")
        villages_df = load_villages_with_chars(conn)

        all_results = []

        for char in characters:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing character: {char}")
            logger.info(f"{'='*60}")

            result_df = integrate_spatial_tendency(
                tendency_df=tendency_df,
                spatial_df=spatial_df,
                villages_df=villages_df,
                character=char,
                tendency_run_id=tendency_run_id,
                spatial_run_id=spatial_run_id
            )

            if len(result_df) > 0:
                all_results.append(result_df)

        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            logger.info(f"\nTotal integration records: {len(combined_df)}")

            logger.info("Writing results to database...")
            write_spatial_tendency_integration(conn, output_run_id, combined_df)

            elapsed = time.time() - start_time
            logger.info(f"\nIntegration completed in {elapsed:.2f}s")
            logger.info(f"Characters analyzed: {len(characters)}")
            logger.info(f"Total clusters: {combined_df['cluster_id'].nunique()}")
            logger.info(f"Total records: {len(combined_df)}")

            return combined_df
        else:
            logger.warning("No integration results generated")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error during integration: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def get_top_characters(conn: sqlite3.Connection, n: int = 100) -> List[str]:
    """
    Get the top N most frequent characters from char_regional_analysis.

    Args:
        conn: Database connection
        n: Number of top characters to return

    Returns:
        List of characters
    """
    query = """
        SELECT char
        FROM char_regional_analysis
        GROUP BY char
        ORDER BY SUM(village_count) DESC
        LIMIT ?
    """
    results = conn.execute(query, (n,)).fetchall()
    return [r[0] for r in results]
