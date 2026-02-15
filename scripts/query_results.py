"""
Command-line tool for querying frequency analysis results from database.

Usage examples:
    # List all runs
    python scripts/query_results.py --list-runs

    # CHARACTER FREQUENCY QUERIES:

    # Query global frequency (top 20)
    python scripts/query_results.py --run-id run_001 --type global --top 20

    # Query regional frequency for a specific region
    python scripts/query_results.py --run-id run_001 --type regional --level city --region 广州市 --top 20

    # Query character tendency across regions
    python scripts/query_results.py --run-id run_001 --type char-tendency --char 村 --level city

    # Query region tendency profile
    python scripts/query_results.py --run-id run_001 --type region-profile --level city --region 广州市 --top 20

    # Query top polarized characters
    python scripts/query_results.py --run-id run_001 --type polarized --level city --top 20

    # MORPHOLOGY PATTERN QUERIES:

    # Query global pattern frequency
    python scripts/query_results.py --run-id morph_001 --type pattern-global --pattern-type suffix_1 --top 20

    # Query regional pattern frequency
    python scripts/query_results.py --run-id morph_001 --type pattern-regional --pattern-type suffix_1 --level city --region 珠海市 --top 20

    # Query pattern tendency across regions
    python scripts/query_results.py --run-id morph_001 --type pattern-tendency --pattern-type suffix_1 --pattern 涌 --level city

    # Query region pattern profile
    python scripts/query_results.py --run-id morph_001 --type pattern-profile --pattern-type suffix_1 --level city --region 佛山市 --top 20

    # Query top polarized patterns
    python scripts/query_results.py --run-id morph_001 --type pattern-polarized --pattern-type suffix_1 --level city --top 20 --metric log_odds

    # Export to CSV
    python scripts/query_results.py --run-id morph_001 --type pattern-global --pattern-type suffix_1 --top 100 --output suffix_1_top100.csv
"""

import argparse
import sqlite3
import sys
import io
from pathlib import Path

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.db_query import (
    get_latest_run_id,
    get_global_frequency,
    get_regional_frequency,
    get_char_tendency_by_region,
    get_top_polarized_chars,
    get_region_tendency_profile,
    get_all_runs,
    get_pattern_frequency_global,
    get_pattern_frequency_regional,
    get_pattern_tendency_by_region,
    get_top_polarized_patterns,
    get_region_pattern_profile,
    get_semantic_vtf_global,
    get_semantic_vtf_regional,
    get_semantic_tendency_by_region,
    get_top_polarized_semantic_categories,
    get_region_semantic_profile,
    get_cluster_assignments,
    get_cluster_profile,
    get_clustering_metrics,
    get_regions_in_cluster
)


