"""
Command-line script to run semantic analysis pipeline.

Usage:
    python scripts/run_semantic_analysis.py --char-run-id run_002 --output-run-id semantic_001
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipelines.semantic_pipeline import run_semantic_analysis_pipeline


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
        description='Run semantic analysis pipeline on village names'
    )

    parser.add_argument(
        '--char-run-id',
        type=str,
        required=True,
        help='Character frequency run ID to use as input (e.g., run_002)'
    )

    parser.add_argument(
        '--output-run-id',
        type=str,
        required=True,
        help='Output run ID for semantic analysis (e.g., semantic_001)'
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
        help='Path to semantic lexicon JSON (default: data/semantic_lexicon_v1.json)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory for CSV exports (optional)'
    )

    parser.add_argument(
        '--region-levels',
        type=str,
        nargs='+',
        default=['city', 'county', 'township'],
        help='Region levels to analyze (default: city county township)'
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
    logger.info("Starting semantic analysis pipeline")
    logger.info(f"Arguments: {vars(args)}")

    try:
        run_semantic_analysis_pipeline(
            db_path=args.db_path,
            char_run_id=args.char_run_id,
            output_run_id=args.output_run_id,
            lexicon_path=args.lexicon_path,
            region_levels=args.region_levels,
            output_dir=args.output_dir
        )

        logger.info("Semantic analysis pipeline completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
