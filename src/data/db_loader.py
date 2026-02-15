"""Database loading and connection utilities."""

import sqlite3
import logging
from typing import Iterator, Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Create database connection.

    Args:
        db_path: Path to SQLite database

    Returns:
        Database connection
    """
    conn = sqlite3.connect(db_path)
    logger.info(f"Connected to database: {db_path}")
    return conn


def validate_database_schema(conn: sqlite3.Connection) -> bool:
    """
    Validate that the database has the expected schema.

    Args:
        conn: Database connection

    Returns:
        True if schema is valid
    """
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='广东省自然村'"
    )
    if not cursor.fetchone():
        logger.error("Table '广东省自然村' not found")
        return False

    # Check required columns
    cursor.execute("PRAGMA table_info(广东省自然村)")
    columns = {row[1] for row in cursor.fetchall()}

    # Actual column names in database: 市级, 区县级, 乡镇级, 行政村, 自然村
    required_columns = {'市级', '区县级', '乡镇级', '自然村'}
    missing = required_columns - columns

    if missing:
        logger.error(f"Missing required columns: {missing}")
        return False

    logger.info("Database schema validated successfully")
    return True


def get_total_village_count(conn: sqlite3.Connection) -> int:
    """Get total number of villages in database."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村")
    count = cursor.fetchone()[0]
    logger.info(f"Total villages in database: {count:,}")
    return count


def load_villages(
    conn: sqlite3.Connection,
    city: Optional[str] = None,
    county: Optional[str] = None,
    township: Optional[str] = None,
    chunk_size: int = 10000
) -> Iterator[pd.DataFrame]:
    """
    Load villages from database in chunks.

    Args:
        conn: Database connection
        city: Filter by city (optional)
        county: Filter by county (optional)
        township: Filter by township (optional)
        chunk_size: Number of rows per chunk

    Yields:
        DataFrame chunks with columns: 市级, 区县级, 乡镇级, 自然村
    """
    # Build query - use actual column names from database
    query = "SELECT 市级, 区县级, 乡镇级, 自然村 FROM 广东省自然村"
    conditions = []
    params = []

    if city:
        conditions.append("市级 = ?")
        params.append(city)
    if county:
        conditions.append("区县级 = ?")
        params.append(county)
    if township:
        conditions.append("乡镇级 = ?")
        params.append(township)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    logger.info(f"Loading villages with query: {query}")
    if params:
        logger.info(f"Parameters: {params}")

    # Load in chunks
    for chunk in pd.read_sql_query(query, conn, params=params, chunksize=chunk_size):
        yield chunk


def get_regional_hierarchy(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    """
    Get the administrative hierarchy.

    Returns:
        Dictionary with keys 'cities', 'counties', 'townships'
    """
    cursor = conn.cursor()

    # Get unique cities
    cursor.execute("SELECT DISTINCT 市级 FROM 广东省自然村 WHERE 市级 IS NOT NULL ORDER BY 市级")
    cities = [row[0] for row in cursor.fetchall()]

    # Get unique counties
    cursor.execute("SELECT DISTINCT 区县级 FROM 广东省自然村 WHERE 区县级 IS NOT NULL ORDER BY 区县级")
    counties = [row[0] for row in cursor.fetchall()]

    # Get unique townships
    cursor.execute("SELECT DISTINCT 乡镇级 FROM 广东省自然村 WHERE 乡镇级 IS NOT NULL ORDER BY 乡镇级")
    townships = [row[0] for row in cursor.fetchall()]

    logger.info(f"Regional hierarchy: {len(cities)} cities, {len(counties)} counties, {len(townships)} townships")

    return {
        'cities': cities,
        'counties': counties,
        'townships': townships
    }


def get_region_village_counts(conn: sqlite3.Connection, level: str) -> pd.DataFrame:
    """
    Get village counts by region.

    Args:
        conn: Database connection
        level: 'city', 'county', or 'township'

    Returns:
        DataFrame with columns: region_name, village_count
    """
    level_map = {
        'city': '市级',
        'county': '区县级',
        'township': '乡镇级'
    }

    if level not in level_map:
        raise ValueError(f"Invalid level: {level}")

    column = level_map[level]
    query = f"""
        SELECT {column} as region_name, COUNT(*) as village_count
        FROM 广东省自然村
        WHERE {column} IS NOT NULL
        GROUP BY {column}
        ORDER BY village_count DESC
    """

    df = pd.read_sql_query(query, conn)
    logger.info(f"Loaded village counts for {len(df)} {level} regions")
    return df

