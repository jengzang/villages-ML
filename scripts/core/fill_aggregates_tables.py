"""
Phase 2: Fill aggregates tables.

This script fills the city_aggregates, county_aggregates, and town_aggregates
tables by computing aggregates directly from village_features.
"""

import sqlite3
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def compute_region_aggregates_simple(conn, region_level, top_n=10):
    """
    Compute region-level aggregates without run_id dependency.
    """
    print(f"Computing {region_level}-level aggregates...")

    # Define grouping columns
    if region_level == 'city':
        group_cols = ['city']
    elif region_level == 'county':
        group_cols = ['city', 'county']
    elif region_level == 'town':
        group_cols = ['city', 'county', 'town']
    else:
        raise ValueError(f"Invalid region_level: {region_level}")

    # Load village features
    query = "SELECT * FROM village_features"
    df = pd.read_sql_query(query, conn)
    print(f"  Loaded {len(df)} village features")

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
            if col_name in group.columns:
                agg[f'{cat}_count'] = group[col_name].sum()
                agg[f'{cat}_pct'] = (group[col_name].sum() / len(group)) * 100

        # Top suffixes
        suffix_counts = {}
        for i in range(1, 4):
            col = f'suffix_{i}'
            if col in group.columns:
                counts = group[col].value_counts()
                for suffix, count in counts.head(top_n).items():
                    if pd.notna(suffix):
                        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + count

        top_suffixes = sorted(suffix_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        agg['top_suffixes'] = json.dumps([{'suffix': s, 'count': c} for s, c in top_suffixes], ensure_ascii=False)

        # Top prefixes
        prefix_counts = {}
        for i in range(1, 4):
            col = f'prefix_{i}'
            if col in group.columns:
                counts = group[col].value_counts()
                for prefix, count in counts.head(top_n).items():
                    if pd.notna(prefix):
                        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + count

        top_prefixes = sorted(prefix_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        agg['top_prefixes'] = json.dumps([{'prefix': p, 'count': c} for p, c in top_prefixes], ensure_ascii=False)

        aggregates.append(agg)

    return pd.DataFrame(aggregates)

def write_aggregates(conn, df, table_name):
    """Write aggregates to database."""
    print(f"  Writing {len(df)} rows to {table_name}...")
    df.to_sql(table_name, conn, if_exists='replace', index=False)

def main():
    db_path = project_root / 'data' / 'villages.db'

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)

    print("\nComputing and writing aggregates for all region levels...")
    print("This may take 5-10 minutes...\n")

    # Compute and write for each level
    for region_level, table_name in [
        ('city', 'city_aggregates'),
        ('county', 'county_aggregates'),
        ('town', 'town_aggregates')
    ]:
        agg_df = compute_region_aggregates_simple(conn, region_level, top_n=10)
        write_aggregates(conn, agg_df, table_name)

    conn.commit()

    # Verify row counts
    cursor = conn.cursor()
    print("\nVerifying aggregates tables:")
    for table in ['city_aggregates', 'county_aggregates', 'town_aggregates']:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")

    conn.close()
    print("\nPhase 2 complete")

if __name__ == '__main__':
    main()
