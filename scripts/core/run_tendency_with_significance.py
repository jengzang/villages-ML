#!/usr/bin/env python
"""Run tendency analysis with statistical significance testing.

Usage:
    python scripts/core/run_tendency_with_significance.py --run-id tendency_v1
    python scripts/core/run_tendency_with_significance.py --run-id tendency_v1 --with-ci
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.schema import REGION_LEVELS
from src.pipelines.tendency_pipeline import run_tendency_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Run tendency analysis with significance testing')
    parser.add_argument('--run-id', type=str, required=True, help='Unique run identifier')
    parser.add_argument('--db-path', type=str, default='data/villages.db', help='Path to database')
    parser.add_argument('--region-levels', type=str, default=','.join(REGION_LEVELS[:3]),
                        help='Comma-separated region levels')
    parser.add_argument('--with-ci', action='store_true', help='Compute confidence intervals')
    parser.add_argument('--min-global-support', type=int, default=20, help='Minimum global village count')
    parser.add_argument('--min-regional-support', type=int, default=5, help='Minimum regional village count')
    parser.add_argument('--normalization-method', type=str, default='percentage',
                        choices=['percentage', 'zscore'],
                        help='Normalization method: percentage (lift) or zscore')
    parser.add_argument('--schema', type=str, default='guangdong', choices=['guangdong', 'national'],
                        help='Village table schema')

    args = parser.parse_args()
    region_levels = [s.strip() for s in args.region_levels.split(',') if s.strip()]

    try:
        result = run_tendency_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            region_levels=region_levels,
            with_ci=args.with_ci,
            min_global_support=args.min_global_support,
            min_regional_support=args.min_regional_support,
            normalization_method=args.normalization_method,
            schema_name=args.schema,
        )
        logger.info(f"Completed in {result['runtime_seconds']}s")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
