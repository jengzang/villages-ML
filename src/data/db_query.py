"""
Database query module for retrieving frequency analysis results.

This module provides convenient query interfaces for:
- Global character frequency
- Regional character frequency
- Regional tendency analysis
- Character tendency across regions
- Top polarized characters
"""

import sqlite3
import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


def get_latest_run_id(conn: sqlite3.Connection) -> Optional[str]:
    """
    Get the most recent run_id from analysis_runs table.

    Args:
        conn: SQLite database connection

    Returns:
        Latest run_id or None if no runs exist
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT run_id FROM analysis_runs
        ORDER BY created_at DESC
        LIMIT 1
    """)
    result = cursor.fetchone()
    return result[0] if result else None


def get_global_frequency(conn: sqlite3.Connection, run_id: str,
                        top_n: Optional[int] = None) -> pd.DataFrame:
    """
    Query global character frequency.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        top_n: Limit to top N characters by frequency (optional)

    Returns:
        DataFrame with global frequency data
    """
    query = """
        SELECT char, village_count, total_villages, frequency, rank
        FROM char_frequency_global
        WHERE run_id = ?
        ORDER BY rank
    """

    if top_n:
        query += f" LIMIT {top_n}"

    return pd.read_sql_query(query, conn, params=(run_id,))


def get_regional_frequency(conn: sqlite3.Connection, run_id: str,
                          region_level: str, region_name: Optional[str] = None,
                          top_n: Optional[int] = None) -> pd.DataFrame:
    """
    Query regional character frequency.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        region_level: Region level ('city', 'county', 'township')
        region_name: Specific region name (optional, returns all if None)
        top_n: Limit to top N characters by frequency (optional)

    Returns:
        DataFrame with regional frequency data
    """
    if region_name:
        query = """
            SELECT region_name, char, village_count, total_villages, frequency, rank_within_region
            FROM char_frequency_regional
            WHERE run_id = ? AND region_level = ? AND region_name = ?
            ORDER BY rank_within_region
        """
        params = (run_id, region_level, region_name)
    else:
        query = """
            SELECT region_name, char, village_count, total_villages, frequency, rank_within_region
            FROM char_frequency_regional
            WHERE run_id = ? AND region_level = ?
            ORDER BY region_name, rank_within_region
        """
        params = (run_id, region_level)

    if top_n and region_name:
        query += f" LIMIT {top_n}"

    return pd.read_sql_query(query, conn, params=params)


def get_char_tendency_by_region(conn: sqlite3.Connection, run_id: str,
                                char: str, region_level: str) -> pd.DataFrame:
    """
    Query a specific character's tendency across all regions at a given level.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        char: Character to query
        region_level: Region level ('city', 'county', 'township')

    Returns:
        DataFrame with tendency data for the character across regions
    """
    query = """
        SELECT char, region_name, frequency, global_frequency, lift, log_lift, log_odds, z_score,
               village_count, total_villages, support_flag
        FROM regional_tendency
        WHERE run_id = ? AND char = ? AND region_level = ?
        ORDER BY lift DESC
    """

    return pd.read_sql_query(query, conn, params=(run_id, char, region_level))


