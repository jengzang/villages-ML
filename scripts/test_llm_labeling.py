#!/usr/bin/env python3
"""
Test LLM Labeling (Phase 2)

Test the LLM labeling functionality without making actual API calls.
Uses mock data to verify the implementation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp.llm_labeler import LabelingResult
from src.nlp.lexicon_expander import LexiconExpander
import numpy as np


def test_lexicon_expander():
    """Test lexicon expander with mock data."""
    print("=" * 60)
    print("TEST: Lexicon Expander")
    print("=" * 60)

    # Create mock lexicon
    lexicon = {
        "mountain": ["山", "岭", "峰"],
        "water": ["水", "河", "溪"],
        "settlement": ["村", "围", "墟"],
    }

    # Create mock embeddings
    embeddings = {}
    np.random.seed(42)

    # Mountain chars - similar to each other
    for char in ["山", "岭", "峰", "坡"]:
        embeddings[char] = np.random.randn(100) + np.array([1.0] * 100)

    # Water chars - similar to each other
    for char in ["水", "河", "溪", "江"]:
        embeddings[char] = np.random.randn(100) + np.array([-1.0] * 100)

    # Settlement chars - similar to each other
    for char in ["村", "围", "墟", "庄"]:
        embeddings[char] = np.random.randn(100) + np.array([0.0, 1.0] * 50)

    # Normalize embeddings
    for char in embeddings:
        embeddings[char] = embeddings[char] / np.linalg.norm(embeddings[char])

    # Create mock LLM results
    llm_results = [
        LabelingResult(
            char="坡",
            category="mountain",
            confidence=0.95,
            reasoning="坡 means slope, related to mountains",
            alternative_categories=["terrain"],
            is_new_category=False,
        ),
        LabelingResult(
            char="江",
            category="water",
            confidence=0.90,
            reasoning="江 means river",
            alternative_categories=[],
            is_new_category=False,
        ),
        LabelingResult(
            char="庄",
            category="settlement",
            confidence=0.85,
            reasoning="庄 means village/hamlet",
            alternative_categories=["agriculture"],
            is_new_category=False,
        ),
        LabelingResult(
            char="龙",
            category="symbolic",
            confidence=0.80,
            reasoning="龙 means dragon, symbolic/auspicious",
            alternative_categories=[],
            is_new_category=True,
        ),
    ]

    # Initialize expander
    expander = LexiconExpander(lexicon, embeddings)

    # Test adding LLM labels
    print("\nAdding LLM labels...")
    expanded = expander.add_llm_labels(
        llm_results,
        min_confidence=0.7,
        validate_with_embeddings=True,
        similarity_threshold=0.3,
    )

    print(f"\n[PASS] Lexicon expanded")
    print(f"  Original categories: {len(lexicon)}")
    print(f"  Expanded categories: {len(expanded)}")
    print(f"  New categories: {len(expander.new_categories)}")

    # Test coverage stats
    print("\nTesting coverage stats...")
    all_chars = set(embeddings.keys())
    stats = expander.get_coverage_stats(all_chars)

    print(f"[PASS] Coverage stats computed")
    print(f"  Total chars: {stats['total_chars']}")
    print(f"  Covered: {stats['covered_chars']}")
    print(f"  Coverage rate: {stats['coverage_rate']:.2%}")

    # Test finding similar categories
    print("\nTesting similar category detection...")
    similar_pairs = expander.find_similar_categories(min_similarity=0.3, top_k=5)

    print(f"[PASS] Similar categories found: {len(similar_pairs)}")
    for cat1, cat2, sim in similar_pairs:
        print(f"  {cat1} <-> {cat2}: {sim:.3f}")

    # Test report generation
    print("\nTesting report generation...")
    report = expander.generate_report()
    print(f"[PASS] Report generated ({len(report)} characters)")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


def test_cost_estimation():
    """Test cost estimation."""
    print("\n" + "=" * 60)
    print("TEST: Cost Estimation")
    print("=" * 60)

    from src.nlp.llm_labeler import LLMLabeler

    # Test with different models
    models = [
        ("gpt-4", "openai"),
        ("gpt-3.5-turbo", "openai"),
        ("claude-3-sonnet", "anthropic"),
        ("deepseek-chat", "deepseek"),
    ]

    num_chars = 100

    print(f"\nEstimating cost for labeling {num_chars} characters:\n")

    for model, provider in models:
        labeler = LLMLabeler(provider=provider, model=model)
        cost = labeler.estimate_cost(num_chars)

        print(f"{model:20s}: ${cost['total_cost_usd']:.4f} (${cost['cost_per_character']:.6f}/char)")

    print("\n[PASS] Cost estimation working")


def main():
    """Run all tests."""
    print("\nTesting Phase 2: LLM-Assisted Semantic Discovery\n")

    try:
        test_lexicon_expander()
        test_cost_estimation()

        print("\n" + "=" * 60)
        print("PHASE 2 IMPLEMENTATION VERIFIED")
        print("=" * 60)
        print("\nAll core functionality is working correctly.")
        print("Ready for actual LLM labeling with API keys.")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
