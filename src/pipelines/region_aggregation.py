"""
Region aggregation module.

Computes region-level aggregates from village features.
"""

import sqlite3
import logging
import time
import json
from typing import Dict, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_region_aggregates(
    conn: sqlite3.Connection,
    run_id: str,
    region_level: str,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Compute region-level aggregates.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        region_level: 'city', 'county', or 'town'
        top_n: Number of top suffixes/prefixes to include

    Returns:
        DataFrame with region aggregates
    """
    logger.info(f"Computing {region_level}-level aggregates for run_id={run_id}")

    # Define grouping columns based on region level
    if region_level == 'city':
        group_cols = ['city']
    elif region_level == 'county':
        group_cols = ['city', 'county']
    elif region_level == 'town':
        group_cols = ['city', 'county', 'town']
    else:
        raise ValueError(f"Invalid region_level: {region_level}")

    # Load village features
    query = f"""
        SELECT *
        FROM village_features
        WHERE run_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(run_id,))

    logger.info(f"Loaded {len(df)} village features")

    # Group by region
    aggregates = []

    for region_values, group in df.groupby(group_cols):
        if not isinstance(region_values, tuple):
            region_values = (region_values,)

        agg = {}

        # Region identification
        for i, col in enumerate(group_cols):
            agg[col] = region_values[i]

        # Basic statistics
        agg['total_villages'] = len(group)
        agg['avg_name_length'] = group['name_length'].mean()

        # Semantic tag counts and percentages
        semantic_categories = ['mountain', 'water', 'settlement', 'direction', 'clan',
                              'symbolic', 'agriculture', 'vegetation', 'infrastructure']

        for cat in semantic_categories:
            col_name = f'sem_{cat}'
            agg[f'{col_name}_count'] = group[col_name].sum()
            agg[f'{col_name}_pct'] = (group[col_name].sum() / len(group)) * 100

        # Top suffixes
        suffix_counts = group['suffix_2'].value_counts().head(top_n)
        agg['top_suffixes_json'] = json.dumps(
            [{'suffix': k, 'count': int(v)} for k, v in suffix_counts.items()],
            ensure_ascii=False
        )

        # Top prefixes
        prefix_counts = group['prefix_2'].value_counts().head(top_n)
        agg['top_prefixes_json'] = json.dumps(
            [{'prefix': k, 'count': int(v)} for k, v in prefix_counts.items()],
            ensure_ascii=False
        )

        # Cluster distribution
        cluster_dist = {}
        for algo in ['kmeans', 'dbscan', 'gmm']:
            col_name = f'{algo}_cluster_id'
            if col_name in group.columns:
                dist = group[col_name].value_counts().to_dict()
                cluster_dist[algo] = {int(k): int(v) for k, v in dist.items() if pd.notna(k)}

        agg['cluster_distribution_json'] = json.dumps(cluster_dist, ensure_ascii=False)

        aggregates.append(agg)

    result_df = pd.DataFrame(aggregates)
    logger.info(f"Computed aggregates for {len(result_df)} regions")

    return result_df


def write_region_aggregates(
    conn: sqlite3.Connection,
    run_id: str,
    region_level: str,
    df: pd.DataFrame
):
    """
    Write region aggregates to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        region_level: 'city', 'county', or 'town'
        df: DataFrame with region aggregates
    """
    logger.info(f"Writing {len(df)} {region_level}-level aggregates to database")

    cursor = conn.cursor()
    created_at = time.time()

    # Add metadata
    df['run_id'] = run_id
    df['created_at'] = created_at

    # Determine table name
    table_name = f"{region_level}_aggregates"

    # Prepare columns
    columns = list(df.columns)

    # Insert
    placeholders = ','.join(['?' for _ in columns])
    values = [tuple(row[col] if col in row else None for col in columns) for _, row in df.iterrows()]

    cursor.executemany(f"""
        INSERT OR REPLACE INTO {table_name}
        ({','.join(columns)})
        VALUES ({placeholders})
    """, values)

    conn.commit()
    logger.info(f"Successfully wrote {len(df)} {region_level}-level aggregates")


def compute_and_write_all_aggregates(
    conn: sqlite3.Connection,
    run_id: str,
    top_n: int = 10
):
    """
    Compute and write aggregates for all region levels.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        top_n: Number of top suffixes/prefixes to include
    """
    for region_level in ['city', 'county', 'town']:
        logger.info(f"Processing {region_level}-level aggregates")
        agg_df = compute_region_aggregates(conn, run_id, region_level, top_n)
        write_region_aggregates(conn, run_id, region_level, agg_df)


