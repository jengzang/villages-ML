#!/usr/bin/env python3
"""Train Character Embeddings on village name character sequences.

Usage:
    python scripts/core/train_char_embeddings.py --run-id embed_001 --db-path data/villages.db
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipelines.embeddings_pipeline import run_embeddings_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Train character embeddings")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    parser.add_argument("--db-path", required=True, help="Path to villages database")
    parser.add_argument("--schema", default="guangdong", choices=["guangdong", "national"],
                        help="Village table schema")
    parser.add_argument("--vector-size", type=int, default=100, help="Embedding dimension")
    parser.add_argument("--window", type=int, default=3, help="Context window size")
    parser.add_argument("--min-count", type=int, default=2, help="Minimum character frequency")
    parser.add_argument("--epochs", type=int, default=15, help="Training epochs")
    parser.add_argument("--model-type", choices=["skipgram", "cbow"], default="skipgram",
                        help="Model type")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    parser.add_argument("--negative", type=int, default=5, help="Negative samples")
    parser.add_argument("--output-dir", default="models/embeddings", help="Output directory")
    parser.add_argument("--precompute-similarities", action="store_true",
                        help="Precompute top-K similarities")
    parser.add_argument("--top-k", type=int, default=50, help="Top similarities to precompute")
    parser.add_argument("--notes", help="Optional run notes")

    args = parser.parse_args()

    try:
        result = run_embeddings_pipeline(
            db_path=args.db_path,
            run_id=args.run_id,
            vector_size=args.vector_size,
            window=args.window,
            min_count=args.min_count,
            epochs=args.epochs,
            model_type=args.model_type,
            workers=args.workers,
            negative=args.negative,
            precompute_similarities=args.precompute_similarities,
            top_k=args.top_k,
            output_dir=args.output_dir,
            schema_name=args.schema,
            notes=args.notes,
        )
        logger.info(f"Done: vocab={result['vocabulary_size']}, time={result['training_time_seconds']}s")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