def main():
    parser = argparse.ArgumentParser(
        description='Query frequency analysis results from database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--db-path', type=str, default='data/villages.db',
                       help='Path to SQLite database (default: data/villages.db)')
    parser.add_argument('--run-id', type=str,
                       help='Run ID to query (default: latest run)')
    parser.add_argument('--list-runs', action='store_true',
                       help='List all analysis runs')
    parser.add_argument('--type', type=str,
                       choices=['global', 'regional', 'char-tendency', 'region-profile', 'polarized',
                               'pattern-global', 'pattern-regional', 'pattern-tendency',
                               'pattern-profile', 'pattern-polarized',
                               'semantic-global', 'semantic-regional', 'semantic-tendency',
                               'semantic-profile', 'semantic-polarized',
                               'cluster-assignments', 'cluster-profile', 'cluster-metrics', 'cluster-regions'],
                       help='Query type')
    parser.add_argument('--level', type=str, choices=['city', 'county', 'township'],
                       help='Region level (for regional queries)')
    parser.add_argument('--region', type=str,
                       help='Region name (for regional queries)')
    parser.add_argument('--char', type=str,
                       help='Character to query (for char-tendency)')
    parser.add_argument('--top', type=int, default=20,
                       help='Number of top results to return (default: 20)')
    parser.add_argument('--metric', type=str, default='log_odds', choices=['log_odds', 'log_lift', 'z_score'],
                       help='Metric to use for sorting (default: log_odds)')
    parser.add_argument('--output', type=str,
                       help='Output CSV file path (optional)')
    parser.add_argument('--pattern-type', type=str,
                       choices=['suffix_1', 'suffix_2', 'suffix_3', 'prefix_2', 'prefix_3'],
                       help='Pattern type (required for pattern-* queries)')
    parser.add_argument('--pattern', type=str,
                       help='Specific pattern to query (required for pattern-tendency)')
    parser.add_argument('--category', type=str,
                       choices=['mountain', 'water', 'settlement', 'direction',
                               'clan', 'symbolic', 'agriculture', 'vegetation',
                               'infrastructure'],
                       help='Semantic category (required for semantic-tendency)')
    parser.add_argument('--algorithm', type=str, default='kmeans',
                       choices=['kmeans'],
                       help='Clustering algorithm (default: kmeans)')
    parser.add_argument('--cluster-id', type=int,
                       help='Cluster ID (required for cluster-profile and cluster-regions)')

    args = parser.parse_args()

    # Connect to database
    try:
        conn = sqlite3.connect(args.db_path)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return 1

    try:
        # List runs
        if args.list_runs:
            df = get_all_runs(conn)
            print("\nAnalysis Runs:")
            print("=" * 80)
            print(df.to_string(index=False))
            return 0

        # Get run_id
        run_id = args.run_id
        if not run_id:
            run_id = get_latest_run_id(conn)
            if not run_id:
                print("No analysis runs found in database")
                return 1
            print(f"Using latest run_id: {run_id}\n")

        # Execute query based on type
        if args.type == 'global':
            df = get_global_frequency(conn, run_id, top_n=args.top)
            print(f"\nGlobal Character Frequency (Top {args.top}):")
            print("=" * 80)

        elif args.type == 'regional':
            if not args.level:
                print("Error: --level is required for regional queries")
                return 1
            df = get_regional_frequency(conn, run_id, args.level, args.region, top_n=args.top)
            if args.region:
                print(f"\nRegional Frequency for {args.region} ({args.level}-level, Top {args.top}):")
            else:
                print(f"\nRegional Frequency ({args.level}-level):")
            print("=" * 80)

        elif args.type == 'char-tendency':
            if not args.char or not args.level:
                print("Error: --char and --level are required for char-tendency queries")
                return 1
            df = get_char_tendency_by_region(conn, run_id, args.char, args.level)
            print(f"\nTendency for '{args.char}' across {args.level}-level regions:")
            print("=" * 80)

        elif args.type == 'region-profile':
            if not args.level or not args.region:
                print("Error: --level and --region are required for region-profile queries")
                return 1
            df = get_region_tendency_profile(conn, run_id, args.level, args.region, top_n=args.top, metric=args.metric)
            print(f"\nTendency Profile for {args.region} ({args.level}-level, Top {args.top} by {args.metric}):")
            print("=" * 80)

        elif args.type == 'polarized':
            if not args.level:
                print("Error: --level is required for polarized queries")
                return 1
            df = get_top_polarized_chars(conn, run_id, args.level, top_n=args.top, metric=args.metric)
            print(f"\nTop {args.top} Polarized Characters ({args.level}-level, by {args.metric}):")
            print("=" * 80)

        elif args.type == 'pattern-global':
            if not args.pattern_type:
                print("Error: --pattern-type is required for pattern-global queries")
                return 1
            df = get_pattern_frequency_global(conn, run_id, args.pattern_type, top_n=args.top)
            print(f"\nGlobal Pattern Frequency ({args.pattern_type}, Top {args.top}):")
            print("=" * 80)

        elif args.type == 'pattern-regional':
            if not args.pattern_type or not args.level:
                print("Error: --pattern-type and --level are required for pattern-regional queries")
                return 1
            df = get_pattern_frequency_regional(conn, run_id, args.pattern_type,
                                                args.level, args.region, top_n=args.top)
            if args.region:
                print(f"\nRegional Pattern Frequency for {args.region} ({args.pattern_type}, {args.level}-level, Top {args.top}):")
            else:
                print(f"\nRegional Pattern Frequency ({args.pattern_type}, {args.level}-level):")
            print("=" * 80)

        elif args.type == 'pattern-tendency':
            if not args.pattern_type or not args.pattern or not args.level:
                print("Error: --pattern-type, --pattern, and --level are required for pattern-tendency queries")
                return 1
            df = get_pattern_tendency_by_region(conn, run_id, args.pattern_type,
                                                args.pattern, args.level)
            print(f"\nTendency for pattern '{args.pattern}' ({args.pattern_type}) across {args.level}-level regions:")
            print("=" * 80)

        elif args.type == 'pattern-profile':
            if not args.pattern_type or not args.level or not args.region:
                print("Error: --pattern-type, --level, and --region are required for pattern-profile queries")
                return 1
            df = get_region_pattern_profile(conn, run_id, args.pattern_type,
                                            args.level, args.region,
                                            top_n=args.top, metric=args.metric)
            print(f"\nPattern Profile for {args.region} ({args.pattern_type}, {args.level}-level, Top {args.top} by {args.metric}):")
            print("=" * 80)

        elif args.type == 'pattern-polarized':
            if not args.pattern_type or not args.level:
                print("Error: --pattern-type and --level are required for pattern-polarized queries")
                return 1
            df = get_top_polarized_patterns(conn, run_id, args.pattern_type,
                                            args.level, top_n=args.top, metric=args.metric)
            print(f"\nTop {args.top} Polarized Patterns ({args.pattern_type}, {args.level}-level, by {args.metric}):")
            print("=" * 80)

        elif args.type == 'semantic-global':
            df = get_semantic_vtf_global(conn, run_id, top_n=args.top)
            print(f"\nGlobal Semantic VTF (Top {args.top}):")
            print("=" * 80)

        elif args.type == 'semantic-regional':
            if not args.level:
                print("Error: --level is required for semantic-regional queries")
                return 1
            df = get_semantic_vtf_regional(conn, run_id, args.level, args.region, top_n=args.top)
            if args.region:
                print(f"\nRegional Semantic VTF for {args.region} ({args.level}-level, Top {args.top}):")
            else:
                print(f"\nRegional Semantic VTF ({args.level}-level):")
            print("=" * 80)

        elif args.type == 'semantic-tendency':
            if not args.category or not args.level:
                print("Error: --category and --level are required for semantic-tendency queries")
                return 1
            df = get_semantic_tendency_by_region(conn, run_id, args.category, args.level)
            print(f"\nTendency for '{args.category}' category across {args.level}-level regions:")
            print("=" * 80)

        elif args.type == 'semantic-profile':
            if not args.level or not args.region:
                print("Error: --level and --region are required for semantic-profile queries")
                return 1
            df = get_region_semantic_profile(conn, run_id, args.level, args.region,
                                            top_n=args.top, metric=args.metric)
            print(f"\nSemantic Profile for {args.region} ({args.level}-level, Top {args.top} by {args.metric}):")
            print("=" * 80)

        elif args.type == 'semantic-polarized':
            if not args.level:
                print("Error: --level is required for semantic-polarized queries")
                return 1
            df = get_top_polarized_semantic_categories(conn, run_id, args.level,
                                                      top_n=args.top, metric=args.metric)
            print(f"\nTop {args.top} Polarized Semantic Categories ({args.level}-level, by {args.metric}):")
            print("=" * 80)

        elif args.type == 'cluster-assignments':
            if not args.level:
                args.level = 'county'  # Default to county level
            df = get_cluster_assignments(conn, run_id, algorithm=args.algorithm, region_level=args.level)
            print(f"\nCluster Assignments ({args.algorithm}, {args.level}-level):")
            print("=" * 80)

        elif args.type == 'cluster-profile':
            if args.cluster_id is None:
                print("Error: --cluster-id is required for cluster-profile queries")
                return 1
            df = get_cluster_profile(conn, run_id, args.cluster_id, algorithm=args.algorithm)
            print(f"\nCluster Profile (Cluster {args.cluster_id}, {args.algorithm}):")
            print("=" * 80)

        elif args.type == 'cluster-metrics':
            df = get_clustering_metrics(conn, run_id, algorithm=args.algorithm)
            print(f"\nClustering Metrics ({args.algorithm}):")
            print("=" * 80)

        elif args.type == 'cluster-regions':
            if args.cluster_id is None:
                print("Error: --cluster-id is required for cluster-regions queries")
                return 1
            if not args.level:
                args.level = 'county'  # Default to county level
            df = get_regions_in_cluster(conn, run_id, args.cluster_id,
                                       algorithm=args.algorithm, region_level=args.level)
            print(f"\nRegions in Cluster {args.cluster_id} ({args.algorithm}, {args.level}-level):")
            print("=" * 80)

        else:
            print("Error: --type is required (or use --list-runs)")
            return 1

        # Display results
        print(df.to_string(index=False))
        print()

        # Save to CSV if requested
        if args.output:
            df.to_csv(args.output, index=False, encoding='utf-8-sig')
            print(f"Results saved to: {args.output}")

    except Exception as e:
        print(f"Error executing query: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())