#!/usr/bin/env python3
"""
Lexicon Coverage Analysis

Analyze current lexicon coverage and identify high-value unlabeled characters.

Usage:
    python scripts/analyze_lexicon_coverage.py \\
        --lexicon data/semantic_lexicon_v2_demo.json \\
        --db data/villages.db \\
        --output results/coverage_analysis.json \\
        --top-n 500
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_lexicon(lexicon_path: str) -> Dict[str, List[str]]:
    """Load existing lexicon."""
    with open(lexicon_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["categories"]


def get_lexicon_characters(lexicon: Dict[str, List[str]]) -> Set[str]:
    """Extract all characters from lexicon."""
    chars = set()
    for category_chars in lexicon.values():
        chars.update(category_chars)
    return chars


def is_chinese_char(c: str) -> bool:
    """Check if character is Chinese."""
    return '\u4e00' <= c <= '\u9fff'


def analyze_coverage(
    db_path: str,
    lexicon_chars: Set[str],
    region_level: str = "市级"
) -> Dict:
    """
    Analyze lexicon coverage across the dataset.

    Returns:
        Dict with coverage metrics
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all villages with region info
    cursor.execute(f"""
        SELECT {region_level}, 自然村
        FROM 广东省自然村
        WHERE 自然村 IS NOT NULL AND 自然村 != ''
    """)

    # Global metrics
    total_villages = 0
    total_char_instances = 0
    labeled_char_instances = 0
    villages_fully_labeled = 0
    villages_partially_labeled = 0

    # Regional metrics
    regional_stats = defaultdict(lambda: {
        'total_villages': 0,
        'total_chars': 0,
        'labeled_chars': 0,
        'fully_labeled_villages': 0
    })

    # Character frequency tracking
    all_char_freq = Counter()
    labeled_char_freq = Counter()
    unlabeled_char_freq = Counter()

    for region, village_name in cursor.fetchall():
        total_villages += 1

        # Extract unique Chinese characters
        unique_chars = set(c for c in village_name if is_chinese_char(c))

        if not unique_chars:
            continue

        # Count labeled vs unlabeled
        labeled_chars = unique_chars & lexicon_chars
        unlabeled_chars = unique_chars - lexicon_chars

        # Update global counts
        total_char_instances += len(unique_chars)
        labeled_char_instances += len(labeled_chars)

        # Update character frequencies
        for char in unique_chars:
            all_char_freq[char] += 1
        for char in labeled_chars:
            labeled_char_freq[char] += 1
        for char in unlabeled_chars:
            unlabeled_char_freq[char] += 1

        # Check if fully labeled
        if len(unlabeled_chars) == 0:
            villages_fully_labeled += 1
            regional_stats[region]['fully_labeled_villages'] += 1
        elif len(labeled_chars) > 0:
            villages_partially_labeled += 1

        # Update regional stats
        regional_stats[region]['total_villages'] += 1
        regional_stats[region]['total_chars'] += len(unique_chars)
        regional_stats[region]['labeled_chars'] += len(labeled_chars)

    conn.close()

    # Calculate coverage percentages
    occurrence_coverage = (labeled_char_instances / total_char_instances * 100
                          if total_char_instances > 0 else 0)
    village_full_coverage = (villages_fully_labeled / total_villages * 100
                            if total_villages > 0 else 0)
    village_partial_coverage = (villages_partially_labeled / total_villages * 100
                               if total_villages > 0 else 0)

    # Calculate regional coverage
    for region, stats in regional_stats.items():
        stats['occurrence_coverage'] = (
            stats['labeled_chars'] / stats['total_chars'] * 100
            if stats['total_chars'] > 0 else 0
        )
        stats['village_coverage'] = (
            stats['fully_labeled_villages'] / stats['total_villages'] * 100
            if stats['total_villages'] > 0 else 0
        )

    return {
        'global': {
            'total_villages': total_villages,
            'total_char_instances': total_char_instances,
            'labeled_char_instances': labeled_char_instances,
            'occurrence_coverage_pct': round(occurrence_coverage, 2),
            'villages_fully_labeled': villages_fully_labeled,
            'villages_partially_labeled': villages_partially_labeled,
            'village_full_coverage_pct': round(village_full_coverage, 2),
            'village_partial_coverage_pct': round(village_partial_coverage, 2),
            'unique_chars_total': len(all_char_freq),
            'unique_chars_labeled': len(labeled_char_freq),
            'unique_chars_unlabeled': len(unlabeled_char_freq)
        },
        'regional': dict(regional_stats),
        'character_frequencies': {
            'all': dict(all_char_freq.most_common(100)),
            'labeled': dict(labeled_char_freq.most_common(100)),
            'unlabeled': dict(unlabeled_char_freq.most_common(100))
        }
    }


