"""
Query spatial-tendency integration results from database.

Usage:
    # Query all results for a run
    python scripts/query_spatial_tendency.py --run-id integration_001

    # Query specific character
    python scripts/query_spatial_tendency.py --run-id integration_001 --char 田

    # Query significant results only
    python scripts/query_spatial_tendency.py --run-id integration_001 --significant-only

    # Filter by city
    python scripts/query_spatial_tendency.py --run-id integration_001 --city 梅州市

    # Export to CSV
    python scripts/query_spatial_tendency.py --run-id integration_001 --output results.csv

    # Top N clusters by character density
    python scripts/query_spatial_tendency.py --run-id integration_001 --top-n 20
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def query_spatial_tendency(
    db_path: str,
    run_id: str,
    character: str = None,
    significant_only: bool = False,
    city: str = None,
    county: str = None,
    min_cluster_size: int = None,
    top_n: int = None
) -> pd.DataFrame:
    """
    Query spatial-tendency integration results.

    Args:
        db_path: Path to database
        run_id: Integration run ID
        character: Filter by character (optional)
        significant_only: Only return significant results
        city: Filter by city (optional)
        county: Filter by county (optional)
        min_cluster_size: Minimum cluster size (optional)
        top_n: Return top N by character density (optional)

    Returns:
        DataFrame with query results
    """
    conn = sqlite3.connect(db_path)

    # Build query
    query = """
        SELECT
            character,
            cluster_id,
            cluster_size,
            n_villages_with_char,
            ROUND(CAST(n_villages_with_char AS FLOAT) / cluster_size * 100, 2) as char_density_pct,
            cluster_tendency_mean,
            cluster_tendency_std,
            centroid_lon,
            centroid_lat,
            avg_distance_km,
            spatial_coherence,
            dominant_city,
            dominant_county,
            is_significant,
            avg_p_value,
            tendency_run_id,
            spatial_run_id
        FROM spatial_tendency_integration
        WHERE run_id = ?
    """

    params = [run_id]

    if character:
        query += " AND character = ?"
        params.append(character)

    if significant_only:
        query += " AND is_significant = 1"

    if city:
        query += " AND dominant_city = ?"
        params.append(city)

    if county:
        query += " AND dominant_county = ?"
        params.append(county)

    if min_cluster_size:
        query += " AND cluster_size >= ?"
        params.append(min_cluster_size)

    if top_n:
        query += " ORDER BY n_villages_with_char DESC LIMIT ?"
        params.append(top_n)
    else:
        query += " ORDER BY character, cluster_id"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return df


def print_summary(df: pd.DataFrame):
    """Print summary statistics."""
    print("\n" + "="*80)
    print("SPATIAL-TENDENCY INTEGRATION QUERY RESULTS")
    print("="*80)
    print(f"Total records: {len(df)}")
    print(f"Unique characters: {df['character'].nunique()}")
    print(f"Unique clusters: {df['cluster_id'].nunique()}")
    print(f"Significant results: {df['is_significant'].sum()} ({df['is_significant'].sum()/len(df)*100:.1f}%)")
    print()

    # Character summary
    print("Character Summary:")
    print("-" * 80)
    char_summary = df.groupby('character').agg({
        'cluster_id': 'count',
        'n_villages_with_char': 'sum',
        'cluster_size': 'sum',
        'is_significant': 'sum'
    }).rename(columns={
        'cluster_id': 'n_clusters',
        'n_villages_with_char': 'total_villages_with_char',
        'cluster_size': 'total_cluster_size',
        'is_significant': 'n_significant'
    })
    char_summary['char_density_pct'] = (
        char_summary['total_villages_with_char'] / char_summary['total_cluster_size'] * 100
    ).round(2)
    print(char_summary.to_string())
    print()

    # City summary
    print("City Summary:")
    print("-" * 80)
    city_summary = df.groupby('dominant_city').agg({
        'cluster_id': 'count',
        'n_villages_with_char': 'sum',
        'is_significant': 'sum'
    }).rename(columns={
        'cluster_id': 'n_clusters',
        'n_villages_with_char': 'total_villages',
        'is_significant': 'n_significant'
    }).sort_values('n_clusters', ascending=False).head(10)
    print(city_summary.to_string())
    print()


def print_detailed_results(df: pd.DataFrame, limit: int = 20):
    """Print detailed results."""
    print("Detailed Results (top {}):".format(min(limit, len(df))))
    print("-" * 80)

    display_cols = [
        'character', 'cluster_id', 'n_villages_with_char', 'cluster_size',
        'char_density_pct', 'cluster_tendency_mean', 'spatial_coherence',
        'dominant_city', 'dominant_county', 'is_significant'
    ]

    print(df[display_cols].head(limit).to_string(index=False))
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Query spatial-tendency integration results'
    )
    parser.add_argument(
        '--run-id',
        type=str,
        required=True,
        help='Integration run ID'
    )
    parser.add_argument(
        '--char',
        type=str,
        help='Filter by character'
    )
    parser.add_argument(
        '--significant-only',
        action='store_true',
        help='Only show significant results'
    )
    parser.add_argument(
        '--city',
        type=str,
        help='Filter by city'
    )
    parser.add_argument(
        '--county',
        type=str,
        help='Filter by county'
    )
    parser.add_argument(
        '--min-cluster-size',
        type=int,
        help='Minimum cluster size'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        help='Return top N by character density'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to database (default: data/villages.db)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file path'
    )
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip summary statistics'
    )

    args = parser.parse_args()

    # Check database exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    # Query results
    logger.info(f"Querying spatial-tendency integration for run_id={args.run_id}")

    df = query_spatial_tendency(
        db_path=str(db_path),
        run_id=args.run_id,
        character=args.char,
        significant_only=args.significant_only,
        city=args.city,
        county=args.county,
        min_cluster_size=args.min_cluster_size,
        top_n=args.top_n
    )

    if len(df) == 0:
        logger.warning("No results found")
        sys.exit(0)

    # Print results
    if not args.no_summary:
        print_summary(df)
        print_detailed_results(df, limit=args.top_n if args.top_n else 20)

    # Export if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"Results exported to: {output_path}")


if __name__ == '__main__':
    main()