def get_top_polarized_chars(conn: sqlite3.Connection, run_id: str,
                            region_level: str, top_n: int = 20,
                            metric: str = 'log_odds') -> pd.DataFrame:
    """
    Query the most polarized characters (highest absolute tendency values).

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        region_level: Region level ('city', 'county', 'township')
        top_n: Number of top characters to return
        metric: Metric to use ('log_odds', 'log_lift', 'z_score')

    Returns:
        DataFrame with top polarized characters
    """
    if metric not in ['log_odds', 'log_lift', 'z_score']:
        raise ValueError(f"Invalid metric: {metric}. Must be one of: log_odds, log_lift, z_score")

    query = f"""
        SELECT char, region_name, frequency, global_frequency, lift, log_lift, log_odds, z_score,
               village_count, total_villages
        FROM regional_tendency
        WHERE run_id = ? AND region_level = ? AND support_flag = 1
        ORDER BY ABS({metric}) DESC
        LIMIT ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, region_level, top_n))


def get_region_tendency_profile(conn: sqlite3.Connection, run_id: str,
                               region_level: str, region_name: str,
                               top_n: int = 20, metric: str = 'log_odds') -> pd.DataFrame:
    """
    Query the tendency profile for a specific region (most characteristic characters).

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        region_level: Region level ('city', 'county', 'township')
        region_name: Region name
        top_n: Number of top characters to return
        metric: Metric to use ('log_odds', 'log_lift', 'z_score')

    Returns:
        DataFrame with region's characteristic characters
    """
    if metric not in ['log_odds', 'log_lift', 'z_score']:
        raise ValueError(f"Invalid metric: {metric}. Must be one of: log_odds, log_lift, z_score")

    query = f"""
        SELECT char, frequency, global_frequency, lift, log_lift, log_odds, z_score,
               village_count, total_villages, rank_overrepresented
        FROM regional_tendency
        WHERE run_id = ? AND region_level = ? AND region_name = ? AND support_flag = 1
        ORDER BY {metric} DESC
        LIMIT ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, region_level, region_name, top_n))


def get_all_runs(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Get metadata for all analysis runs.

    Args:
        conn: SQLite database connection

    Returns:
        DataFrame with run metadata
    """
    query = """
        SELECT run_id, created_at, total_villages, valid_villages, unique_chars, status, notes
        FROM analysis_runs
        ORDER BY created_at DESC
    """

    return pd.read_sql_query(query, conn)


# ============================================================================
# Morphology Pattern Query Functions
# ============================================================================

def get_pattern_frequency_global(
    conn: sqlite3.Connection,
    run_id: str,
    pattern_type: str,
    top_n: Optional[int] = None
) -> pd.DataFrame:
    """
    Query global pattern frequency.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        pattern_type: Pattern type (e.g., 'suffix_1', 'prefix_2')
        top_n: Limit to top N patterns by frequency (optional)

    Returns:
        DataFrame with global pattern frequency data
    """
    query = """
        SELECT pattern, village_count, total_villages, frequency, rank
        FROM pattern_frequency_global
        WHERE run_id = ? AND pattern_type = ?
        ORDER BY rank
    """

    if top_n:
        query += f" LIMIT {top_n}"

    return pd.read_sql_query(query, conn, params=(run_id, pattern_type))


def get_pattern_frequency_regional(
    conn: sqlite3.Connection,
    run_id: str,
    pattern_type: str,
    region_level: str,
    region_name: Optional[str] = None,
    top_n: Optional[int] = None
) -> pd.DataFrame:
    """
    Query regional pattern frequency.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        pattern_type: Pattern type (e.g., 'suffix_1', 'prefix_2')
        region_level: Region level ('city', 'county', 'township')
        region_name: Specific region name (optional, returns all if None)
        top_n: Limit to top N patterns by frequency (optional)

    Returns:
        DataFrame with regional pattern frequency data
    """
    if region_name:
        query = """
            SELECT region_name, pattern, village_count, total_villages, frequency, rank_within_region
            FROM pattern_frequency_regional
            WHERE run_id = ? AND pattern_type = ? AND region_level = ? AND region_name = ?
            ORDER BY rank_within_region
        """
        params = (run_id, pattern_type, region_level, region_name)
    else:
        query = """
            SELECT region_name, pattern, village_count, total_villages, frequency, rank_within_region
            FROM pattern_frequency_regional
            WHERE run_id = ? AND pattern_type = ? AND region_level = ?
            ORDER BY region_name, rank_within_region
        """
        params = (run_id, pattern_type, region_level)

    if top_n and region_name:
        query += f" LIMIT {top_n}"

    return pd.read_sql_query(query, conn, params=params)


def get_pattern_tendency_by_region(
    conn: sqlite3.Connection,
    run_id: str,
    pattern_type: str,
    pattern: str,
    region_level: str
) -> pd.DataFrame:
    """
    Query a specific pattern's tendency across all regions at a given level.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        pattern_type: Pattern type (e.g., 'suffix_1', 'prefix_2')
        pattern: Pattern to query (e.g., '村', '新村')
        region_level: Region level ('city', 'county', 'township')

    Returns:
        DataFrame with tendency data for the pattern across regions
    """
    query = """
        SELECT pattern, region_name, frequency, global_frequency, lift, log_lift, log_odds, z_score,
               village_count, total_villages, support_flag
        FROM pattern_tendency
        WHERE run_id = ? AND pattern_type = ? AND pattern = ? AND region_level = ?
        ORDER BY lift DESC
    """

    return pd.read_sql_query(query, conn, params=(run_id, pattern_type, pattern, region_level))


def get_top_polarized_patterns(
    conn: sqlite3.Connection,
    run_id: str,
    pattern_type: str,
    region_level: str,
    top_n: int = 20,
    metric: str = 'log_odds'
) -> pd.DataFrame:
    """
    Query the most polarized patterns (highest absolute tendency values).

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        pattern_type: Pattern type (e.g., 'suffix_1', 'prefix_2')
        region_level: Region level ('city', 'county', 'township')
        top_n: Number of top patterns to return
        metric: Metric to use ('log_odds', 'log_lift', 'z_score')

    Returns:
        DataFrame with top polarized patterns
    """
    if metric not in ['log_odds', 'log_lift', 'z_score']:
        raise ValueError(f"Invalid metric: {metric}. Must be one of: log_odds, log_lift, z_score")

    query = f"""
        SELECT pattern, region_name, frequency, global_frequency, lift, log_lift, log_odds, z_score,
               village_count, total_villages
        FROM pattern_tendency
        WHERE run_id = ? AND pattern_type = ? AND region_level = ? AND support_flag = 1
        ORDER BY ABS({metric}) DESC
        LIMIT ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, pattern_type, region_level, top_n))


