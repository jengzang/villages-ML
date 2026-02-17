#!/usr/bin/env python3
"""
Expand Lexicon

Expand semantic lexicon using LLM labels and embedding validation.

Usage:
    python scripts/expand_lexicon.py \\
        --llm-labels results/llm_labels/llm_001_labels.json \\
        --lexicon data/semantic_lexicon_v1.json \\
        --embedding-run-id embed_full_001 \\
        --output data/semantic_lexicon_v2.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import EmbeddingAnalyzer
from src.nlp.llm_labeler import LabelingResult
from src.nlp.lexicon_expander import LexiconExpander


def load_llm_labels(labels_path: str) -> list:
    """Load LLM labeling results."""
    with open(labels_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for item in data:
        results.append(LabelingResult(
            char=item["char"],
            category=item["category"],
            confidence=item["confidence"],
            reasoning=item["reasoning"],
            alternative_categories=item.get("alternative_categories", []),
            is_new_category=item.get("is_new_category", False),
        ))

    return results


def load_lexicon(lexicon_path: str) -> dict:
    """Load existing lexicon."""
    with open(lexicon_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["categories"]


def main():
    parser = argparse.ArgumentParser(description="Expand lexicon with LLM labels")

    # Required arguments
    parser.add_argument("--llm-labels", required=True,
                       help="Path to LLM labeling results JSON")
    parser.add_argument("--lexicon", required=True,
                       help="Path to existing lexicon JSON")
    parser.add_argument("--output", required=True,
                       help="Output path for expanded lexicon")

    # Validation options
    parser.add_argument("--embedding-run-id", default="embed_full_001",
                       help="Embedding run ID for validation")
    parser.add_argument("--db-path", default="data/villages.db",
                       help="Path to database")
    parser.add_argument("--min-confidence", type=float, default=0.7,
                       help="Minimum confidence to accept label")
    parser.add_argument("--similarity-threshold", type=float, default=0.3,
                       help="Minimum similarity to category")
    parser.add_argument("--validate-with-embeddings", action="store_true",
                       help="Validate labels with embeddings")

    # Analysis options
    parser.add_argument("--find-similar-categories", action="store_true",
                       help="Find similar categories (potential merges)")
    parser.add_argument("--show-coverage", action="store_true",
                       help="Show coverage statistics")

    args = parser.parse_args()

    # Load existing lexicon
    print(f"Loading lexicon from {args.lexicon}...")
    lexicon = load_lexicon(args.lexicon)
    print(f"Loaded {len(lexicon)} categories, {sum(len(chars) for chars in lexicon.values())} characters")

    # Load LLM labels
    print(f"\nLoading LLM labels from {args.llm_labels}...")
    llm_results = load_llm_labels(args.llm_labels)
    print(f"Loaded {len(llm_results)} LLM labels")

    # Load embeddings if validation enabled
    embeddings = None
    if args.validate_with_embeddings:
        print(f"\nLoading embeddings (run_id={args.embedding_run_id})...")
        analyzer = EmbeddingAnalyzer(args.embedding_run_id, args.db_path)
        analyzer.load_embeddings()
        embeddings = analyzer.embeddings
        print(f"Loaded {len(embeddings)} embeddings")

    # Initialize expander
    expander = LexiconExpander(lexicon, embeddings)

    # Add LLM labels
    print("\n" + "=" * 60)
    print("EXPANDING LEXICON")
    print("=" * 60)

    expanded_lexicon = expander.add_llm_labels(
        llm_results,
        min_confidence=args.min_confidence,
        validate_with_embeddings=args.validate_with_embeddings,
        similarity_threshold=args.similarity_threshold,
    )

    # Show coverage if requested
    if args.show_coverage and embeddings:
        print("\n" + "=" * 60)
        print("COVERAGE STATISTICS")
        print("=" * 60)

        all_chars = set(embeddings.keys())
        stats = expander.get_coverage_stats(all_chars)

        print(f"Total characters in corpus: {stats['total_chars']}")
        print(f"Covered by lexicon: {stats['covered_chars']} ({stats['coverage_rate']:.2%})")
        print(f"Uncovered: {stats['uncovered_chars']}")
        print(f"Number of categories: {stats['num_categories']}")
        print(f"Average category size: {stats['avg_category_size']:.1f}")

    # Find similar categories if requested
    if args.find_similar_categories and embeddings:
        print("\n" + "=" * 60)
        print("SIMILAR CATEGORIES (Potential Merges)")
        print("=" * 60)

        similar_pairs = expander.find_similar_categories(min_similarity=0.4, top_k=10)

        if similar_pairs:
            for cat1, cat2, sim in similar_pairs:
                print(f"  {cat1:20s} <-> {cat2:20s} ({sim:.3f})")
        else:
            print("  No similar category pairs found")

    # Export expanded lexicon
    print(f"\nExporting expanded lexicon to {args.output}...")
    expander.export_lexicon(
        args.output,
        version="2.0.0",
        description="Expanded lexicon with LLM-generated labels and embedding validation"
    )

    # Generate report
    print("\n" + expander.generate_report())

    print(f"\nExpanded lexicon saved to {args.output}")


if __name__ == "__main__":
    main()
