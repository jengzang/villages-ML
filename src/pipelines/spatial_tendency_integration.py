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
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.schema import REGION_LEVELS, DEFAULT_SCHEMA
from src.data.db_writer import (
    create_spatial_tendency_table,
    create_spatial_tendency_indexes,
    write_spatial_tendency_integration,
)

logger = logging.getLogger(__name__)


def _load_char_category_map(conn: sqlite3.Connection) -> Dict[str, str]:
    """Load character→category mapping from semantic_subcategory_labels."""
    try:
        cursor = conn.execute("""
            SELECT char, parent_category FROM semantic_subcategory_labels
        """)
        return {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        return {}


def load_tendency_results(
    conn: sqlite3.Connection,
    tendency_run_id: str,
    region_level: str = REGION_LEVELS[1]
) -> pd.DataFrame:
    """
    Load tendency analysis results from char_regional_analysis table.

    Args:
        conn: Database connection
        tendency_run_id: Run ID for tendency analysis (unused - table has no run_id)
        region_level: Region level (REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2])

    Returns:
        DataFrame with tendency results including significance (if available)
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
            p_value,
            is_significant
        FROM char_regional_analysis
        WHERE region_level = ?
    """
    # Note: p_value / is_significant are populated by Phase 10 ALTER TABLE
    # and may be NULL for runs that haven't had significance computed yet.

    try:
        df = pd.read_sql_query(query, conn, params=[region_level])
    except (sqlite3.OperationalError, pd.errors.DatabaseError) as e:
        if "no such column" in str(e).lower():
            # Fall back to query without significance columns (pre-Phase-10)
            logger.warning("p_value/is_significant columns not found — loading without significance")
            query = """
                SELECT
                    region_name, char,
                    frequency as regional_frequency, global_frequency,
                    lift, log_lift, log_odds, z_score,
                    village_count, total_villages
                FROM char_regional_analysis
                WHERE region_level = ?
            """
            df = pd.read_sql_query(query, conn, params=[region_level])
        elif "no such table" in str(e).lower():
            logger.warning("char_regional_analysis not found — run Phase 2 first")
            return pd.DataFrame()
        else:
            raise

    logger.info(f"Loaded {len(df)} tendency records")

    return df


def load_spatial_features(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load spatial features from database (optimized schema without run_id).

    Args:
        conn: Database connection

    Returns:
        DataFrame with spatial features
    """
    logger.info("Loading spatial features from village_spatial_features")

    query = f"""
        SELECT
            village_id,
            village_name,
            city,
            county,
            {REGION_LEVELS[2]},
            longitude,
            latitude,
            spatial_cluster_id,
            cluster_size,
            nn_distance_1,
            local_density_1km,
            isolation_score,
            is_isolated
        FROM village_spatial_features
    """

    df = pd.read_sql_query(query, conn)
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

    S = DEFAULT_SCHEMA
    query = f"""
        SELECT
            ROWID as row_id,
            {S.village_name_col_prefix_removed} as village_name,
            {S.city_col} as city,
            {S.county_col} as county,
            {S.township_col} as {REGION_LEVELS[2]}
        FROM {S.preprocessed_table}
        WHERE {S.char_count_col} > 0
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
    spatial_run_id: str,
    global_tendency: Optional[float] = None,
    char_category: Optional[str] = None,
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
        global_tendency: Global mean lift for this character (across all regions)
        char_category: Semantic category label for this character

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

    # Global ratio for spatial_specificity
    total_village_count = len(villages_df)
    global_char_count = len(villages_with_char)
    global_ratio = global_char_count / total_village_count if total_village_count > 0 else 0.0

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

        # tendency_deviation
        tendency_deviation = None
        if tendency_mean is not None and global_tendency is not None:
            tendency_deviation = tendency_mean - global_tendency

        # spatial_specificity: local_ratio / global_ratio
        cluster_total = int(cluster_df['cluster_size'].iloc[0])
        n_char = len(cluster_df)
        local_ratio = n_char / cluster_total if cluster_total > 0 else 0.0
        spatial_specificity = local_ratio / global_ratio if global_ratio > 0 else None

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
            'character_category': char_category,
            'cluster_id': int(cluster_id),
            'cluster_size': cluster_total,
            'n_villages_with_char': n_char,
            'cluster_tendency_mean': tendency_mean,
            'cluster_tendency_std': None,
            'global_tendency_mean': global_tendency,
            'tendency_deviation': tendency_deviation,
            'centroid_lon': centroid_lon,
            'centroid_lat': centroid_lat,
            'avg_distance_km': avg_distance_km,
            'spatial_coherence': coherence,
            'spatial_specificity': spatial_specificity,
            'dominant_city': dominant_city,
            'dominant_county': dominant_county,
            'is_significant': is_significant,
            'p_value': p_value,
            'u_statistic': None,
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
    region_level: str = REGION_LEVELS[1]
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

        # Pre-compute global_tendency_mean per character
        logger.info("Computing global tendency means...")
        global_tendency_map = {}
        if len(tendency_df) > 0:
            global_means = tendency_df.groupby('char')['lift'].mean()
            global_tendency_map = global_means.to_dict()

        # Load character→category map
        char_category_map = _load_char_category_map(conn)

        logger.info("Loading spatial features...")
        spatial_df = load_spatial_features(conn)

        logger.info("Loading village data...")
        villages_df = load_villages_with_chars(conn)

        all_results = []

        for char in characters:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing character: {char}")
            logger.info(f"{'='*60}")

            global_tend = global_tendency_map.get(char)
            char_cat = char_category_map.get(char)

            result_df = integrate_spatial_tendency(
                tendency_df=tendency_df,
                spatial_df=spatial_df,
                villages_df=villages_df,
                character=char,
                tendency_run_id=tendency_run_id,
                spatial_run_id=spatial_run_id,
                global_tendency=global_tend,
                char_category=char_cat,
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