def calculate_marginal_gains(
    db_path: str,
    lexicon_chars: Set[str],
    unlabeled_chars: List[Tuple[str, int]],
    top_n: int = 500
) -> List[Dict]:
    """
    Calculate marginal coverage gain for each unlabeled character.

    Args:
        db_path: Path to database
        lexicon_chars: Current lexicon characters
        unlabeled_chars: List of (char, frequency) tuples
        top_n: Number of characters to analyze

    Returns:
        List of dicts with character, frequency, and marginal gains
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 自然村 FROM 广东省自然村
        WHERE 自然村 IS NOT NULL AND 自然村 != ''
    """)

    # Track which villages would become fully labeled
    village_unlabeled_counts = []

    for row in cursor.fetchall():
        village_name = row[0]
        unique_chars = set(c for c in village_name if is_chinese_char(c))
        unlabeled = unique_chars - lexicon_chars
        village_unlabeled_counts.append((village_name, len(unlabeled), unlabeled))

    conn.close()

    # Calculate marginal gains
    results = []
    for char, freq in unlabeled_chars[:top_n]:
        # Count how many villages would become fully labeled
        villages_unlocked = 0
        for village_name, unlabeled_count, unlabeled_set in village_unlabeled_counts:
            if unlabeled_count == 1 and char in unlabeled_set:
                villages_unlocked += 1

        # Estimate occurrence coverage gain (simplified)
        occurrence_gain = freq

        results.append({
            'character': char,
            'frequency': freq,
            'villages_unlocked': villages_unlocked,
            'occurrence_gain': occurrence_gain,
            'roi_score': villages_unlocked * 10 + freq  # Weighted score
        })

    # Sort by ROI score
    results.sort(key=lambda x: x['roi_score'], reverse=True)

    return results


def generate_priority_list(
    marginal_gains: List[Dict],
    batch_sizes: List[int] = [50, 100, 150, 300, 500]
) -> Dict:
    """
    Generate priority batches for labeling.

    Args:
        marginal_gains: List of character analysis results
        batch_sizes: Cumulative batch sizes to analyze

    Returns:
        Dict with batch recommendations
    """
    batches = {}

    for size in batch_sizes:
        if size > len(marginal_gains):
            size = len(marginal_gains)

        batch_chars = marginal_gains[:size]
        total_freq = sum(c['frequency'] for c in batch_chars)
        total_villages_unlocked = sum(c['villages_unlocked'] for c in batch_chars)

        batches[f'top_{size}'] = {
            'size': size,
            'characters': [c['character'] for c in batch_chars],
            'total_frequency': total_freq,
            'total_villages_unlocked': total_villages_unlocked,
            'estimated_occurrence_gain_pct': round(total_freq / 285000 * 100, 2),
            'top_10_chars': batch_chars[:10]
        }

    return batches


