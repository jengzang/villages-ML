#!/usr/bin/env python3
"""
Analyze semantic co-occurrence patterns in village names.

Usage:
    python scripts/analyze_semantic_cooccurrence.py \\
        --run-id cooccur_001 \\
        --lexicon data/semantic_lexicon_v1.json \\
        --db-path data/villages.db

    # With regional analysis
    python scripts/analyze_semantic_cooccurrence.py \\
        --run-id cooccur_regional_001 \\
        --lexicon data/semantic_lexicon_v1.json \\
        --region-level 市级 \\
        --db-path data/villages.db
"""

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.nlp.semantic_cooccurrence import SemanticCooccurrence


def main():
    parser = argparse.ArgumentParser(
        description="Analyze semantic co-occurrence patterns"
    )
    parser.add_argument(
        '--run-id',
        required=True,
        help='Analysis run ID'
    )
    parser.add_argument(
        '--lexicon',
        required=True,
        help='Path to semantic lexicon JSON'
    )
    parser.add_argument(
        '--db-path',
        default='data/villages.db',
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--region-level',
        choices=['市级', '县区级', '乡镇'],
        help='Regional level for analysis (optional)'
    )
    parser.add_argument(
        '--output-dir',
        default='results/semantic_cooccurrence',
        help='Output directory for results'
    )
    parser.add_argument(
        '--min-cooccurrence',
        type=int,
        default=5,
        help='Minimum co-occurrence count for significance test'
    )

    args = parser.parse_args()

    # Load lexicon
    print(f"Loading lexicon from {args.lexicon}...")
    with open(args.lexicon, 'r', encoding='utf-8') as f:
        lexicon = json.load(f)

    # Load villages
    print(f"Loading villages from {args.db_path}...")
    conn = sqlite3.connect(args.db_path)
    query = "SELECT * FROM 广东省自然村"
    villages_df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"Loaded {len(villages_df)} villages")

    # Initialize analyzer
    analyzer = SemanticCooccurrence(
        db_path=args.db_path,
        lexicon=lexicon
    )

    # Analyze co-occurrence
    print(f"\nAnalyzing co-occurrence patterns...")
    cooccur_matrix = analyzer.analyze_villages(
        villages_df,
        village_col='自然村'
    )

    print(f"Co-occurrence matrix shape: {cooccur_matrix.shape}")
    print(f"Total co-occurrences: {cooccur_matrix.sum().sum()}")

    # Compute PMI
    print("\nComputing PMI...")
    pmi_df = analyzer.compute_pmi()
    print(f"PMI computed for {len(pmi_df)} category pairs")

    # Find significant pairs
    print("\nFinding statistically significant pairs...")
    significant_pairs = analyzer.find_significant_pairs(
        min_cooccurrence=args.min_cooccurrence
    )
    print(f"Found {len(significant_pairs)} significant pairs")

    # Save to database
    print(f"\nSaving results to database (run_id={args.run_id})...")
    analyzer.save_to_database(args.run_id)

    # Extract composition rules
    print("\nExtracting composition rules...")
    rules = analyzer.extract_composition_rules(top_k=20)

    # Compute category entropy
    print("\nComputing category entropy...")
    entropy_df = analyzer.compute_category_entropy()

    # Create output directory
    output_dir = Path(args.output_dir) / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save results
    print(f"\nSaving results to {output_dir}...")

    # Save co-occurrence matrix
    cooccur_matrix.to_csv(
        output_dir / 'cooccurrence_matrix.csv',
        encoding='utf-8'
    )

    # Save PMI matrix
    pmi_df.to_csv(
        output_dir / 'pmi_matrix.csv',
        encoding='utf-8'
    )

    # Save significant pairs
    significant_pairs.to_csv(
        output_dir / 'significant_pairs.csv',
        index=False,
        encoding='utf-8'
    )

    # Save composition rules
    with open(output_dir / 'composition_rules.json', 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

    # Save entropy
    entropy_df.to_csv(
        output_dir / 'category_entropy.csv',
        index=False,
        encoding='utf-8'
    )

    # Print summary
    print("\n" + "="*60)
    print("SEMANTIC CO-OCCURRENCE ANALYSIS SUMMARY")
    print("="*60)
    print(f"Run ID: {args.run_id}")
    print(f"Villages analyzed: {len(villages_df)}")
    print(f"Categories: {len(cooccur_matrix)}")
    print(f"Total co-occurrences: {int(cooccur_matrix.sum().sum())}")
    print(f"Significant pairs: {len(significant_pairs)}")
    print(f"\nTop 10 co-occurring pairs (by PMI):")
    print("-" * 60)

    top_pairs = significant_pairs.nlargest(10, 'pmi')
    for _, row in top_pairs.iterrows():
        print(f"  {row['category1']:15s} + {row['category2']:15s} | "
              f"PMI: {row['pmi']:6.3f} | Count: {int(row['cooccurrence_count']):5d}")

    print(f"\nTop 5 composition rules:")
    print("-" * 60)
    for i, rule in enumerate(rules[:5], 1):
        cats = ' + '.join(rule['categories'])
        print(f"  {i}. {cats:40s} | Count: {rule['count']:5d} | "
              f"Freq: {rule['frequency']:.4f}")

    print(f"\nCategory entropy (top 5 most diverse):")
    print("-" * 60)
    top_entropy = entropy_df.nlargest(5, 'entropy')
    for _, row in top_entropy.iterrows():
        print(f"  {row['category']:15s} | Entropy: {row['entropy']:.3f} | "
              f"Unique pairs: {int(row['unique_cooccurrences'])}")

    print(f"\nResults saved to: {output_dir}")
    print("="*60)


if __name__ == '__main__':
    main()
