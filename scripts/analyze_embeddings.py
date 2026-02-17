#!/usr/bin/env python3
"""
Analyze Character Embeddings

Query and analyze trained character embeddings.

Usage:
    # Find similar characters
    python scripts/analyze_embeddings.py --run-id embed_001 --query 田 --top-k 20

    # Semantic arithmetic
    python scripts/analyze_embeddings.py --run-id embed_001 --arithmetic "山+水-石" --top-k 10

    # Analogy
    python scripts/analyze_embeddings.py --run-id embed_001 --analogy "东:西::南:?" --top-k 5

    # Cluster analysis
    python scripts/analyze_embeddings.py --run-id embed_001 --cluster --n-clusters 20

    # Compare with lexicon
    python scripts/analyze_embeddings.py --run-id embed_001 --compare-lexicon data/semantic_lexicon_v1.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import EmbeddingAnalyzer


def print_similar_characters(results, title="Similar Characters"):
    """Print similarity results."""
    print(f"\n{title}:")
    print("-" * 50)
    for i, (char, sim) in enumerate(results, 1):
        print(f"{i:2d}. {char} ({sim:.4f})")


def main():
    parser = argparse.ArgumentParser(description="Analyze character embeddings")

    # Required arguments
    parser.add_argument("--run-id", required=True, help="Embedding run identifier")
    parser.add_argument("--db-path", default="data/villages.db",
                       help="Path to database (default: data/villages.db)")

    # Query modes
    parser.add_argument("--query", help="Find similar characters to this character")
    parser.add_argument("--arithmetic", help="Semantic arithmetic (e.g., '山+水-石')")
    parser.add_argument("--analogy", help="Analogy query (e.g., '东:西::南:?')")
    parser.add_argument("--cluster", action="store_true", help="Perform clustering")
    parser.add_argument("--compare-lexicon", help="Compare with lexicon JSON file")

    # Options
    parser.add_argument("--top-k", type=int, default=20,
                       help="Number of results to return (default: 20)")
    parser.add_argument("--n-clusters", type=int, default=20,
                       help="Number of clusters (default: 20)")
    parser.add_argument("--output", help="Output file for results (JSON)")

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = EmbeddingAnalyzer(args.run_id, args.db_path)

    results = {}

    # Similarity query
    if args.query:
        print(f"Finding characters similar to '{args.query}'...")
        similar = analyzer.find_similar(args.query, top_k=args.top_k)
        print_similar_characters(similar, f"Top {args.top_k} similar to '{args.query}'")
        results["similar"] = similar

    # Semantic arithmetic
    if args.arithmetic:
        print(f"\nSemantic arithmetic: {args.arithmetic}")
        # Parse arithmetic expression
        parts = args.arithmetic.replace("+", " + ").replace("-", " - ").split()
        positive = []
        negative = []
        current_sign = "+"

        for part in parts:
            if part == "+":
                current_sign = "+"
            elif part == "-":
                current_sign = "-"
            else:
                if current_sign == "+":
                    positive.append(part)
                else:
                    negative.append(part)

        similar = analyzer.semantic_arithmetic(positive, negative, top_k=args.top_k)
        print_similar_characters(similar, f"Result of {args.arithmetic}")
        results["arithmetic"] = {
            "expression": args.arithmetic,
            "results": similar,
        }

    # Analogy
    if args.analogy:
        print(f"\nAnalogy: {args.analogy}")
        # Parse analogy (format: a:b::c:?)
        parts = args.analogy.replace("::", ":").split(":")
        if len(parts) >= 3:
            a, b, c = parts[0], parts[1], parts[2]
            similar = analyzer.analogy(a, b, c, top_k=args.top_k)
            print_similar_characters(similar, f"Analogy: {a}:{b}::{c}:?")
            results["analogy"] = {
                "query": args.analogy,
                "results": similar,
            }
        else:
            print("Invalid analogy format. Use: a:b::c:?")

    # Clustering
    if args.cluster:
        print(f"\nClustering into {args.n_clusters} clusters...")
        clusters = analyzer.cluster_embeddings(n_clusters=args.n_clusters)

        print(f"\nCluster Summary:")
        print("-" * 50)
        for cluster_id in sorted(clusters.keys()):
            chars = clusters[cluster_id]
            print(f"Cluster {cluster_id}: {len(chars)} characters")
            print(f"  Sample: {' '.join(chars[:20])}")

        results["clusters"] = {
            cluster_id: chars for cluster_id, chars in clusters.items()
        }

    # Compare with lexicon
    if args.compare_lexicon:
        print(f"\nComparing with lexicon: {args.compare_lexicon}")
        with open(args.compare_lexicon, "r", encoding="utf-8") as f:
            lexicon = json.load(f)

        metrics = analyzer.compare_with_lexicon(lexicon)

        print("\nLexicon Comparison Results:")
        print("-" * 50)
        print(f"Average intra-category similarity: {metrics['summary']['avg_intra_category_similarity']:.4f}")
        print(f"Average inter-category similarity: {metrics['summary']['avg_inter_category_similarity']:.4f}")
        print(f"Average coverage: {metrics['summary']['avg_coverage']:.2%}")

        print("\nIntra-category similarities:")
        for category, sim in sorted(metrics["intra_category_similarity"].items(),
                                    key=lambda x: x[1], reverse=True):
            print(f"  {category}: {sim:.4f}")

        results["lexicon_comparison"] = metrics

    # Save results
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()