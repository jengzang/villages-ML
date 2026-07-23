#!/usr/bin/env python3
"""Phase 14: Semantic Composition Analysis.

Analyzes how semantic categories combine in village names:
1. Extract semantic category sequences
2. Analyze semantic bigrams and trigrams
3. Detect modifier-head patterns
4. Identify semantic conflicts
5. Calculate PMI scores
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.schema import REGION_LEVELS
from src.pipelines.semantic_composition_pipeline import run_semantic_composition_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_project_root = Path(__file__).parent.parent.parent


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 14: Semantic Composition Analysis")
    parser.add_argument("--db-path", default="data/villages.db")
    parser.add_argument("--schema", default="guangdong", choices=["guangdong", "national"])
    parser.add_argument("--run-id", default="semantic_indices_detailed_001")
    parser.add_argument("--lexicon-path", default=str(_project_root / "data" / "semantic_lexicon_v4.json"))
    parser.add_argument("--basic-lexicon-path", default=str(_project_root / "data" / "semantic_lexicon_v1.json"))
    parser.add_argument("--detailed-lexicon-path", default=None,
                        help="Defaults to --lexicon-path")
    parser.add_argument("--conflict-threshold", type=int, default=5,
                        help="Minimum sequence count for unusual conflict detection")
    parser.add_argument("--structure-progress-interval", type=int, default=10000)
    parser.add_argument("--skip-village-structures", action="store_true")
    parser.add_argument("--region-levels", default=",".join(REGION_LEVELS[:3]))
    return parser.parse_args()


def main():
    args = parse_args()
    region_levels = [s.strip() for s in args.region_levels.split(",") if s.strip()]
    detailed_lexicon_path = args.detailed_lexicon_path or args.lexicon_path

    print(f"\nPhase 14: Semantic Composition Analysis")
    print(f"  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        result = run_semantic_composition_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            basic_lexicon_path=args.basic_lexicon_path,
            detailed_lexicon_path=detailed_lexicon_path,
            lexicon_path=args.lexicon_path,
            conflict_threshold=args.conflict_threshold,
            region_levels=region_levels,
            skip_village_structures=args.skip_village_structures,
            structure_progress_interval=args.structure_progress_interval,
            schema_name=args.schema,
        )
        logger.info(f"Done in {result['runtime_seconds']}s")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Phase 14 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
