#!/usr/bin/env python3
"""
Analyze Embedding Quality

Compute quantitative metrics for embedding quality.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import EmbeddingAnalyzer

def main():
    run_id = "embed_full_001"
    db_path = "data/villages.db"
    lexicon_path = "data/semantic_lexicon_v1.json"

    # Load lexicon
    with open(lexicon_path, "r", encoding="utf-8") as f:
        lexicon_data = json.load(f)
    lexicon = lexicon_data["categories"]

    # Initialize analyzer
    analyzer = EmbeddingAnalyzer(run_id, db_path)

    # Compare with lexicon
    print("Computing lexicon comparison metrics...")
    metrics = analyzer.compare_with_lexicon(lexicon)

    # Save results
    output_path = "results/embeddings/quality_metrics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("EMBEDDING QUALITY METRICS")
    print("=" * 60)
    print(f"Average intra-category similarity: {metrics['summary']['avg_intra_category_similarity']:.4f}")
    print(f"Average inter-category similarity: {metrics['summary']['avg_inter_category_similarity']:.4f}")
    print(f"Average coverage: {metrics['summary']['avg_coverage']:.2%}")

    print("\nIntra-category similarities (higher is better):")
    for category, sim in sorted(metrics["intra_category_similarity"].items(),
                                key=lambda x: x[1], reverse=True):
        print(f"  {category:15s}: {sim:.4f}")

    print("\nCategory coverage:")
    for category, cov in sorted(metrics["category_coverage"].items(),
                                key=lambda x: x[1], reverse=True):
        print(f"  {category:15s}: {cov:.2%}")

    # Test some analogies
    print("\n" + "=" * 60)
    print("ANALOGY TESTS")
    print("=" * 60)

    test_analogies = [
        ("东", "西", "南"),  # Should return 北
        ("上", "下", "前"),  # Should return 后
        ("山", "岭", "水"),  # Should return river-related
    ]

    for a, b, c in test_analogies:
        try:
            results = analyzer.analogy(a, b, c, top_k=5)
            print(f"\n{a}:{b}::{c}:?")
            for i, (char, sim) in enumerate(results, 1):
                print(f"  {i}. {char} ({sim:.4f})")
        except Exception as e:
            print(f"\n{a}:{b}::{c}:? - Error: {e}")

    # Test semantic arithmetic
    print("\n" + "=" * 60)
    print("SEMANTIC ARITHMETIC TESTS")
    print("=" * 60)

    test_arithmetic = [
        (["山", "水"], []),
        (["田", "地"], []),
        (["东", "南"], ["西"]),
    ]

    for positive, negative in test_arithmetic:
        try:
            expr = "+".join(positive)
            if negative:
                expr += "-" + "-".join(negative)
            results = analyzer.semantic_arithmetic(positive, negative, top_k=5)
            print(f"\n{expr}:")
            for i, (char, sim) in enumerate(results, 1):
                print(f"  {i}. {char} ({sim:.4f})")
        except Exception as e:
            print(f"\n{expr}: Error: {e}")

if __name__ == "__main__":
    main()
