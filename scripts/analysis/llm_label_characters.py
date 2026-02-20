#!/usr/bin/env python3
"""
LLM Label Characters

Use LLM to label unlabeled characters in the corpus.

Usage:
    python scripts/llm_label_characters.py \\
        --run-id llm_001 \\
        --provider openai \\
        --model gpt-4 \\
        --top-n 100 \\
        --output results/llm_labels/
"""

import argparse
import json
import sys
import sqlite3
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import EmbeddingAnalyzer
from src.nlp.llm_labeler import LLMLabeler


def load_lexicon(lexicon_path: str) -> dict:
    """Load existing lexicon."""
    with open(lexicon_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["categories"]


def get_unlabeled_characters(
    db_path: str,
    lexicon: dict,
    top_n: int = 100,
) -> list:
    """
    Get top N unlabeled characters by frequency.

    Args:
        db_path: Path to database
        lexicon: Existing lexicon
        top_n: Number of characters to return

    Returns:
        List of (char, frequency) tuples
    """
    # Get all lexicon characters
    lexicon_chars = set()
    for chars in lexicon.values():
        lexicon_chars.update(chars)

    # Load character frequencies from database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count villages containing each character
    cursor.execute("""
        SELECT 自然村 FROM 广东省自然村
        WHERE 自然村 IS NOT NULL AND 自然村 != ''
    """)

    char_freq = defaultdict(int)
    for row in cursor.fetchall():
        village_name = row[0]
        # Deduplicate characters within village
        unique_chars = set(c for c in village_name if '\u4e00' <= c <= '\u9fff')
        for char in unique_chars:
            char_freq[char] += 1

    conn.close()

    # Filter unlabeled characters
    unlabeled = [(char, freq) for char, freq in char_freq.items()
                 if char not in lexicon_chars]

    # Sort by frequency descending
    unlabeled.sort(key=lambda x: x[1], reverse=True)

    return unlabeled[:top_n]


def get_example_villages(db_path: str, char: str, limit: int = 5) -> list:
    """Get example village names containing the character."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 自然村 FROM 广东省自然村
        WHERE 自然村 LIKE ?
        LIMIT ?
    """, (f"%{char}%", limit))

    villages = [row[0] for row in cursor.fetchall()]
    conn.close()

    return villages


def main():
    parser = argparse.ArgumentParser(description="Label characters using LLM")

    # Required arguments
    parser.add_argument("--run-id", required=True, help="Run identifier")
    parser.add_argument("--db-path", default="data/villages.db",
                       help="Path to database")
    parser.add_argument("--lexicon", default="data/semantic_lexicon_v1.json",
                       help="Path to existing lexicon")
    parser.add_argument("--embedding-run-id", default="embed_full_001",
                       help="Embedding run ID for similarity")

    # LLM configuration
    parser.add_argument("--provider", default="openai",
                       choices=["openai", "anthropic", "deepseek", "local"],
                       help="LLM provider")
    parser.add_argument("--model", default="gpt-4",
                       help="Model name")
    parser.add_argument("--api-key", help="API key (or use environment variable)")
    parser.add_argument("--base-url", help="Base URL for local models")

    # Labeling options
    parser.add_argument("--top-n", type=int, default=100,
                       help="Number of top unlabeled characters to label")
    parser.add_argument("--rate-limit-delay", type=float, default=1.0,
                       help="Delay between API calls (seconds)")
    parser.add_argument("--estimate-cost-only", action="store_true",
                       help="Only estimate cost, don't run labeling")

    # Output
    parser.add_argument("--output-dir", default="results/llm_labels",
                       help="Output directory")

    args = parser.parse_args()

    # Create output directory
    import os
    os.makedirs(args.output_dir, exist_ok=True)

    # Load lexicon
    print(f"Loading lexicon from {args.lexicon}...")
    lexicon = load_lexicon(args.lexicon)
    existing_categories = list(lexicon.keys())
    print(f"Loaded {len(existing_categories)} categories")

    # Get unlabeled characters
    print(f"\nFinding top {args.top_n} unlabeled characters...")
    unlabeled = get_unlabeled_characters(args.db_path, lexicon, args.top_n)
    print(f"Found {len(unlabeled)} unlabeled characters")

    if not unlabeled:
        print("No unlabeled characters found!")
        return

    # Show top 10
    print("\nTop 10 unlabeled characters:")
    for i, (char, freq) in enumerate(unlabeled[:10], 1):
        print(f"  {i:2d}. {char} ({freq} villages)")

    # Initialize LLM labeler
    print(f"\nInitializing LLM labeler (provider={args.provider}, model={args.model})...")
    labeler = LLMLabeler(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
        temperature=0.0,
    )

    # Estimate cost
    cost_estimate = labeler.estimate_cost(len(unlabeled))
    print("\n" + "=" * 60)
    print("COST ESTIMATE")
    print("=" * 60)
    print(f"Characters to label: {cost_estimate['num_characters']}")
    print(f"Total input tokens: {cost_estimate['total_input_tokens']:,}")
    print(f"Total output tokens: {cost_estimate['total_output_tokens']:,}")
    print(f"Input cost: ${cost_estimate['input_cost_usd']:.4f}")
    print(f"Output cost: ${cost_estimate['output_cost_usd']:.4f}")
    print(f"Total cost: ${cost_estimate['total_cost_usd']:.4f}")
    print(f"Cost per character: ${cost_estimate['cost_per_character']:.6f}")
    print("=" * 60)

    if args.estimate_cost_only:
        print("\nCost estimation complete. Exiting.")
        return

    # Confirm before proceeding
    response = input("\nProceed with labeling? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        return

    # Load embeddings for similarity
    print(f"\nLoading embeddings (run_id={args.embedding_run_id})...")
    analyzer = EmbeddingAnalyzer(args.embedding_run_id, args.db_path)
    analyzer.load_embeddings()

    # Prepare character data
    print("\nPreparing character data...")
    characters_data = []

    for char, freq in unlabeled:
        # Get example villages
        examples = get_example_villages(args.db_path, char, limit=5)

        # Get similar characters from embeddings
        similar = analyzer.find_similar(char, top_k=10, use_precomputed=True)

        characters_data.append({
            "char": char,
            "frequency": freq,
            "example_villages": examples,
            "similar_chars": similar,
        })

    # Run batch labeling
    print(f"\nLabeling {len(characters_data)} characters...")
    print("This may take a while...")

    results = labeler.batch_label_characters(
        characters_data,
        existing_categories,
        rate_limit_delay=args.rate_limit_delay,
    )

    # Save results
    output_file = f"{args.output_dir}/{args.run_id}_labels.json"
    results_data = [
        {
            "char": r.char,
            "category": r.category,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "alternative_categories": r.alternative_categories,
            "is_new_category": r.is_new_category,
        }
        for r in results
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {output_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("LABELING SUMMARY")
    print("=" * 60)
    print(f"Characters labeled: {len(results)}/{len(unlabeled)}")
    print(f"Average confidence: {sum(r.confidence for r in results) / len(results):.3f}")

    # Count by category
    category_counts = defaultdict(int)
    for r in results:
        category_counts[r.category] += 1

    print("\nLabels by category:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category:20s}: {count:3d} characters")

    # New categories
    new_categories = [r for r in results if r.is_new_category]
    if new_categories:
        print(f"\nNew categories suggested: {len(new_categories)}")
        for r in new_categories:
            print(f"  {r.category}: {r.char}")

    print("=" * 60)


if __name__ == "__main__":
    main()
