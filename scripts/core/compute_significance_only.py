#!/usr/bin/env python
"""Compute statistical significance for existing tendency data.

Usage:
    python scripts/core/compute_significance_only.py --run-id significance_v1
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipelines.tendency_pipeline import run_significance_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Compute statistical significance from existing data')
    parser.add_argument('--run-id', type=str, required=True, help='Run identifier for output')
    parser.add_argument('--db-path', type=str, default='data/villages.db', help='Path to database')
    parser.add_argument('--significance-level', type=float, default=0.05, help='Significance threshold')

    args = parser.parse_args()

    try:
        result = run_significance_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            significance_level=args.significance_level,
        )
        logger.info(f"Done: {result['significant_pairs']:,} significant out of {result['total_pairs']:,}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
