"""
CLI script for running spatial analysis.

Usage:
    # Single run (default)
    python scripts/run_spatial_analysis.py --run-id spatial_001 --eps-km 2.0

    # Multi-resolution mode (5 configs)
    python scripts/run_spatial_analysis.py --multi-resolution

    # With HDBSCAN
    python scripts/run_spatial_analysis.py --run-id spatial_hdbscan_v1 --method hdbscan
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pipelines.spatial_pipeline import run_spatial_analysis_pipeline
from src.spatial.coordinate_loader import CHINA_BOUNDS, GUANGDONG_BOUNDS

# Predefined multi-resolution configurations
MULTI_RESOLUTION_CONFIGS = [
    {"run_id": "spatial_eps_05",      "eps_km": 0.5,  "min_samples": 15, "method": "dbscan"},
    {"run_id": "spatial_eps_15",      "eps_km": 1.5,  "min_samples": 25, "method": "dbscan"},
    {"run_id": "spatial_eps_25",      "eps_km": 2.5,  "min_samples": 60, "method": "dbscan"},
    {"run_id": "spatial_eps_45",      "eps_km": 4.5,  "min_samples": 100, "method": "dbscan"},
    {"run_id": "spatial_hdbscan_v2",  "eps_km": 0.0,  "min_samples": 35, "method": "hdbscan"},
]


def parse_multi_resolution_configs(value: str):
    """Parse run_id:method:eps_km:min_samples entries separated by semicolons."""
    configs = []
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 4:
            raise argparse.ArgumentTypeError(
                "Each multi-resolution config must be run_id:method:eps_km:min_samples"
            )
        run_id, method, eps_km, min_samples = parts
        if method not in {"dbscan", "hdbscan"}:
            raise argparse.ArgumentTypeError(f"Unsupported spatial method: {method}")
        configs.append({
            "run_id": run_id,
            "method": method,
            "eps_km": float(eps_km),
            "min_samples": int(min_samples),
        })
    if not configs:
        raise argparse.ArgumentTypeError("At least one multi-resolution config is required")
    return configs


def parse_coordinate_bounds(value: str):
    if value == "guangdong":
        return GUANGDONG_BOUNDS
    if value == "china":
        return CHINA_BOUNDS

    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "Coordinate bounds must be 'guangdong', 'china', or lon_min,lon_max,lat_min,lat_max"
        )
    lon_min, lon_max, lat_min, lat_max = map(float, parts)
    return {
        "lon_min": lon_min,
        "lon_max": lon_max,
        "lat_min": lat_min,
        "lat_max": lat_max,
    }


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    parser = argparse.ArgumentParser(
        description='Run spatial analysis on village data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single run (requires --run-id)
  python scripts/run_spatial_analysis.py --run-id spatial_001

  # Custom DBSCAN parameters
  python scripts/run_spatial_analysis.py --run-id spatial_002 --eps-km 3.0 --min-samples 10

  # HDBSCAN clustering
  python scripts/run_spatial_analysis.py --run-id spatial_hdbscan_v2 --method hdbscan

  # Multi-resolution mode (runs all 5 predefined configs)
  python scripts/run_spatial_analysis.py --multi-resolution
        """
    )

    parser.add_argument(
        '--run-id',
        type=str,
        default=None,
        help='Unique identifier for this spatial analysis run (required unless --multi-resolution)'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to SQLite database (default: data/villages.db)'
    )
    parser.add_argument(
        '--schema',
        default='guangdong',
        choices=['guangdong', 'national'],
        help='Village table schema'
    )
    parser.add_argument(
        '--coordinate-bounds',
        type=parse_coordinate_bounds,
        default=GUANGDONG_BOUNDS,
        help="Coordinate bounds: guangdong, china, or lon_min,lon_max,lat_min,lat_max"
    )

    parser.add_argument(
        '--eps-km',
        type=float,
        default=2.0,
        help='DBSCAN epsilon in kilometers (default: 2.0)'
    )

    parser.add_argument(
        '--min-samples',
        type=int,
        default=5,
        help='DBSCAN min_samples / HDBSCAN min_cluster_size (default: 5)'
    )

    parser.add_argument(
        '--method',
        type=str,
        choices=['dbscan', 'hdbscan'],
        default='dbscan',
        help='Clustering method (default: dbscan)'
    )

    parser.add_argument(
        '--multi-resolution',
        action='store_true',
        help='Run all 5 predefined spatial configurations (eps=0.3/10/20, hdbscan, v2)'
    )
    parser.add_argument(
        '--multi-resolution-configs',
        type=parse_multi_resolution_configs,
        default=MULTI_RESOLUTION_CONFIGS,
        help='Semicolon-separated run_id:method:eps_km:min_samples configs'
    )

    parser.add_argument(
        '--feature-run-id',
        type=str,
        default=None,
        help='Run ID of semantic features to integrate with (optional)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory for maps and exports (optional)'
    )

    parser.add_argument(
        '--generate-maps',
        action='store_true',
        help='Generate interactive folium maps'
    )

    parser.add_argument(
        '--integrate-tendency',
        action='store_true',
        help='After spatial analysis, run spatial-tendency integration for top characters'
    )

    parser.add_argument(
        '--tendency-chars',
        type=int,
        default=100,
        help='Number of top characters to integrate (default: 100)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if not args.multi_resolution and not args.run_id:
        parser.error("--run-id is required (or use --multi-resolution)")

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if args.multi_resolution:
        multi_resolution_configs = args.multi_resolution_configs
        logger.info("=" * 80)
        logger.info("MULTI-RESOLUTION SPATIAL ANALYSIS")
        logger.info(f"Running {len(multi_resolution_configs)} configurations")
        logger.info("=" * 80)

        for i, cfg in enumerate(multi_resolution_configs):
            logger.info(f"\n{'#'*80}")
            logger.info(f"Config {i+1}/{len(multi_resolution_configs)}: {cfg['run_id']}")
            logger.info(f"  method={cfg['method']}, eps_km={cfg['eps_km']}, min_samples={cfg['min_samples']}")
            logger.info(f"{'#'*80}")

            try:
                stats = run_spatial_analysis_pipeline(
                    db_path=args.db_path,
                    run_id=cfg['run_id'],
                    eps_km=cfg['eps_km'],
                    min_samples=cfg['min_samples'],
                    method=cfg['method'],
                    feature_run_id=args.feature_run_id,
                    output_dir=args.output_dir,
                    generate_maps=args.generate_maps and (i == len(multi_resolution_configs) - 1),
                    schema_name=args.schema,
                    coordinate_bounds=args.coordinate_bounds,
                )
                logger.info(f"Config {cfg['run_id']} complete: "
                           f"{stats['n_clusters']} clusters, "
                           f"{stats['elapsed_time']:.1f}s")
            except Exception as e:
                logger.error(f"Config {cfg['run_id']} failed: {e}", exc_info=True)
                logger.warning("Continuing with next configuration...")

        logger.info("\nMulti-resolution spatial analysis complete!")

        # Optional: run spatial-tendency integration after multi-res
        if args.integrate_tendency:
            logger.info("\n" + "=" * 60)
            logger.info("Running spatial-tendency integration...")
            logger.info("=" * 60)

            from src.pipelines.spatial_tendency_integration import run_integration, get_top_characters
            import sqlite3

            conn = sqlite3.connect(args.db_path)
            try:
                characters = get_top_characters(conn, n=args.tendency_chars)
                logger.info(f"Integrating top {len(characters)} characters")
            finally:
                conn.close()

            output_run_id = "spatial_multi_tendency"
            run_integration(
                db_path=args.db_path,
                tendency_run_id="latest",
                spatial_run_id=multi_resolution_configs[-1]['run_id'],
                output_run_id=output_run_id,
                characters=characters
            )
            logger.info("Spatial-tendency integration complete.")

    else:
        logger.info("Starting spatial analysis")
        logger.info(f"Run ID: {args.run_id}")
        logger.info(f"Database: {args.db_path}")
        logger.info(f"Method: {args.method}, eps={args.eps_km}km, min_samples={args.min_samples}")

        if args.feature_run_id:
            logger.info(f"Integrating with semantic features: {args.feature_run_id}")

        if args.generate_maps:
            if not args.output_dir:
                logger.error("--output-dir is required when --generate-maps is specified")
                sys.exit(1)
            logger.info(f"Maps will be saved to: {args.output_dir}")

        try:
            stats = run_spatial_analysis_pipeline(
                db_path=args.db_path,
                run_id=args.run_id,
                eps_km=args.eps_km,
                min_samples=args.min_samples,
                method=args.method,
                feature_run_id=args.feature_run_id,
                output_dir=args.output_dir,
                generate_maps=args.generate_maps,
                schema_name=args.schema,
                coordinate_bounds=args.coordinate_bounds,
            )

            logger.info("\nSpatial analysis complete!")
            logger.info(f"Results saved with run_id: {args.run_id}")
            logger.info(f"Villages analyzed: {stats['n_villages']}")
            logger.info(f"Spatial clusters: {stats['n_clusters']}")
            logger.info(f"Elapsed time: {stats['elapsed_time']:.1f}s")

            # Optional: run spatial-tendency integration
            if args.integrate_tendency:
                logger.info("\n" + "=" * 60)
                logger.info("Running spatial-tendency integration...")
                logger.info("=" * 60)

                from src.pipelines.spatial_tendency_integration import run_integration, get_top_characters
                import sqlite3

                conn = sqlite3.connect(args.db_path)
                try:
                    characters = get_top_characters(conn, n=args.tendency_chars)
                    logger.info(f"Integrating top {len(characters)} characters")
                finally:
                    conn.close()

                output_run_id = f"{args.run_id}_tendency"
                run_integration(
                    db_path=args.db_path,
                    tendency_run_id="latest",
                    spatial_run_id=args.run_id,
                    output_run_id=output_run_id,
                    characters=characters
                )
                logger.info("Spatial-tendency integration complete.")

        except Exception as e:
            logger.error(f"Spatial analysis failed: {e}", exc_info=True)
            sys.exit(1)


if __name__ == '__main__':
    main()
