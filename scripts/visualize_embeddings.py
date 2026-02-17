#!/usr/bin/env python3
"""
Visualize Character Embeddings

Generate interactive visualizations of character embeddings.

Usage:
    # t-SNE visualization
    python scripts/visualize_embeddings.py --run-id embed_001 --method tsne --output results/tsne.html

    # UMAP visualization
    python scripts/visualize_embeddings.py --run-id embed_001 --method umap --output results/umap.html

    # Similarity heatmap
    python scripts/visualize_embeddings.py --run-id embed_001 --heatmap --characters "田,地,园,山,水,河" --output results/heatmap.html

    # Category visualization
    python scripts/visualize_embeddings.py --run-id embed_001 --categories --lexicon data/semantic_lexicon_v1.json --output results/categories.html
"""

import argparse
import json
import sys
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp import EmbeddingVisualizer


def load_char_frequencies(db_path: str) -> dict:
    """Load character frequencies from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count villages containing each character
    cursor.execute("""
        SELECT 自然村 FROM 广东省自然村
        WHERE 自然村 IS NOT NULL AND 自然村 != ''
    """)

    char_freq = {}
    for row in cursor.fetchall():
        village_name = row[0]
        # Deduplicate characters within village
        unique_chars = set(c for c in village_name if '\u4e00' <= c <= '\u9fff')
        for char in unique_chars:
            char_freq[char] = char_freq.get(char, 0) + 1

    conn.close()
    return char_freq


def main():
    parser = argparse.ArgumentParser(description="Visualize character embeddings")

    # Required arguments
    parser.add_argument("--run-id", required=True, help="Embedding run identifier")
    parser.add_argument("--db-path", default="data/villages.db",
                       help="Path to database (default: data/villages.db)")
    parser.add_argument("--output", required=True, help="Output HTML file path")

    # Visualization modes
    parser.add_argument("--method", choices=["tsne", "umap"],
                       help="Dimensionality reduction method")
    parser.add_argument("--heatmap", action="store_true",
                       help="Create similarity heatmap")
    parser.add_argument("--categories", action="store_true",
                       help="Visualize category distribution")

    # Options
    parser.add_argument("--color-by", choices=["lexicon", "frequency"], default="lexicon",
                       help="Color scheme (default: lexicon)")
    parser.add_argument("--lexicon", help="Path to lexicon JSON file")
    parser.add_argument("--characters", help="Comma-separated list of characters for heatmap")

    # t-SNE parameters
    parser.add_argument("--perplexity", type=int, default=30,
                       help="t-SNE perplexity (default: 30)")
    parser.add_argument("--n-iter", type=int, default=1000,
                       help="t-SNE iterations (default: 1000)")

    # UMAP parameters
    parser.add_argument("--n-neighbors", type=int, default=15,
                       help="UMAP n_neighbors (default: 15)")
    parser.add_argument("--min-dist", type=float, default=0.1,
                       help="UMAP min_dist (default: 0.1)")

    args = parser.parse_args()

    # Initialize visualizer
    visualizer = EmbeddingVisualizer(args.run_id, args.db_path)

    # Load lexicon if needed
    lexicon = None
    if args.lexicon:
        with open(args.lexicon, "r", encoding="utf-8") as f:
            lexicon = json.load(f)

    # Load character frequencies if needed
    char_frequencies = None
    if args.color_by == "frequency":
        print("Loading character frequencies...")
        char_frequencies = load_char_frequencies(args.db_path)

    # t-SNE visualization
    if args.method == "tsne":
        visualizer.plot_tsne(
            output_path=args.output,
            color_by=args.color_by,
            lexicon=lexicon,
            char_frequencies=char_frequencies,
            perplexity=args.perplexity,
            n_iter=args.n_iter,
        )

    # UMAP visualization
    elif args.method == "umap":
        visualizer.plot_umap(
            output_path=args.output,
            color_by=args.color_by,
            lexicon=lexicon,
            char_frequencies=char_frequencies,
            n_neighbors=args.n_neighbors,
            min_dist=args.min_dist,
        )

    # Similarity heatmap
    elif args.heatmap:
        if not args.characters:
            print("Error: --characters required for heatmap")
            sys.exit(1)

        characters = [c.strip() for c in args.characters.split(",")]
        visualizer.plot_similarity_heatmap(characters, args.output)

    # Category distribution
    elif args.categories:
        if not lexicon:
            print("Error: --lexicon required for category visualization")
            sys.exit(1)

        visualizer.plot_category_distribution(lexicon, args.output)

    else:
        print("Error: Specify --method, --heatmap, or --categories")
        sys.exit(1)

    print(f"\nVisualization complete! Open {args.output} in a web browser.")


if __name__ == "__main__":
    main()