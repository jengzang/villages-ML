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
from src.schema import REGION_LEVELS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _parse_int_csv(value: str) -> list[int]:
    if value == "":
        return []
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _parse_str_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


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
    parser.add_argument('--suffix-lengths', default='1,2,3', help='Comma-separated suffix lengths')
    parser.add_argument('--prefix-lengths', default='2,3', help='Comma-separated prefix lengths; empty disables prefixes')
    parser.add_argument('--region-levels', default=','.join(REGION_LEVELS[:3]), help='Comma-separated region levels')
    parser.add_argument('--schema', default='guangdong', choices=['guangdong', 'national'], help='Village table schema')
    parser.add_argument('--chunk-size', type=int, default=10000, help='Village load chunk size')
    parser.add_argument('--min-global-support', type=int, default=20, help='Minimum global support')
    parser.add_argument('--min-regional-support', type=int, default=5, help='Minimum regional support')
    parser.add_argument('--smoothing-alpha', type=float, default=1.0, help='Tendency smoothing alpha')
    parser.add_argument('--no-z-score', action='store_true', help='Disable z-score calculation')
    parser.add_argument('--persist-batch-size', type=int, default=10000, help='Rows to persist per batch')

    args = parser.parse_args()
    suffix_lengths = _parse_int_csv(args.suffix_lengths)
    prefix_lengths = _parse_int_csv(args.prefix_lengths)
    region_levels = _parse_str_csv(args.region_levels)

    logger.info("=" * 60)
    logger.info("Morphology Pattern Analysis Phase")
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Output: {args.output_dir}")
    logger.info("=" * 60)

    config = PipelineConfig.create_default(
        db_path=args.db_path,
        output_dir=args.output_dir,
        run_id=args.run_id,
        schema_name=args.schema,
    )
    config.frequency.region_levels = region_levels
    config.frequency.chunk_size = args.chunk_size
    config.tendency.min_global_support = args.min_global_support
    config.tendency.min_regional_support = args.min_regional_support
    config.tendency.smoothing_alpha = args.smoothing_alpha
    config.tendency.compute_z_score = not args.no_z_score

    pipeline = MorphologyPipeline(
        config,
        suffix_lengths=suffix_lengths,
        prefix_lengths=prefix_lengths,
        persist_batch_size=args.persist_batch_size,
    )
    pipeline.run()

    logger.info("Morphology phase complete.")


if __name__ == '__main__':
    main()
