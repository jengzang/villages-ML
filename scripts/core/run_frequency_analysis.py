"""Entry point script for character frequency analysis."""

import argparse
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PipelineConfig
from src.utils.logging_config import setup_logging
from src.pipelines.frequency_pipeline import CharacterFrequencyPipeline


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