def main():
    parser = argparse.ArgumentParser(description='Analyze lexicon coverage')
    parser.add_argument('--lexicon', default='data/semantic_lexicon_v2_demo.json',
                       help='Path to lexicon file')
    parser.add_argument('--db', default='data/villages.db',
                       help='Path to database')
    parser.add_argument('--output', default='results/coverage_analysis.json',
                       help='Output file path')
    parser.add_argument('--top-n', type=int, default=500,
                       help='Number of unlabeled characters to analyze')
    parser.add_argument('--region-level', default='市级',
                       choices=['市级', '县区级'],
                       help='Region level for analysis')

    args = parser.parse_args()

    print("=" * 60)
    print("Lexicon Coverage Analysis")
    print("=" * 60)

    # Load lexicon
    print(f"\n[1/5] Loading lexicon from {args.lexicon}...")
    lexicon = load_lexicon(args.lexicon)
    lexicon_chars = get_lexicon_characters(lexicon)
    print(f"  Loaded {len(lexicon_chars)} characters across {len(lexicon)} categories")

    # Analyze coverage
    print(f"\n[2/5] Analyzing coverage...")
    coverage = analyze_coverage(args.db, lexicon_chars, args.region_level)

    print(f"\n  Global Coverage:")
    print(f"    Total villages: {coverage['global']['total_villages']:,}")
    print(f"    Occurrence coverage: {coverage['global']['occurrence_coverage_pct']}%")
    print(f"    Villages fully labeled: {coverage['global']['villages_fully_labeled']:,} "
          f"({coverage['global']['village_full_coverage_pct']}%)")
    print(f"    Villages partially labeled: {coverage['global']['villages_partially_labeled']:,} "
          f"({coverage['global']['village_partial_coverage_pct']}%)")
    print(f"    Unique characters: {coverage['global']['unique_chars_total']:,}")
    print(f"    Labeled: {coverage['global']['unique_chars_labeled']:,}")
    print(f"    Unlabeled: {coverage['global']['unique_chars_unlabeled']:,}")

    # Get unlabeled characters
    print(f"\n[3/5] Identifying top {args.top_n} unlabeled characters...")
    unlabeled_freq = [(char, freq) for char, freq in
                      coverage['character_frequencies']['unlabeled'].items()]
    # Get full list from database
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 自然村 FROM 广东省自然村
        WHERE 自然村 IS NOT NULL AND 自然村 != ''
    """)
    char_freq = Counter()
    for row in cursor.fetchall():
        unique_chars = set(c for c in row[0] if is_chinese_char(c))
        for char in unique_chars:
            if char not in lexicon_chars:
                char_freq[char] += 1
    conn.close()

    unlabeled_list = char_freq.most_common(args.top_n)
    print(f"  Found {len(char_freq)} unlabeled characters")
    print(f"  Top 10: {', '.join([f'{c}({f})' for c, f in unlabeled_list[:10]])}")

    # Calculate marginal gains
    print(f"\n[4/5] Calculating marginal coverage gains...")
    marginal_gains = calculate_marginal_gains(
        args.db, lexicon_chars, unlabeled_list, args.top_n
    )
    print(f"  Analyzed {len(marginal_gains)} characters")
    print(f"  Top 5 by ROI:")
    for i, char_data in enumerate(marginal_gains[:5], 1):
        print(f"    {i}. '{char_data['character']}' - "
              f"freq={char_data['frequency']}, "
              f"unlocks={char_data['villages_unlocked']} villages, "
              f"ROI={char_data['roi_score']}")

    # Generate priority batches
    print(f"\n[5/5] Generating priority batches...")
    priority_batches = generate_priority_list(marginal_gains)

    for batch_name, batch_data in priority_batches.items():
        print(f"\n  {batch_name}:")
        print(f"    Characters: {batch_data['size']}")
        print(f"    Est. occurrence gain: +{batch_data['estimated_occurrence_gain_pct']}%")
        print(f"    Villages unlocked: {batch_data['total_villages_unlocked']:,}")

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = {
        'lexicon_path': args.lexicon,
        'lexicon_size': len(lexicon_chars),
        'analysis_date': '2026-02-18',
        'coverage': coverage,
        'marginal_gains': marginal_gains,
        'priority_batches': priority_batches
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Results saved to {output_path}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
