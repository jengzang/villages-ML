#!/usr/bin/env python3
"""
Demo LLM Labeling

Demonstrates the LLM labeling workflow with mock responses.
No API keys required.
"""

import json
import sys
import sqlite3
from pathlib import Path
from collections import defaultdict
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import EmbeddingAnalyzer
from src.nlp.llm_labeler import LabelingResult
from src.nlp.lexicon_expander import LexiconExpander


def load_lexicon(lexicon_path: str) -> dict:
    """Load existing lexicon."""
    with open(lexicon_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["categories"]


def get_unlabeled_characters(db_path: str, lexicon: dict, top_n: int = 20) -> list:
    """Get top N unlabeled characters."""
    lexicon_chars = set()
    for chars in lexicon.values():
        lexicon_chars.update(chars)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 自然村 FROM 广东省自然村
        WHERE 自然村 IS NOT NULL AND 自然村 != ''
    """)

    char_freq = defaultdict(int)
    for row in cursor.fetchall():
        village_name = row[0]
        unique_chars = set(c for c in village_name if '\u4e00' <= c <= '\u9fff')
        for char in unique_chars:
            char_freq[char] += 1

    conn.close()

    unlabeled = [(char, freq) for char, freq in char_freq.items()
                 if char not in lexicon_chars]
    unlabeled.sort(key=lambda x: x[1], reverse=True)

    return unlabeled[:top_n]


def generate_mock_label(char: str, freq: int, similar_chars: list, categories: list, lexicon: dict) -> LabelingResult:
    """Generate mock LLM label based on similar characters."""
    # Try to infer category from similar characters
    category_votes = defaultdict(int)

    for sim_char, sim_score in similar_chars[:5]:
        for cat, chars in lexicon.items():
            if sim_char in chars:
                category_votes[cat] += sim_score

    if category_votes:
        # Pick category with highest vote
        category = max(category_votes.items(), key=lambda x: x[1])[0]
        confidence = min(0.95, max(0.70, category_votes[category] / 2))
    else:
        # Random category
        category = random.choice(categories)
        confidence = 0.75

    reasoning = f"字符'{char}'在{freq}個村莊中出現，與{similar_chars[0][0]}等字符相似，歸類為{category}"

    return LabelingResult(
        char=char,
        category=category,
        confidence=confidence,
        reasoning=reasoning,
        alternative_categories=[],
        is_new_category=False,
    )


def main():
    print("=" * 60)
    print("DEMO: LLM LABELING WORKFLOW")
    print("=" * 60)
    print("\nThis demo shows the complete workflow with mock LLM responses.")
    print("No API keys required.\n")

    # Configuration
    db_path = "data/villages.db"
    lexicon_path = "data/semantic_lexicon_v1.json"
    embedding_run_id = "embed_full_001"
    num_chars = 20

    # Load lexicon
    print(f"Loading lexicon from {lexicon_path}...")
    lexicon = load_lexicon(lexicon_path)
    categories = list(lexicon.keys())
    print(f"Loaded {len(categories)} categories")

    # Get unlabeled characters
    print(f"\nFinding top {num_chars} unlabeled characters...")
    unlabeled = get_unlabeled_characters(db_path, lexicon, num_chars)
    print(f"Found {len(unlabeled)} unlabeled characters")

    print("\nTop 10 unlabeled characters:")
    for i, (char, freq) in enumerate(unlabeled[:10], 1):
        print(f"  {i:2d}. {char} ({freq:,} villages)")

    # Load embeddings
    print(f"\nLoading embeddings (run_id={embedding_run_id})...")
    analyzer = EmbeddingAnalyzer(embedding_run_id, db_path)
    analyzer.load_embeddings()
    print(f"Loaded {len(analyzer.embeddings)} embeddings")

    # Generate mock labels
    print(f"\nGenerating mock LLM labels for {len(unlabeled)} characters...")
    mock_results = []

    for char, freq in unlabeled:
        # Get similar characters
        similar = analyzer.find_similar(char, top_k=10, use_precomputed=True)

        # Generate mock label
        result = generate_mock_label(char, freq, similar, categories, lexicon)
        mock_results.append(result)

    print(f"Generated {len(mock_results)} mock labels")

    # Show sample results
    print("\n" + "=" * 60)
    print("SAMPLE MOCK LABELS")
    print("=" * 60)

    for i, result in enumerate(mock_results[:5], 1):
        print(f"\n{i}. Character: {result.char}")
        print(f"   Category: {result.category}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Reasoning: {result.reasoning}")

    # Expand lexicon
    print("\n" + "=" * 60)
    print("EXPANDING LEXICON")
    print("=" * 60)

    expander = LexiconExpander(lexicon, analyzer.embeddings)

    expanded = expander.add_llm_labels(
        mock_results,
        min_confidence=0.7,
        validate_with_embeddings=True,
        similarity_threshold=0.3,
    )

    # Show results
    print("\n" + expander.generate_report())

    # Coverage stats
    all_chars = set(analyzer.embeddings.keys())
    stats = expander.get_coverage_stats(all_chars)

    print("=" * 60)
    print("COVERAGE IMPROVEMENT")
    print("=" * 60)
    print(f"Before: 97.10% (from Phase 1)")
    print(f"After:  {stats['coverage_rate']:.2%}")
    print(f"Improvement: +{stats['coverage_rate'] - 0.971:.2%}")

    # Save mock results
    output_dir = "results/llm_labels"
    import os
    os.makedirs(output_dir, exist_ok=True)

    output_file = f"{output_dir}/demo_mock_labels.json"
    results_data = [
        {
            "char": r.char,
            "category": r.category,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "alternative_categories": r.alternative_categories,
            "is_new_category": r.is_new_category,
        }
        for r in mock_results
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)

    print(f"\nMock results saved to {output_file}")

    # Save expanded lexicon
    lexicon_output = "data/semantic_lexicon_v2_demo.json"
    expander.export_lexicon(
        lexicon_output,
        version="2.0.0-demo",
        description="Demo expanded lexicon with mock LLM labels"
    )

    print(f"Demo expanded lexicon saved to {lexicon_output}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nThis demo showed the complete workflow:")
    print("  1. Load unlabeled characters")
    print("  2. Generate LLM labels (mocked)")
    print("  3. Validate with embeddings")
    print("  4. Expand lexicon")
    print("  5. Compute coverage statistics")
    print("\nTo run with real LLM:")
    print("  1. Set API key: export DEEPSEEK_API_KEY='sk-...'")
    print("  2. Run: python scripts/llm_label_characters.py --provider deepseek")


if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)
    main()
