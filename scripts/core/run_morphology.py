#!/usr/bin/env python
"""
Run morphology pattern analysis pipeline and persist results to database.

This script:
1. Extracts suffix/prefix patterns from village names
2. Computes global and regional pattern frequencies
3. Calculates pattern tendency (lift, z_score)
4. Persists results to pattern_frequency_global and pattern_regional_analysis tables

Usage:
    python scripts/core/run_morphology.py --run-id morphology_v1
    python scripts/core/run_morphology.py --run-id morphology_v1 --db-path data/villages.db --output-dir results/morphology
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import PipelineConfig
from src.pipelines.morphology_pipeline import MorphologyPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Run morphology pattern analysis and persist to database'
    )
    parser.add_argument(
        '--run-id',
        type=str,
        required=True,
        help='Run identifier for this analysis'
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
        default='results/morphology',
        help='Output directory for CSV results (default: results/morphology)'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Morphology Pattern Analysis Phase")
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Output: {args.output_dir}")
    logger.info("=" * 60)

    config = PipelineConfig.create_default(
        db_path=args.db_path,
        output_dir=args.output_dir,
        run_id=args.run_id
    )

    pipeline = MorphologyPipeline(config)
    pipeline.run()

    logger.info("Morphology phase complete.")


if __name__ == '__main__':
    main()
