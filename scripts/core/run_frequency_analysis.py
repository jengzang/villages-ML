"""Entry point script for character frequency analysis."""

import argparse
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import PipelineConfig
from src.utils.logging_config import setup_logging
from src.pipelines.frequency_pipeline import CharacterFrequencyPipeline


def _split_csv_values(value: str):
    return [item.strip() for item in value.split(",") if item.strip()]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Character frequency analysis for Guangdong village names"
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
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    parser.add_argument('--region-levels', default='city,county,township', help='Comma-separated region levels')
    parser.add_argument('--chunk-size', type=int, default=10000, help='Village load chunk size')
    parser.add_argument('--persist-batch-size', type=int, default=10000, help='Rows to persist per DB batch')
    parser.add_argument('--min-global-support', type=int, default=20, help='Minimum global support')
    parser.add_argument('--min-regional-support', type=int, default=5, help='Minimum regional support')
    parser.add_argument('--smoothing-alpha', type=float, default=1.0, help='Tendency smoothing alpha')
    parser.add_argument('--no-z-score', action='store_true', help='Disable z-score calculation')

    args = parser.parse_args()

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

    config.frequency.region_levels = _split_csv_values(args.region_levels)
    config.frequency.chunk_size = args.chunk_size
    config.frequency.persist_batch_size = args.persist_batch_size
    config.tendency.min_global_support = args.min_global_support
    config.tendency.min_regional_support = args.min_regional_support
    config.tendency.smoothing_alpha = args.smoothing_alpha
    config.tendency.compute_z_score = not args.no_z_score

    # Validate configuration
    try:
        config.validate()
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        sys.exit(1)

    # Setup logging
    log_file = Path(config.output_dir) / config.run_id / "pipeline.log"
    log_level = getattr(logging, args.log_level)
    setup_logging(log_file=str(log_file), level=log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting character frequency analysis")
    logger.info(f"Configuration: {config.to_dict()}")

    # Run pipeline
    try:
        pipeline = CharacterFrequencyPipeline(config)
        pipeline.run()
        print(f"\nPipeline completed successfully!")
        print(f"Results saved to: {Path(config.output_dir) / config.run_id}")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\nPipeline failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
