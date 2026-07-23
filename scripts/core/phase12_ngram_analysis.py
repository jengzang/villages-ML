#!/usr/bin/env python
"""Phase 12: N-gram Structure Analysis.

Usage:
    python scripts/core/phase12_ngram_analysis.py --schema guangdong
    python scripts/core/phase12_ngram_analysis.py --n-values 2,3,4 --region-levels city,county
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.schema import REGION_LEVELS, get_schema
from src.pipelines.ngram_pipeline import run_ngram_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _parse_int_csv(value: str) -> list[int]:
    return [int(s.strip()) for s in value.split(',') if s.strip()] if value else []


def _parse_str_csv(value: str) -> list[str]:
    return [s.strip() for s in value.split(',') if s.strip()] if value else []


def _parse_thresholds(value: str) -> dict[int, int]:
    result = {}
    if value:
        for part in value.split(','):
            n_str, t_str = part.split(':')
            result[int(n_str.strip())] = int(t_str.strip())
    return result


def main():
    parser = argparse.ArgumentParser(description="Phase 12: N-gram Structure Analysis")
    parser.add_argument("--db-path", default="data/villages.db", help="Path to database")
    parser.add_argument("--schema", default="guangdong", choices=["guangdong", "national"],
                        help="Village table schema")
    parser.add_argument("--run-id", default=None, help="Run ID for metadata")
    parser.add_argument("--n-values", default="2,3", help="Comma-separated n values")
    parser.add_argument("--region-levels", default=",".join(REGION_LEVELS[:3]),
                        help="Comma-separated regional levels")
    parser.add_argument("--positions", default="prefix,suffix,middle",
                        help="Comma-separated positions")
    parser.add_argument("--min-global-count", type=int, default=10,
                        help="Minimum global frequency")
    parser.add_argument("--min-regional-count-by-n", default="",
                        help="Per-n thresholds, e.g. 2:3,3:2")
    parser.add_argument("--min-tendency-support-by-n", default="",
                        help="Per-n tendency thresholds, e.g. 2:5,3:3")
    parser.add_argument("--skip-village-ngrams", action="store_true",
                        help="Skip village_ngrams generation")
    parser.add_argument("--batch-size", type=int, default=5000,
                        help="Batch size for DB inserts")

    args = parser.parse_args()

    n_values = tuple(_parse_int_csv(args.n_values))
    raw_levels = _parse_str_csv(args.region_levels)
    region_levels = [REGION_LEVELS[int(s)] if s.isdigit() else s for s in raw_levels]
    positions = tuple(_parse_str_csv(args.positions))
    min_regional_freq = _parse_thresholds(args.min_regional_count_by_n) or {2: 3, 3: 2}
    min_tendency_support = _parse_thresholds(args.min_tendency_support_by_n) or {2: 5, 3: 3}

    print("\n" + "=" * 60)
    print("Phase 12: N-gram Structure Analysis")
    print("=" * 60)
    print(f"N values: {n_values}")
    print(f"Regional levels: {region_levels}")
    print(f"Positions: {positions}")

    start_time = datetime.now()
    run_id = args.run_id or f"ngram_{start_time.strftime('%Y%m%d_%H%M%S')}"

    try:
        result = run_ngram_pipeline(
            db_path=args.db_path,
            schema_name=args.schema,
            n_values=n_values,
            region_levels=region_levels,
            positions=positions,
            min_global_freq=args.min_global_count,
            min_regional_freq=min_regional_freq,
            min_tendency_support=min_tendency_support,
            exclude_tables={"village_ngrams"} if args.skip_village_ngrams else None,
            skip_village_ngrams=args.skip_village_ngrams,
            batch_size=args.batch_size,
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\nPhase 12 Complete! Duration: {duration:.1f}s")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Phase 12 failed: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
