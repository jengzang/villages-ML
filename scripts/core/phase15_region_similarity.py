#!/usr/bin/env python
"""Phase 15: Region Similarity Analysis.

Computes pairwise similarity between regions based on character frequency patterns.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipelines.region_similarity_pipeline import run_region_similarity_pipeline
from src.schema import REGION_LEVELS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Phase 15: Region Similarity Analysis")
    parser.add_argument("--run-id", default=None, help="Accepted for pipeline run tracking")
    parser.add_argument("--db-path", default=str(Path.cwd() / "data" / "villages.db"))
    parser.add_argument("--region-levels", default=",".join(REGION_LEVELS[:2]),
                        help="Comma-separated region levels to analyze")
    parser.add_argument("--top-k-global", type=int, default=100)
    parser.add_argument("--z-score-threshold", type=float, default=2.0)
    parser.add_argument("--summary-limit", type=int, default=10)

    args = parser.parse_args()
    region_levels = [s.strip() for s in args.region_levels.split(",") if s.strip()]

    try:
        result = run_region_similarity_pipeline(
            db_path=args.db_path,
            region_levels=region_levels,
            top_k_global=args.top_k_global,
            z_score_threshold=args.z_score_threshold,
            summary_limit=args.summary_limit,
        )
        logger.info(f"Done: {result['total_pairs']} pairs in {result['runtime_seconds']}s")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Phase 15 failed: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
