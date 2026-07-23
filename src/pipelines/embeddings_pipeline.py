"""
Character embedding training pipeline.

Trains Word2Vec embeddings on village name character sequences and stores
them in the database for downstream semantic tasks (similarity queries,
semantic clustering, analogy computation).

Pipeline steps:
1. Load village names from preprocessed table
2. Prepare character sequences as training corpus
3. Train Word2Vec (Skip-gram or CBOW)
4. Evaluate model quality
5. Save model file + persist embeddings to database
6. Optionally precompute top-K character similarities
"""

import logging
import os
import sqlite3
import time
from typing import Any

import pandas as pd

from src.schema import get_schema
from src.nlp import CharacterEmbeddingTrainer, EmbeddingStorage

logger = logging.getLogger(__name__)


def run_embeddings_pipeline(
    db_path: str,
    run_id: str,
    vector_size: int = 100,
    window: int = 3,
    min_count: int = 2,
    epochs: int = 15,
    model_type: str = 'skipgram',
    workers: int = 4,
    negative: int = 5,
    precompute_similarities: bool = False,
    top_k: int = 50,
    output_dir: str = 'models/embeddings',
    schema_name: str = 'guangdong',
    notes: str | None = None,
) -> dict[str, Any]:
    """Train character embeddings on village name character sequences.

    Each village name is treated as a "sentence" of characters. The model
    learns dense vector representations capturing semantic and syntactic
    regularities in character co-occurrence patterns.

    Args:
        db_path: Path to SQLite database.
        run_id: Unique run identifier.
        vector_size: Embedding dimension (typical: 100-300).
        window: Context window — max chars left/right of target (typical: 3-5).
        min_count: Ignore characters appearing fewer than this many times.
        epochs: Training iterations over the corpus (typical: 10-30).
        model_type: 'skipgram' (better for rare chars) or 'cbow' (faster).
        workers: Parallel training threads.
        negative: Number of negative samples per positive (typical: 5-20).
        precompute_similarities: If True, precompute top-K most-similar chars.
        top_k: How many similar chars to store per character.
        output_dir: Directory for the saved .model file.
        schema_name: Village table schema name.
        notes: Optional free-text notes stored in run metadata.
    """
    logger.info("=" * 60)
    logger.info("Character Embedding Training Pipeline")
    logger.info("=" * 60)
    logger.info(f"  Run ID:     {run_id}")
    logger.info(f"  Model:      {model_type}, dim={vector_size}, window={window}")
    logger.info(f"  Training:   {epochs} epochs, min_count={min_count}, negative={negative}")
    logger.info(f"  Workers:    {workers}")
    logger.info(f"  Schema:     {schema_name}")
    logger.info("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Load village names from preprocessed table.
    # Skip rows with zero valid characters (char_count_col = 0).
    logger.info("Step 1: Loading village names...")
    S = get_schema(schema_name)
    conn = sqlite3.connect(db_path)
    villages_df = pd.read_sql_query(
        f"""SELECT {S.village_name_col_prefix_removed} as 自然村
            FROM {S.preprocessed_table}
            WHERE {S.char_count_col} > 0""",
        conn,
    )
    conn.close()
    logger.info(f"  Loaded {len(villages_df):,} village names")

    if len(villages_df) == 0:
        raise ValueError("No villages loaded — check preprocessing and char_count column")

    # Step 2: Initialize trainer with Word2Vec hyperparameters.
    # sg=1 → Skip-gram (predicts context from target, better for rare chars).
    # sg=0 → CBOW (predicts target from context, faster training).
    sg = 1 if model_type == 'skipgram' else 0
    trainer = CharacterEmbeddingTrainer(
        vector_size=vector_size, window=window, min_count=min_count,
        sg=sg, epochs=epochs, workers=workers, negative=negative,
    )

    # Step 3: Prepare corpus — tokenize each village name into character list.
    # Also returns per-character frequency counts for metadata.
    logger.info("Step 2: Preparing training corpus...")
    corpus, char_frequencies = trainer.prepare_corpus(villages_df)
    logger.info(f"  {len(corpus):,} sequences (sentences)")
    logger.info(f"  {len(char_frequencies):,} unique characters")

    # Step 4: Train Word2Vec model.
    logger.info("Step 3: Training Word2Vec model...")
    logger.info(f"  Model type: {model_type}")
    logger.info(f"  Vector size: {vector_size}")
    logger.info(f"  Epochs: {epochs}")
    train_start = time.time()
    model = trainer.train(corpus)
    training_time = time.time() - train_start
    logger.info(f"  Training completed in {training_time:.1f}s")

    # Step 5: Evaluate model quality — vocabulary size, coverage stats.
    logger.info("Step 4: Evaluating model...")
    metrics = trainer.evaluate_model(model)
    logger.info(f"  Vocabulary: {metrics['vocabulary_size']:,} chars")
    logger.info(f"  Training time: {training_time:.1f}s")
    if 'average_similarity' in metrics:
        logger.info(f"  Avg pairwise similarity: {metrics['average_similarity']:.4f}")

    # Step 6: Save model file to disk.
    model_path = os.path.join(output_dir, f"{run_id}.model")
    trainer.save_model(model, model_path)
    file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    logger.info(f"Step 5: Model saved to {model_path} ({file_size_mb:.1f} MB)")

    # Step 7: Persist embeddings to database (char_embeddings table).
    # Each vector dim gets its own column: dim_0, dim_1, ..., dim_N.
    logger.info("Step 6: Saving embeddings to database...")
    storage = EmbeddingStorage(db_path)
    with storage:
        storage.create_tables()
        storage.save_run_metadata(
            run_id=run_id, model=model, training_time=training_time,
            corpus_size=len(corpus), hyperparameters=trainer.get_hyperparameters(),
            notes=notes,
        )
        storage.save_embeddings(run_id, model, char_frequencies)
        logger.info(f"  {len(char_frequencies):,} embeddings written to char_embeddings")

        # Step 8 (optional): Precompute top-K most-similar characters.
        # Stored in char_similarity table for fast API queries.
        if precompute_similarities:
            logger.info(f"Step 7: Precomputing top-{top_k} similarities...")
            sim_start = time.time()
            storage.precompute_similarities(run_id, model, top_k=top_k)
            sim_time = time.time() - sim_start
            logger.info(f"  Similarities computed in {sim_time:.1f}s")

    total_time = time.time() - train_start
    logger.info("=" * 60)
    logger.info("Embeddings pipeline complete")
    logger.info(f"  Total elapsed: {total_time:.1f}s")
    logger.info(f"  Model: {model_path}")
    logger.info("=" * 60)

    return {
        'run_id': run_id,
        'model_type': model_type,
        'vocabulary_size': metrics['vocabulary_size'],
        'training_time_seconds': round(training_time, 2),
        'model_path': model_path,
    }