def get_region_pattern_profile(
    conn: sqlite3.Connection,
    run_id: str,
    pattern_type: str,
    region_level: str,
    region_name: str,
    top_n: int = 20,
    metric: str = 'log_odds'
) -> pd.DataFrame:
    """
    Query the pattern tendency profile for a specific region.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        pattern_type: Pattern type (e.g., 'suffix_1', 'prefix_2')
        region_level: Region level ('city', 'county', 'township')
        region_name: Region name
        top_n: Number of top patterns to return
        metric: Metric to use ('log_odds', 'log_lift', 'z_score')

    Returns:
        DataFrame with region's characteristic patterns
    """
    if metric not in ['log_odds', 'log_lift', 'z_score']:
        raise ValueError(f"Invalid metric: {metric}. Must be one of: log_odds, log_lift, z_score")

    query = f"""
        SELECT pattern, frequency, global_frequency, lift, log_lift, log_odds, z_score,
               village_count, total_villages, rank_overrepresented
        FROM pattern_tendency
        WHERE run_id = ? AND pattern_type = ? AND region_level = ? AND region_name = ? AND support_flag = 1
        ORDER BY {metric} DESC
        LIMIT ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, pattern_type, region_level, region_name, top_n))


# ============================================================================
# Semantic Analysis Query Functions
# ============================================================================

def get_semantic_vtf_global(conn: sqlite3.Connection, run_id: str,
                           top_n: int = 20) -> pd.DataFrame:
    """
    Query global semantic VTF.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        top_n: Number of top categories to return

    Returns:
        DataFrame with global semantic VTF data
    """
    query = """
        SELECT category, vtf_count, total_villages, frequency, rank
        FROM semantic_vtf_global
        WHERE run_id = ?
        ORDER BY rank
        LIMIT ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, top_n))


