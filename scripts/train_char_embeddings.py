#!/usr/bin/env python3
"""
Train Character Embeddings

Trains Word2Vec embeddings on village name character sequences.

Usage:
    python scripts/train_char_embeddings.py \\
        --run-id embed_001 \\
        --vector-size 100 \\
        --window 3 \\
        --min-count 2 \\
        --epochs 15 \\
        --model-type skipgram \\
        --db-path data/villages.db \\
        --output-dir models/embeddings/
"""

import argparse
import os
import sys
import time
import sqlite3
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import CharacterEmbeddingTrainer, EmbeddingStorage


def load_villages(db_path: str) -> pd.DataFrame:
    """Load village data from database."""
    print(f"Loading villages from {db_path}...")
    conn = sqlite3.connect(db_path)
    # Use preprocessed table with prefix-cleaned names
    df = pd.read_sql_query(
        "SELECT 自然村_去前缀 as 自然村 FROM 广东省自然村_预处理 WHERE 有效 = 1",
        conn
    )
    conn.close()
    print(f"Loaded {len(df)} valid villages (prefix-cleaned)")
    return df


def main():
    parser = argparse.ArgumentParser(description="Train character embeddings")

    # Required arguments
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    parser.add_argument("--db-path", required=True, help="Path to villages database")

    # Model hyperparameters
    parser.add_argument("--vector-size", type=int, default=100,
                       help="Embedding dimension (default: 100)")
    parser.add_argument("--window", type=int, default=3,
                       help="Context window size (default: 3)")
    parser.add_argument("--min-count", type=int, default=2,
                       help="Minimum character frequency (default: 2)")
    parser.add_argument("--epochs", type=int, default=15,
                       help="Number of training epochs (default: 15)")
    parser.add_argument("--model-type", choices=["skipgram", "cbow"], default="skipgram",
                       help="Model type (default: skipgram)")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of parallel workers (default: 4)")
    parser.add_argument("--negative", type=int, default=5,
                       help="Number of negative samples (default: 5)")

    # Output options
    parser.add_argument("--output-dir", default="models/embeddings",
                       help="Output directory for model files")
    parser.add_argument("--precompute-similarities", action="store_true",
                       help="Precompute top-K similarities (slower but enables fast queries)")
    parser.add_argument("--top-k", type=int, default=50,
                       help="Number of top similarities to precompute (default: 50)")
    parser.add_argument("--notes", help="Optional notes about this run")

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Load villages
    villages_df = load_villages(args.db_path)

    # Initialize trainer
    sg = 1 if args.model_type == "skipgram" else 0
    trainer = CharacterEmbeddingTrainer(
        vector_size=args.vector_size,
        window=args.window,
        min_count=args.min_count,
        sg=sg,
        epochs=args.epochs,
        workers=args.workers,
        negative=args.negative,
    )

    # Prepare corpus
    corpus, char_frequencies = trainer.prepare_corpus(villages_df)

    # Train model
    start_time = time.time()
    model = trainer.train(corpus)
    training_time = time.time() - start_time

    # Evaluate model
    metrics = trainer.evaluate_model(model)

    # Save model to disk
    model_path = os.path.join(args.output_dir, f"{args.run_id}.model")
    trainer.save_model(model, model_path)

    # Save to database
    print("\nSaving embeddings to database...")
    storage = EmbeddingStorage(args.db_path)
    with storage:
        storage.create_tables()
        storage.save_run_metadata(
            run_id=args.run_id,
            model=model,
            training_time=training_time,
            corpus_size=len(corpus),
            hyperparameters=trainer.get_hyperparameters(),
            notes=args.notes,
        )
        storage.save_embeddings(args.run_id, model, char_frequencies)

        if args.precompute_similarities:
            print(f"\nPrecomputing top-{args.top_k} similarities...")
            storage.precompute_similarities(args.run_id, model, top_k=args.top_k)

    # Print summary
    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    print(f"Run ID: {args.run_id}")
    print(f"Model type: {args.model_type}")
    print(f"Vector size: {args.vector_size}")
    print(f"Window size: {args.window}")
    print(f"Min count: {args.min_count}")
    print(f"Epochs: {args.epochs}")
    print(f"Corpus size: {len(corpus)} villages")
    print(f"Vocabulary size: {metrics['vocabulary_size']} characters")
    print(f"Training time: {training_time:.2f}s")
    print(f"Model saved to: {model_path}")
    print(f"Embeddings saved to database: {args.db_path}")
    if args.precompute_similarities:
        print(f"Precomputed top-{args.top_k} similarities")
    print("=" * 60)


if __name__ == "__main__":
    main()
