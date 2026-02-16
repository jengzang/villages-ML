"""
CLI script for generating spatial maps from existing analysis.

Usage:
    python scripts/generate_spatial_maps.py \\
        --run-id spatial_001 \\
        --output-dir results/spatial_001/maps \\
        --map-types clusters,density,hotspots
"""

import argparse
import logging
import sys
import sqlite3
import pandas as pd
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.spatial.map_generator import MapGenerator


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
        description='Generate interactive maps from spatial analysis results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all map types
  python scripts/generate_spatial_maps.py --run-id spatial_001 --output-dir maps

  # Generate specific map types
  python scripts/generate_spatial_maps.py \\
      --run-id spatial_001 \\
      --output-dir maps \\
      --map-types clusters,density
        """
    )

    parser.add_argument(
        '--run-id',
        type=str,
        required=True,
        help='Spatial analysis run ID to visualize'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to SQLite database (default: data/villages.db)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='Output directory for maps'
    )

    parser.add_argument(
        '--map-types',
        type=str,
        default='all',
        help='Comma-separated list of map types: clusters, density, hotspots, all (default: all)'
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

    # Parse map types
    if args.map_types == 'all':
        map_types = ['clusters', 'density', 'hotspots']
    else:
        map_types = [t.strip() for t in args.map_types.split(',')]

    logger.info(f"Generating maps for run_id: {args.run_id}")
    logger.info(f"Map types: {', '.join(map_types)}")
    logger.info(f"Output directory: {args.output_dir}")

    # Create output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(args.db_path)

    try:
        # Load spatial features
        logger.info("Loading spatial features from database...")
        features_query = f"""
            SELECT *
            FROM village_spatial_features
            WHERE run_id = '{args.run_id}'
        """
        features_df = pd.read_sql_query(features_query, conn)

        if len(features_df) == 0:
            logger.error(f"No spatial features found for run_id: {args.run_id}")
            sys.exit(1)

        logger.info(f"Loaded {len(features_df)} villages")

        # Initialize map generator
        map_gen = MapGenerator()

        # Generate cluster map
        if 'clusters' in map_types:
            logger.info("Generating cluster map...")
            map_gen.create_cluster_map(
                features_df,
                str(output_path / 'spatial_clusters.html')
            )
            logger.info(f"  Saved: {output_path / 'spatial_clusters.html'}")

        # Generate density heatmap
        if 'density' in map_types:
            logger.info("Generating density heatmap...")
            map_gen.create_density_heatmap(
                features_df,
                str(output_path / 'density_heatmap.html')
            )
            logger.info(f"  Saved: {output_path / 'density_heatmap.html'}")

        # Generate hotspot map
        if 'hotspots' in map_types:
            logger.info("Generating hotspot map...")

            # Load hotspots
            hotspots_query = f"""
                SELECT *
                FROM spatial_hotspots
                WHERE run_id = '{args.run_id}'
            """
            hotspots_df = pd.read_sql_query(hotspots_query, conn)

            if len(hotspots_df) > 0:
                map_gen.create_hotspot_map(
                    hotspots_df,
                    str(output_path / 'spatial_hotspots.html')
                )
                logger.info(f"  Saved: {output_path / 'spatial_hotspots.html'}")
            else:
                logger.warning("No hotspots found, skipping hotspot map")

        logger.info("\nMap generation complete!")
        logger.info(f"Maps saved to: {output_path}")

    except Exception as e:
        logger.error(f"Map generation failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
