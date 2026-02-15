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