#!/usr/bin/env python
"""Phase 17: Semantic Subcategory VTF Analysis.

Uses v4 lexicon (9 parents, 53 subcategories) to generate
semantic_subcategory_* tables with global and regional VTF.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipelines.semantic_subcategory_pipeline import run_semantic_subcategory_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = _PROJECT_ROOT / "data" / "villages.db"
LEXICON_V4_PATH = _PROJECT_ROOT / "data" / "semantic_lexicon_v4.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 17: Semantic subcategory VTF analysis")
    parser.add_argument("--run-id", default=None, help="Accepted for pipeline run tracking")
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--schema", default="guangdong", choices=["guangdong", "national"])
    parser.add_argument("--lexicon-path", default=str(LEXICON_V4_PATH))
    return parser.parse_args()


def main():
    args = parse_args()

    if not Path(args.lexicon_path).exists():
        logger.error(f"v4 lexicon not found: {args.lexicon_path}")
        sys.exit(1)

    try:
        result = run_semantic_subcategory_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            lexicon_path=args.lexicon_path,
            schema_name=args.schema,
        )
        logger.info(f"Done in {result['runtime_seconds']}s")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Phase 17 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
