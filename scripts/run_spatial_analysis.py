"""
CLI script for running spatial analysis.

Usage:
    python scripts/run_spatial_analysis.py \\
        --run-id spatial_001 \\
        --eps-km 2.0 \\
        --min-samples 5 \\
        --feature-run-id run_002 \\
        --output-dir results/spatial_001 \\
        --generate-maps
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pipelines.spatial_pipeline import run_spatial_analysis_pipeline


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
  # Basic spatial analysis
  python scripts/run_spatial_analysis.py --run-id spatial_001

  # With custom DBSCAN parameters
  python scripts/run_spatial_analysis.py --run-id spatial_002 --eps-km 3.0 --min-samples 10

  # Integrate with semantic features and generate maps
  python scripts/run_spatial_analysis.py \\
      --run-id spatial_003 \\
      --feature-run-id run_002 \\
      --output-dir results/spatial_003 \\
      --generate-maps
        """
    )

    parser.add_argument(
        '--run-id',
        type=str,
        required=True,
        help='Unique identifier for this spatial analysis run'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to SQLite database (default: data/villages.db)'
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
        help='DBSCAN min_samples parameter (default: 5)'
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
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Starting spatial analysis")
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"DBSCAN parameters: eps={args.eps_km}km, min_samples={args.min_samples}")

    if args.feature_run_id:
        logger.info(f"Integrating with semantic features: {args.feature_run_id}")

    if args.generate_maps:
        if not args.output_dir:
            logger.error("--output-dir is required when --generate-maps is specified")
            sys.exit(1)
        logger.info(f"Maps will be saved to: {args.output_dir}")

    try:
        # Run pipeline
        stats = run_spatial_analysis_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            eps_km=args.eps_km,
            min_samples=args.min_samples,
            feature_run_id=args.feature_run_id,
            output_dir=args.output_dir,
            generate_maps=args.generate_maps
        )

        logger.info("\nSpatial analysis complete!")
        logger.info(f"Results saved with run_id: {args.run_id}")
        logger.info(f"Villages analyzed: {stats['n_villages']}")
        logger.info(f"Spatial clusters: {stats['n_clusters']}")
        logger.info(f"Hotspots detected: {stats['n_hotspots']}")
        logger.info(f"Elapsed time: {stats['elapsed_time']:.1f}s")

    except Exception as e:
        logger.error(f"Spatial analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
