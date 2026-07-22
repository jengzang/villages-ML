"""Database loading and connection utilities."""

import sqlite3
import logging
from typing import Iterator, Dict, List, Optional, Tuple
import pandas as pd

from src.schema import VillageTableSchema, DEFAULT_SCHEMA

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


def validate_database_schema(
    conn: sqlite3.Connection,
    use_preprocessed: bool = True,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
) -> bool:
    """
    Validate that the database has the expected schema.

    Args:
        conn: Database connection
        use_preprocessed: If True, validate preprocessed table; otherwise validate original table
        schema: Table schema definition

    Returns:
        True if schema is valid
    """
    cursor = conn.cursor()

    table_name = schema.preprocessed_table if use_preprocessed else schema.raw_table

    cursor.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    if not cursor.fetchone():
        logger.error(f"Table '{table_name}' not found")
        return False

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}

    required_columns = set(schema.admin_columns) | {
        schema.village_name_col(use_preprocessed),
    }

    missing = required_columns - columns

    if missing:
        logger.error(f"Missing required columns: {missing}")
        return False

    logger.info(f"Database schema validated successfully for table: {table_name}")
    return True


def get_total_village_count(
    conn: sqlite3.Connection,
    use_preprocessed: bool = True,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
) -> int:
    """
    Get total number of villages in database.

    Args:
        conn: Database connection
        use_preprocessed: If True, use preprocessed table; otherwise use original table
        schema: Table schema definition

    Returns:
        Total village count
    """
    cursor = conn.cursor()
    table_name = schema.preprocessed_table if use_preprocessed else schema.raw_table

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

    count = cursor.fetchone()[0]
    logger.info(f"Total villages in {table_name}: {count:,}")
    return count


def load_villages(
    conn: sqlite3.Connection,
    city: Optional[str] = None,
    county: Optional[str] = None,
    township: Optional[str] = None,
    chunk_size: int = 10000,
    use_preprocessed: bool = True,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
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
        schema: Table schema definition

    Yields:
        DataFrame chunks with columns: 市级, 区县级, 乡镇级, 自然村
    """
    table_name = schema.preprocessed_table if use_preprocessed else schema.raw_table
    village_col = schema.village_name_col(use_preprocessed)

    query = (
        f"SELECT {schema.city_col}, {schema.county_col}, {schema.township_col}, "
        f"{village_col} as 自然村 FROM {table_name}"
    )
    conditions = []
    params = []

    if city:
        conditions.append(f"{schema.city_col} = ?")
        params.append(city)
    if county:
        conditions.append(f"{schema.county_col} = ?")
        params.append(county)
    if township:
        conditions.append(f"{schema.township_col} = ?")
        params.append(township)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    logger.info(f"Loading villages from {table_name} with query: {query}")
    if params:
        logger.info(f"Parameters: {params}")

    for chunk in pd.read_sql_query(query, conn, params=params, chunksize=chunk_size):
        yield chunk


def get_regional_hierarchy(
    conn: sqlite3.Connection,
    use_preprocessed: bool = True,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
) -> Dict[str, List[str]]:
    """
    Get the administrative hierarchy.

    Args:
        conn: Database connection
        use_preprocessed: If True, use preprocessed table; otherwise use original table
        schema: Table schema definition

    Returns:
        Dictionary with keys 'cities', 'counties', 'townships'
    """
    cursor = conn.cursor()

    table_name = schema.preprocessed_table if use_preprocessed else schema.raw_table

    if use_preprocessed:
        where_clause = f'WHERE {schema.char_count_col} > 0 AND'
    else:
        where_clause = 'WHERE'

    cities = []
    counties = []
    townships = []

    for key, col in [('cities', schema.city_col), ('counties', schema.county_col), ('townships', schema.township_col)]:
        cursor.execute(
            f"SELECT DISTINCT {col} FROM {table_name} {where_clause} {col} IS NOT NULL ORDER BY {col}"
        )
        if key == 'cities':
            cities = [row[0] for row in cursor.fetchall()]
        elif key == 'counties':
            counties = [row[0] for row in cursor.fetchall()]
        else:
            townships = [row[0] for row in cursor.fetchall()]

    logger.info(
        f"Regional hierarchy from {table_name}: "
        f"{len(cities)} cities, {len(counties)} counties, {len(townships)} townships"
    )

    return {
        'cities': cities,
        'counties': counties,
        'townships': townships,
    }


def get_region_village_counts(
    conn: sqlite3.Connection,
    level: str,
    use_preprocessed: bool = True,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
) -> pd.DataFrame:
    """
    Get village counts by region.

    Args:
        conn: Database connection
        level: 'city', 'county', or 'township'
        use_preprocessed: If True, use preprocessed table; otherwise use original table
        schema: Table schema definition

    Returns:
        DataFrame with columns: region_name, village_count
    """
    if level not in schema.level_map:
        raise ValueError(f"Invalid level: {level}. Must be one of: {list(schema.level_map.keys())}")

    column = schema.level_map[level]
    table_name = schema.preprocessed_table if use_preprocessed else schema.raw_table

    if use_preprocessed:
        where_clause = f'WHERE {schema.char_count_col} > 0 AND {column} IS NOT NULL'
    else:
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