def get_semantic_vtf_regional(conn: sqlite3.Connection, run_id: str,
                             level: str, region: Optional[str] = None,
                             top_n: int = 20) -> pd.DataFrame:
    """
    Query regional semantic VTF.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        level: Region level ('city', 'county', 'township')
        region: Specific region name (optional)
        top_n: Number of top categories to return

    Returns:
        DataFrame with regional semantic VTF data
    """
    if region:
        query = """
            SELECT region_name, category, vtf_count, total_villages, frequency, rank_within_region
            FROM semantic_vtf_regional
            WHERE run_id = ? AND region_level = ? AND region_name = ?
            ORDER BY rank_within_region
            LIMIT ?
        """
        params = (run_id, level, region, top_n)
    else:
        query = """
            SELECT region_name, category, vtf_count, total_villages, frequency, rank_within_region
            FROM semantic_vtf_regional
            WHERE run_id = ? AND region_level = ?
            ORDER BY region_name, rank_within_region
        """
        params = (run_id, level)

    return pd.read_sql_query(query, conn, params=params)


def get_semantic_tendency_by_region(conn: sqlite3.Connection, run_id: str,
                                   category: str, level: str) -> pd.DataFrame:
    """
    Query semantic tendency across regions for a specific category.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        category: Semantic category (e.g., 'water', 'mountain')
        level: Region level ('city', 'county', 'township')

    Returns:
        DataFrame with tendency data for the category across regions
    """
    query = """
        SELECT category, region_name, frequency, global_frequency, lift, log_lift,
               log_odds, z_score, vtf_count, total_villages, support_flag
        FROM semantic_tendency
        WHERE run_id = ? AND category = ? AND region_level = ?
        ORDER BY lift DESC
    """

    return pd.read_sql_query(query, conn, params=(run_id, category, level))


def get_top_polarized_semantic_categories(conn: sqlite3.Connection, run_id: str,
                                         level: str, top_n: int = 20,
                                         metric: str = 'log_odds') -> pd.DataFrame:
    """
    Query semantic categories with highest regional variation.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        level: Region level ('city', 'county', 'township')
        top_n: Number of top categories to return
        metric: Metric to use ('log_odds', 'log_lift', 'z_score')

    Returns:
        DataFrame with top polarized semantic categories
    """
    if metric not in ['log_odds', 'log_lift', 'z_score']:
        raise ValueError(f"Invalid metric: {metric}. Must be one of: log_odds, log_lift, z_score")

    query = f"""
        SELECT category, region_name, frequency, global_frequency, lift, log_lift,
               log_odds, z_score, vtf_count, total_villages
        FROM semantic_tendency
        WHERE run_id = ? AND region_level = ? AND support_flag = 1
        ORDER BY ABS({metric}) DESC
        LIMIT ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, level, top_n))


def get_region_semantic_profile(conn: sqlite3.Connection, run_id: str,
                               level: str, region: str, top_n: int = 20,
                               metric: str = 'log_odds') -> pd.DataFrame:
    """
    Query semantic profile for a specific region.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        level: Region level ('city', 'county', 'township')
        region: Region name
        top_n: Number of top categories to return
        metric: Metric to use ('log_odds', 'log_lift', 'z_score')

    Returns:
        DataFrame with region's semantic profile
    """
    if metric not in ['log_odds', 'log_lift', 'z_score']:
        raise ValueError(f"Invalid metric: {metric}. Must be one of: log_odds, log_lift, z_score")

    query = f"""
        SELECT category, frequency, global_frequency, lift, log_lift, log_odds, z_score,
               vtf_count, total_villages
        FROM semantic_tendency
        WHERE run_id = ? AND region_level = ? AND region_name = ? AND support_flag = 1
        ORDER BY {metric} DESC
        LIMIT ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, level, region, top_n))


# ============================================================================
# Clustering Analysis Query Functions
# ============================================================================

