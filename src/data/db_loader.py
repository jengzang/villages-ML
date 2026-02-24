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


def validate_database_schema(conn: sqlite3.Connection, use_preprocessed: bool = True) -> bool:
    """
    Validate that the database has the expected schema.

    Args:
        conn: Database connection
        use_preprocessed: If True, validate preprocessed table; otherwise validate original table

    Returns:
        True if schema is valid
    """
    cursor = conn.cursor()

    # Determine table name
    table_name = '广东省自然村_预处理' if use_preprocessed else '广东省自然村'

    # Check if table exists
    cursor.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    if not cursor.fetchone():
        logger.error(f"Table '{table_name}' not found")
        return False

    # Check required columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}

    # Required columns depend on table type
    if use_preprocessed:
        required_columns = {'市级', '区县级', '乡镇级', '自然村_去前缀'}
    else:
        required_columns = {'市级', '区县级', '乡镇级', '自然村'}

    missing = required_columns - columns

    if missing:
        logger.error(f"Missing required columns: {missing}")
        return False

    logger.info(f"Database schema validated successfully for table: {table_name}")
    return True


def get_total_village_count(conn: sqlite3.Connection, use_preprocessed: bool = True) -> int:
    """
    Get total number of villages in database.

    Args:
        conn: Database connection
        use_preprocessed: If True, use preprocessed table; otherwise use original table

    Returns:
        Total village count
    """
    cursor = conn.cursor()

    if use_preprocessed:
        cursor.execute("SELECT COUNT(*) FROM 广东省自然村_预处理")
    else:
        cursor.execute("SELECT COUNT(*) FROM 广东省自然村")

    count = cursor.fetchone()[0]
    table_name = '广东省自然村_预处理' if use_preprocessed else '广东省自然村'
    logger.info(f"Total villages in {table_name}: {count:,}")
    return count


def load_villages(
    conn: sqlite3.Connection,
    city: Optional[str] = None,
    county: Optional[str] = None,
    township: Optional[str] = None,
    chunk_size: int = 10000,
    use_preprocessed: bool = True
) -> Iterator[pd.DataFrame]:
    """
    Load villages from database in chunks.

    Args:
        conn: Database connection
        city: Filter by city (optional)
        county: Filter by county (optional)
        township: Filter by township (optional)
        chunk_size: Number of rows per chunk
        use_preprocessed: If True, use preprocessed table with prefix-cleaned names

    Yields:
        DataFrame chunks with columns: 市级, 区县级, 乡镇级, 自然村
    """
    # Determine table and column names
    if use_preprocessed:
        table_name = '广东省自然村_预处理'
        village_col = '自然村_去前缀'
        base_conditions = []  # No filtering needed for preprocessed table
    else:
        table_name = '广东省自然村'
        village_col = '自然村'
        base_conditions = []

    # Build query - use actual column names from database
    query = f"SELECT 市级, 区县级, 乡镇级, {village_col} as 自然村 FROM {table_name}"
    conditions = base_conditions.copy()
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

    logger.info(f"Loading villages from {table_name} with query: {query}")
    if params:
        logger.info(f"Parameters: {params}")

    # Load in chunks
    for chunk in pd.read_sql_query(query, conn, params=params, chunksize=chunk_size):
        yield chunk


def get_regional_hierarchy(conn: sqlite3.Connection, use_preprocessed: bool = True) -> Dict[str, List[str]]:
    """
    Get the administrative hierarchy.

    Args:
        conn: Database connection
        use_preprocessed: If True, use preprocessed table; otherwise use original table

    Returns:
        Dictionary with keys 'cities', 'counties', 'townships'
    """
    cursor = conn.cursor()

    # Determine table name and filter
    if use_preprocessed:
        table_name = '广东省自然村_预处理'
        where_clause = 'WHERE 有效 = 1 AND'
    else:
        table_name = '广东省自然村'
        where_clause = 'WHERE'

    # Get unique cities
    cursor.execute(f"SELECT DISTINCT 市级 FROM {table_name} {where_clause} 市级 IS NOT NULL ORDER BY 市级")
    cities = [row[0] for row in cursor.fetchall()]

    # Get unique counties
    cursor.execute(f"SELECT DISTINCT 区县级 FROM {table_name} {where_clause} 区县级 IS NOT NULL ORDER BY 区县级")
    counties = [row[0] for row in cursor.fetchall()]

    # Get unique townships
    cursor.execute(f"SELECT DISTINCT 乡镇级 FROM {table_name} {where_clause} 乡镇级 IS NOT NULL ORDER BY 乡镇级")
    townships = [row[0] for row in cursor.fetchall()]

    logger.info(f"Regional hierarchy from {table_name}: {len(cities)} cities, {len(counties)} counties, {len(townships)} townships")

    return {
        'cities': cities,
        'counties': counties,
        'townships': townships
    }


def get_region_village_counts(conn: sqlite3.Connection, level: str, use_preprocessed: bool = True) -> pd.DataFrame:
    """
    Get village counts by region.

    Args:
        conn: Database connection
        level: 'city', 'county', or 'township'
        use_preprocessed: If True, use preprocessed table; otherwise use original table

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

    # Determine table name and filter
    if use_preprocessed:
        table_name = '广东省自然村_预处理'
        where_clause = f'WHERE 有效 = 1 AND {column} IS NOT NULL'
    else:
        table_name = '广东省自然村'
        where_clause = f'WHERE {column} IS NOT NULL'

    query = f"""
        SELECT {column} as region_name, COUNT(*) as village_count
        FROM {table_name}
        {where_clause}
        GROUP BY {column}
        ORDER BY village_count DESC
    """

    df = pd.read_sql_query(query, conn)
    logger.info(f"Loaded village counts for {len(df)} {level} regions from {table_name}")
    return df

