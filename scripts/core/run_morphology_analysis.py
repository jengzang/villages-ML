"""Entry point script for morphology pattern analysis."""

import argparse
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PipelineConfig
from src.utils.logging_config import setup_logging
from src.pipelines.morphology_pipeline import MorphologyPipeline


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Morphology pattern analysis for Guangdong village names"
    )

    parser.add_argument(
        '--run-id',
        type=str,
        help='Run identifier (default: auto-generated timestamp)'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration JSON file'
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
        default='results',
        help='Output directory (default: results)'
    )

    parser.add_argument(
        '--suffix-lengths',
        type=str,
        default='1,2,3',
        help='Comma-separated suffix n-gram lengths (default: 1,2,3)'
    )

    parser.add_argument(
        '--prefix-lengths',
        type=str,
        default='2,3',
        help='Comma-separated prefix n-gram lengths (default: 2,3)'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Parse suffix and prefix lengths
    suffix_lengths = [int(x.strip()) for x in args.suffix_lengths.split(',')]
    prefix_lengths = [int(x.strip()) for x in args.prefix_lengths.split(',')]

    # Load or create configuration
    if args.config:
        print(f"Loading configuration from {args.config}")
        config = PipelineConfig.load(args.config)
    else:
        print("Creating default configuration")
        config = PipelineConfig.create_default(
            db_path=args.db_path,
            output_dir=args.output_dir,
            run_id=args.run_id
        )

    # Validate configuration
    try:
        config.validate()
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        sys.exit(1)

    # Setup logging
    log_file = Path(config.output_dir) / config.run_id / "morphology_pipeline.log"
    log_level = getattr(logging, args.log_level)
    setup_logging(log_file=str(log_file), level=log_level)

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Morphology Pattern Analysis")
    logger.info("=" * 80)
    logger.info(f"Run ID: {config.run_id}")
    logger.info(f"Database: {config.db_path}")
    logger.info(f"Output directory: {config.output_dir}")
    logger.info(f"Suffix lengths: {suffix_lengths}")
    logger.info(f"Prefix lengths: {prefix_lengths}")
    logger.info("=" * 80)

    # Create and run pipeline
    try:
        pipeline = MorphologyPipeline(
            config=config,
            suffix_lengths=suffix_lengths,
            prefix_lengths=prefix_lengths
        )
        pipeline.run()

        logger.info("\n" + "=" * 80)
        logger.info("SUCCESS: Morphology analysis completed")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\nERROR: Pipeline failed - {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
