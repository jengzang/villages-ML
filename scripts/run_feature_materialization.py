"""
Feature materialization pipeline runner.

Materializes village-level features into database for fast deployment queries.

Usage:
    python scripts/run_feature_materialization.py \\
        --run-id feature_001 \\
        --clustering-run-id village_cluster_001 \\
        --output-dir results/feature_001
"""

import argparse
import logging
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipelines.feature_materialization_pipeline import run_feature_materialization_pipeline


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
        description='Run feature materialization pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--run-id',
        type=str,
        required=True,
        help='Run identifier for this materialization'
    )

    parser.add_argument(
        '--clustering-run-id',
        type=str,
        default=None,
        help='Run identifier for clustering results (optional)'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to SQLite database (default: data/villages.db)'
    )

    parser.add_argument(
        '--lexicon-path',
        type=str,
        default='data/semantic_lexicon_v1.json',
        help='Path to semantic lexicon JSON file (default: data/semantic_lexicon_v1.json)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory for CSV exports (optional)'
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

    logger.info("=" * 80)
    logger.info("Feature Materialization Pipeline")
    logger.info("=" * 80)
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Clustering Run ID: {args.clustering_run_id}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Lexicon: {args.lexicon_path}")
    logger.info(f"Output Directory: {args.output_dir}")
    logger.info("=" * 80)

    try:
        # Run pipeline
        stats = run_feature_materialization_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            clustering_run_id=args.clustering_run_id,
            lexicon_path=args.lexicon_path,
            output_dir=args.output_dir
        )

        # Print summary
        logger.info("=" * 80)
        logger.info("Pipeline Summary")
        logger.info("=" * 80)
        logger.info(f"Total Villages: {stats['total_villages']:,}")
        logger.info(f"Average Name Length: {stats['avg_name_length']:.2f}")
        logger.info(f"Runtime: {stats['runtime_seconds']:.2f} seconds")
        logger.info("")
        logger.info("Semantic Tag Counts:")
        for category, count in stats['semantic_tag_counts'].items():
            pct = (count / stats['total_villages']) * 100
            logger.info(f"  {category:15s}: {count:6,} ({pct:5.2f}%)")
        logger.info("=" * 80)

        # Save stats to JSON
        if args.output_dir:
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            stats_path = output_path / f"stats_{args.run_id}.json"
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved statistics to {stats_path}")

        logger.info("Pipeline completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