def get_cluster_assignments(conn: sqlite3.Connection, run_id: str,
                           algorithm: str = 'kmeans',
                           region_level: str = 'county') -> pd.DataFrame:
    """
    Query cluster assignments for regions.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        algorithm: Clustering algorithm ('kmeans')
        region_level: Region level ('city', 'county', 'town')

    Returns:
        DataFrame with cluster assignments
    """
    query = """
        SELECT region_id, region_name, cluster_id, algorithm, k,
               silhouette_score, distance_to_centroid
        FROM cluster_assignments
        WHERE run_id = ? AND algorithm = ? AND region_level = ?
        ORDER BY cluster_id, distance_to_centroid
    """

    return pd.read_sql_query(query, conn, params=(run_id, algorithm, region_level))


def get_cluster_profile(conn: sqlite3.Connection, run_id: str,
                       cluster_id: int, algorithm: str = 'kmeans') -> pd.DataFrame:
    """
    Query profile for a specific cluster.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        cluster_id: Cluster ID
        algorithm: Clustering algorithm ('kmeans')

    Returns:
        DataFrame with cluster profile
    """
    query = """
        SELECT cluster_id, cluster_size, top_features_json,
               top_semantic_categories_json, top_suffixes_json,
               representative_regions_json
        FROM cluster_profiles
        WHERE run_id = ? AND algorithm = ? AND cluster_id = ?
    """

    return pd.read_sql_query(query, conn, params=(run_id, algorithm, cluster_id))


def get_clustering_metrics(conn: sqlite3.Connection, run_id: str,
                          algorithm: str = 'kmeans') -> pd.DataFrame:
    """
    Query clustering evaluation metrics.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        algorithm: Clustering algorithm ('kmeans')

    Returns:
        DataFrame with clustering metrics for different k values
    """
    query = """
        SELECT k, silhouette_score, davies_bouldin_index,
               calinski_harabasz_score, n_features, pca_enabled, pca_n_components
        FROM clustering_metrics
        WHERE run_id = ? AND algorithm = ?
        ORDER BY k
    """

    return pd.read_sql_query(query, conn, params=(run_id, algorithm))


def get_regions_in_cluster(conn: sqlite3.Connection, run_id: str,
                          cluster_id: int, algorithm: str = 'kmeans',
                          region_level: str = 'county') -> pd.DataFrame:
    """
    Query all regions in a specific cluster.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        cluster_id: Cluster ID
        algorithm: Clustering algorithm ('kmeans')
        region_level: Region level ('city', 'county', 'town')

    Returns:
        DataFrame with regions in the cluster
    """
    query = """
        SELECT region_id, region_name, cluster_id, distance_to_centroid
        FROM cluster_assignments
        WHERE run_id = ? AND algorithm = ? AND cluster_id = ? AND region_level = ?
        ORDER BY distance_to_centroid
    """

    return pd.read_sql_query(query, conn, params=(run_id, algorithm, cluster_id, region_level))


def get_village_features(conn: sqlite3.Connection, run_id: str,
                         city: Optional[str] = None,
                         county: Optional[str] = None,
                         town: Optional[str] = None,
                         limit: Optional[int] = None,
                         offset: Optional[int] = None) -> pd.DataFrame:
    """
    Query village features with optional filters.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        city: Filter by city (optional)
        county: Filter by county (optional)
        town: Filter by town (optional)
        limit: Limit number of results (optional)
        offset: Offset for pagination (optional)

    Returns:
        DataFrame with village features
    """
    query = "SELECT * FROM village_features WHERE run_id = ?"
    params = [run_id]

    if city:
        query += " AND city = ?"
        params.append(city)

    if county:
        query += " AND county = ?"
        params.append(county)

    if town:
        query += " AND town = ?"
        params.append(town)

    if limit:
        query += f" LIMIT {limit}"

    if offset:
        query += f" OFFSET {offset}"

    return pd.read_sql_query(query, conn, params=tuple(params))


