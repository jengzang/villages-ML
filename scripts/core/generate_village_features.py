#!/usr/bin/env python
"""Generate village_features table from preprocessed data.

Thin wrapper — delegates to src/pipelines/feature_materialization_pipeline.py.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipelines.feature_materialization_pipeline import run_feature_generation_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Generate village_features table')
    parser.add_argument('--run-id', type=str, required=True)
    parser.add_argument('--db-path', type=str, default='data/villages.db')
    parser.add_argument('--schema', default='guangdong', choices=['guangdong', 'national'])
    parser.add_argument('--lexicon-path', type=str, default='data/semantic_lexicon_v1.json')
    parser.add_argument('--batch-size', type=int, default=10000)
    args = parser.parse_args()

    try:
        result = run_feature_generation_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            lexicon_path=args.lexicon_path,
            schema_name=args.schema,
            batch_size=args.batch_size,
        )
        logger.info(f"Done: {result['total_villages']} villages in {result['runtime_seconds']}s")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Feature generation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
