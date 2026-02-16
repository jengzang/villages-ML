#!/usr/bin/env python
"""
Query tendency analysis results from database.

This script queries tendency analysis results including significance testing
from the database.

Usage:
    # Query all results for a run
    python scripts/query_tendency.py --run-id tendency_v1

    # Query specific character
    python scripts/query_tendency.py --run-id tendency_v1 --char 田

    # Query only significant results
    python scripts/query_tendency.py --run-id tendency_v1 --significant-only

    # Query by region level
    python scripts/query_tendency.py --run-id tendency_v1 --level 乡镇

    # Export to CSV
    python scripts/query_tendency.py --run-id tendency_v1 --output results.csv
"""

import argparse
import logging
import sqlite3
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def query_tendency_results(
    db_path: str,
    run_id: str,
    char: str = None,
    region_level: str = None,
    region_name: str = None,
    significant_only: bool = False,
    min_effect_size: float = None,
    max_p_value: float = None,
    limit: int = None
) -> pd.DataFrame:
    """
    Query tendency analysis results from database.

    Args:
        db_path: Path to SQLite database
        run_id: Run identifier
        char: Filter by specific character
        region_level: Filter by region level
        region_name: Filter by region name
        significant_only: Only return significant results (p < 0.05)
        min_effect_size: Minimum effect size
        max_p_value: Maximum p-value
        limit: Maximum number of results

    Returns:
        DataFrame with tendency and significance results
    """
    conn = sqlite3.connect(db_path)

    try:
        # Build query
        query = """
            SELECT
                t.run_id,
                t.region_level,
                t.region_name,
                t.char,
                t.village_count,
                t.total_villages,
                t.frequency,
                t.global_village_count,
                t.global_frequency,
                t.lift,
                t.log_lift,
                t.log_odds,
                t.z_score,
                t.support_flag,
                t.rank_overrepresented,
                t.rank_underrepresented,
                s.chi_square_statistic,
                s.p_value,
                s.is_significant,
                s.significance_level,
                s.effect_size,
                s.effect_size_interpretation,
                s.ci_lower,
                s.ci_upper
            FROM regional_tendency t
            LEFT JOIN tendency_significance s
                ON t.run_id = s.run_id
                AND t.region_level = s.region_level
                AND t.region_name = s.region_name
                AND t.char = s.char
            WHERE t.run_id = ?
        """

        params = [run_id]

        # Add filters
        if char:
            query += " AND t.char = ?"
            params.append(char)

        if region_level:
            query += " AND t.region_level = ?"
            params.append(region_level)

        if region_name:
            query += " AND t.region_name = ?"
            params.append(region_name)

        if significant_only:
            query += " AND s.is_significant = 1"

        if min_effect_size is not None:
            query += " AND s.effect_size >= ?"
            params.append(min_effect_size)

        if max_p_value is not None:
            query += " AND s.p_value <= ?"
            params.append(max_p_value)

        # Add ordering
        query += " ORDER BY s.p_value ASC, s.effect_size DESC"

        # Add limit
        if limit:
            query += f" LIMIT {limit}"

        # Execute query
        df = pd.read_sql_query(query, conn, params=params)

        logger.info(f"Retrieved {len(df)} tendency results for run_id={run_id}")

        return df

    finally:
        conn.close()


def print_summary(df: pd.DataFrame):
    """Print summary statistics of query results."""
    if len(df) == 0:
        logger.info("No results found")
        return

    logger.info("\n=== Query Results Summary ===")
    logger.info(f"Total results: {len(df)}")

    # Significance summary
    if 'is_significant' in df.columns:
        n_significant = df['is_significant'].sum()
        pct_significant = (n_significant / len(df) * 100) if len(df) > 0 else 0
        logger.info(f"Significant results: {n_significant} ({pct_significant:.1f}%)")

    # Effect size distribution
    if 'effect_size_interpretation' in df.columns:
        effect_counts = df['effect_size_interpretation'].value_counts()
        logger.info(f"Effect size distribution:")
        for effect, count in effect_counts.items():
            logger.info(f"  {effect}: {count}")

    # Top results
    logger.info("\nTop 10 results:")
    display_cols = ['char', 'region_name', 'lift', 'p_value', 'significance_level', 'effect_size']
    available_cols = [col for col in display_cols if col in df.columns]
    print(df[available_cols].head(10).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description='Query tendency analysis results')
    parser.add_argument('--run-id', type=str, required=True, help='Run identifier')
    parser.add_argument('--db-path', type=str, default='data/villages.db', help='Path to database')
    parser.add_argument('--char', type=str, help='Filter by character')
    parser.add_argument('--level', type=str, help='Filter by region level')
    parser.add_argument('--region', type=str, help='Filter by region name')
    parser.add_argument('--significant-only', action='store_true', help='Only show significant results')
    parser.add_argument('--min-effect-size', type=float, help='Minimum effect size')
    parser.add_argument('--max-p-value', type=float, help='Maximum p-value')
    parser.add_argument('--limit', type=int, help='Maximum number of results')
    parser.add_argument('--output', type=str, help='Output CSV file path')

    args = parser.parse_args()

    # Query results
    df = query_tendency_results(
        db_path=args.db_path,
        run_id=args.run_id,
        char=args.char,
        region_level=args.level,
        region_name=args.region,
        significant_only=args.significant_only,
        min_effect_size=args.min_effect_size,
        max_p_value=args.max_p_value,
        limit=args.limit
    )

    # Print summary
    print_summary(df)

    # Export if requested
    if args.output:
        df.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"\n✓ Results exported to {args.output}")


if __name__ == '__main__':
    main()