def get_villages_by_semantic_tag(conn: sqlite3.Connection, run_id: str,
                                 semantic_category: str,
                                 limit: Optional[int] = None,
                                 offset: Optional[int] = None) -> pd.DataFrame:
    """
    Query villages by semantic tag.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        semantic_category: Semantic category name (e.g., 'mountain', 'water')
        limit: Limit number of results (optional)
        offset: Offset for pagination (optional)

    Returns:
        DataFrame with villages having the specified semantic tag
    """
    col_name = f"sem_{semantic_category}"
    query = f"""
        SELECT city, county, town, village_name, {col_name}
        FROM village_features
        WHERE run_id = ? AND {col_name} = 1
    """

    if limit:
        query += f" LIMIT {limit}"

    if offset:
        query += f" OFFSET {offset}"

    return pd.read_sql_query(query, conn, params=(run_id,))


def get_villages_by_suffix(conn: sqlite3.Connection, run_id: str,
                           suffix: str,
                           suffix_length: int = 2,
                           limit: Optional[int] = None,
                           offset: Optional[int] = None) -> pd.DataFrame:
    """
    Query villages by suffix pattern.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        suffix: Suffix pattern to search for
        suffix_length: Suffix length (1, 2, or 3)
        limit: Limit number of results (optional)
        offset: Offset for pagination (optional)

    Returns:
        DataFrame with villages having the specified suffix
    """
    col_name = f"suffix_{suffix_length}"
    query = f"""
        SELECT city, county, town, village_name, {col_name}
        FROM village_features
        WHERE run_id = ? AND {col_name} = ?
    """

    if limit:
        query += f" LIMIT {limit}"

    if offset:
        query += f" OFFSET {offset}"

    return pd.read_sql_query(query, conn, params=(run_id, suffix))


def get_villages_by_cluster(conn: sqlite3.Connection, run_id: str,
                            cluster_id: int,
                            algorithm: str = 'kmeans',
                            limit: Optional[int] = None,
                            offset: Optional[int] = None) -> pd.DataFrame:
    """
    Query villages by cluster assignment.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        cluster_id: Cluster ID
        algorithm: Clustering algorithm ('kmeans', 'dbscan', 'gmm')
        limit: Limit number of results (optional)
        offset: Offset for pagination (optional)

    Returns:
        DataFrame with villages in the specified cluster
    """
    col_name = f"{algorithm}_cluster_id"
    query = f"""
        SELECT city, county, town, village_name, {col_name}
        FROM village_features
        WHERE run_id = ? AND {col_name} = ?
    """

    if limit:
        query += f" LIMIT {limit}"

    if offset:
        query += f" OFFSET {offset}"

    return pd.read_sql_query(query, conn, params=(run_id, cluster_id))


def get_region_aggregates(conn: sqlite3.Connection, run_id: str,
                         region_level: str = 'county') -> pd.DataFrame:
    """
    Query region aggregates.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        region_level: Region level ('city', 'county', 'town')

    Returns:
        DataFrame with region aggregates
    """
    table_name = f"{region_level}_aggregates"
    query = f"SELECT * FROM {table_name} WHERE run_id = ?"

    return pd.read_sql_query(query, conn, params=(run_id,))


def get_semantic_tag_statistics(conn: sqlite3.Connection, run_id: str) -> pd.DataFrame:
    """
    Query semantic tag statistics across all villages.

    Args:
        conn: SQLite database connection
        run_id: Run identifier

    Returns:
        DataFrame with semantic tag counts and percentages
    """
    query = """
        SELECT
            SUM(sem_mountain) as mountain_count,
            SUM(sem_water) as water_count,
            SUM(sem_settlement) as settlement_count,
            SUM(sem_direction) as direction_count,
            SUM(sem_clan) as clan_count,
            SUM(sem_symbolic) as symbolic_count,
            SUM(sem_agriculture) as agriculture_count,
            SUM(sem_vegetation) as vegetation_count,
            SUM(sem_infrastructure) as infrastructure_count,
            COUNT(*) as total_villages
        FROM village_features
        WHERE run_id = ?
    """

    return pd.read_sql_query(query, conn, params=(run_id,))


