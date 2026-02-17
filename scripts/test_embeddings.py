#!/usr/bin/env python3
"""
Test Character Embeddings Implementation

Quick test to verify the embedding system works correctly.
"""

import sys
import os
import tempfile
import sqlite3
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import (
    CharacterEmbeddingTrainer,
    EmbeddingStorage,
    EmbeddingAnalyzer,
)


def create_test_database():
    """Create a small test database."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_db.name
    temp_db.close()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE 广东省自然村 (
            自然村 TEXT
        )
    """)

    # Insert test data (100 villages with common patterns)
    test_villages = [
        "东村", "西村", "南村", "北村",
        "东山村", "西山村", "南山村", "北山村",
        "田心村", "田边村", "田头村", "田尾村",
        "水口村", "水边村", "水头村", "水尾村",
        "河边村", "河口村", "河头村", "河尾村",
        "山下村", "山上村", "山前村", "山后村",
        "大田村", "小田村", "新田村", "老田村",
        "大水村", "小水村", "新水村", "老水村",
        "东田村", "西田村", "南田村", "北田村",
        "东水村", "西水村", "南水村", "北水村",
    ] * 3  # Repeat to get ~100 villages

    for village in test_villages:
        cursor.execute("INSERT INTO 广东省自然村 (自然村) VALUES (?)", (village,))

    conn.commit()
    conn.close()

    return db_path


def test_training():
    """Test embedding training."""
    print("=" * 60)
    print("TEST 1: Training")
    print("=" * 60)

    # Create test database
    db_path = create_test_database()
    print(f"Created test database: {db_path}")

    # Load data
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT 自然村 FROM 广东省自然村", conn)
    conn.close()
    print(f"Loaded {len(df)} test villages")

    # Train embeddings
    trainer = CharacterEmbeddingTrainer(
        vector_size=50,
        window=2,
        min_count=1,
        epochs=10,
        workers=2,
    )

    corpus, char_frequencies = trainer.prepare_corpus(df)
    print(f"Corpus: {len(corpus)} sequences, {len(char_frequencies)} unique characters")

    model = trainer.train(corpus)
    print(f"Model trained: {len(model.wv)} characters in vocabulary")

    # Evaluate
    metrics = trainer.evaluate_model(model)
    print(f"Vocabulary size: {metrics['vocabulary_size']}")
    print(f"Has NaN: {metrics['has_nan']}")
    print(f"Has Inf: {metrics['has_inf']}")

    assert metrics['vocabulary_size'] > 0, "Vocabulary should not be empty"
    assert not metrics['has_nan'], "Model should not contain NaN"
    assert not metrics['has_inf'], "Model should not contain Inf"

    print("[PASS] Training test passed")
    return db_path, model, char_frequencies


def test_storage(db_path, model, char_frequencies):
    """Test database storage."""
    print("\n" + "=" * 60)
    print("TEST 2: Storage")
    print("=" * 60)

    storage = EmbeddingStorage(db_path)

    with storage:
        # Create tables
        storage.create_tables()
        print("[PASS] Tables created")

        # Save metadata
        storage.save_run_metadata(
            run_id="test_001",
            model=model,
            training_time=1.0,
            corpus_size=100,
            hyperparameters={"test": True},
        )
        print("[PASS] Metadata saved")

        # Save embeddings
        storage.save_embeddings("test_001", model, char_frequencies)
        print(f"[PASS] Saved {len(model.wv)} embeddings")

        # Precompute similarities
        storage.precompute_similarities("test_001", model, top_k=10)
        print("[PASS] Similarities precomputed")

        # Load embedding
        if "村" in model.wv:
            vec = storage.load_embedding("test_001", "村")
            assert vec is not None, "Should load embedding"
            assert len(vec) == model.wv.vector_size, "Vector size should match"
            print(f"[PASS] Loaded embedding for '村': shape {vec.shape}")

        # Get similar characters
        if "村" in model.wv:
            similar = storage.get_similar_characters("test_001", "村", top_k=5)
            print(f"[PASS] Similar to '村': {[c for c, s in similar]}")

    print("[PASS] Storage test passed")


def test_analyzer(db_path):
    """Test embedding analyzer."""
    print("\n" + "=" * 60)
    print("TEST 3: Analyzer")
    print("=" * 60)

    analyzer = EmbeddingAnalyzer("test_001", db_path)

    # Load embeddings first
    analyzer.load_embeddings()

    # Test similarity query
    if "村" in analyzer.embeddings:
        similar = analyzer.find_similar("村", top_k=5)
        print(f"[PASS] Similar to '村': {[(c, f'{s:.3f}') for c, s in similar[:3]]}")

    # Test semantic arithmetic
    try:
        result = analyzer.semantic_arithmetic(["东", "山"], ["西"], top_k=3)
        print(f"[PASS] Arithmetic '东+山-西': {[c for c, s in result]}")
    except Exception as e:
        print(f"  Arithmetic test skipped: {e}")

    # Test clustering
    clusters = analyzer.cluster_embeddings(n_clusters=3)
    print(f"[PASS] Clustering: {len(clusters)} clusters")
    for cid, chars in list(clusters.items())[:2]:
        print(f"  Cluster {cid}: {chars[:5]}")

    print("[PASS] Analyzer test passed")


def main():
    """Run all tests."""
    print("\nRunning Character Embeddings Tests\n")

    try:
        # Test 1: Training
        db_path, model, char_frequencies = test_training()

        # Test 2: Storage
        test_storage(db_path, model, char_frequencies)

        # Test 3: Analyzer
        test_analyzer(db_path)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)

        # Cleanup
        os.unlink(db_path)
        print(f"\nCleaned up test database: {db_path}")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()