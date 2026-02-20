#!/usr/bin/env python3
"""
Analyze semantic network structure.

Usage:
    python scripts/analyze_semantic_network.py \\
        --cooccur-run-id cooccur_001 \\
        --network-run-id network_001 \\
        --db-path data/villages.db

    # With custom thresholds
    python scripts/analyze_semantic_network.py \\
        --cooccur-run-id cooccur_001 \\
        --network-run-id network_001 \\
        --min-pmi 0.5 \\
        --min-cooccurrence 10 \\
        --db-path data/villages.db
"""

import argparse
import json
from pathlib import Path

from src.nlp.semantic_network import SemanticNetwork


def main():
    parser = argparse.ArgumentParser(
        description="Analyze semantic network structure"
    )
    parser.add_argument(
        '--cooccur-run-id',
        required=True,
        help='Co-occurrence analysis run ID'
    )
    parser.add_argument(
        '--network-run-id',
        required=True,
        help='Network analysis run ID'
    )
    parser.add_argument(
        '--db-path',
        default='data/villages.db',
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--min-pmi',
        type=float,
        default=0.0,
        help='Minimum PMI threshold for edges'
    )
    parser.add_argument(
        '--min-cooccurrence',
        type=int,
        default=5,
        help='Minimum co-occurrence count'
    )
    parser.add_argument(
        '--significant-only',
        action='store_true',
        help='Only include statistically significant pairs'
    )
    parser.add_argument(
        '--community-method',
        choices=['louvain', 'label_propagation', 'greedy'],
        default='louvain',
        help='Community detection method'
    )
    parser.add_argument(
        '--output-dir',
        default='results/semantic_network',
        help='Output directory for results'
    )

    args = parser.parse_args()

    # Initialize network analyzer
    print(f"Building semantic network from run_id={args.cooccur_run_id}...")
    analyzer = SemanticNetwork(db_path=args.db_path)

    # Build network
    graph = analyzer.build_network(
        run_id=args.cooccur_run_id,
        min_pmi=args.min_pmi,
        min_cooccurrence=args.min_cooccurrence,
        significant_only=args.significant_only
    )

    print(f"Network built: {graph.number_of_nodes()} nodes, "
          f"{graph.number_of_edges()} edges")

    # Detect communities
    print(f"\nDetecting communities using {args.community_method}...")
    communities = analyzer.detect_communities(method=args.community_method)
    print(f"Found {len(set(communities.values()))} communities")

    # Compute centrality
    print("\nComputing centrality measures...")
    centrality = analyzer.compute_centrality()

    # Get network stats
    print("\nComputing network statistics...")
    stats = analyzer.get_network_stats()

    # Find bridges and articulation points
    print("\nFinding structural features...")
    bridges = analyzer.find_bridges()
    articulation_points = analyzer.find_articulation_points()

    # Save to database
    print(f"\nSaving results to database (run_id={args.network_run_id})...")
    analyzer.save_to_database(args.network_run_id)

    # Create output directory
    output_dir = Path(args.output_dir) / args.network_run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export network to JSON
    print(f"\nExporting network to JSON...")
    analyzer.export_to_json(output_dir / 'network.json')

    # Save community assignments
    with open(output_dir / 'communities.json', 'w', encoding='utf-8') as f:
        json.dump(communities, f, ensure_ascii=False, indent=2)

    # Save centrality measures
    with open(output_dir / 'centrality.json', 'w', encoding='utf-8') as f:
        json.dump(centrality, f, ensure_ascii=False, indent=2)

    # Save bridges and articulation points
    structural_features = {
        'bridges': [list(bridge) for bridge in bridges],
        'articulation_points': list(articulation_points)
    }
    with open(output_dir / 'structural_features.json', 'w', encoding='utf-8') as f:
        json.dump(structural_features, f, ensure_ascii=False, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("SEMANTIC NETWORK ANALYSIS SUMMARY")
    print("="*60)
    print(f"Network Run ID: {args.network_run_id}")
    print(f"Co-occurrence Run ID: {args.cooccur_run_id}")
    print(f"\nNetwork Structure:")
    print(f"  Nodes (categories): {stats['num_nodes']}")
    print(f"  Edges: {stats['num_edges']}")
    print(f"  Density: {stats['density']:.4f}")
    print(f"  Connected: {stats['is_connected']}")
    print(f"  Components: {stats['num_components']}")
    print(f"  Avg clustering: {stats['avg_clustering']:.4f}")

    if stats['diameter']:
        print(f"  Diameter: {stats['diameter']}")
        print(f"  Avg shortest path: {stats['avg_shortest_path']:.4f}")

    print(f"\nCommunity Structure:")
    print(f"  Communities: {stats['num_communities']}")
    print(f"  Modularity: {stats['modularity']:.4f}")

    print(f"\nStructural Features:")
    print(f"  Bridges: {len(bridges)}")
    print(f"  Articulation points: {len(articulation_points)}")

    # Print top central categories
    print(f"\nTop 10 Central Categories (by degree):")
    print("-" * 60)
    sorted_by_degree = sorted(
        centrality.items(),
        key=lambda x: x[1]['degree'],
        reverse=True
    )
    for i, (cat, metrics) in enumerate(sorted_by_degree[:10], 1):
        comm_id = communities.get(cat, -1)
        print(f"  {i:2d}. {cat:15s} | Degree: {metrics['degree']:.4f} | "
              f"Between: {metrics['betweenness']:.4f} | Community: {comm_id}")

    # Print communities
    print(f"\nCommunity Composition:")
    print("-" * 60)
    comm_groups = {}
    for cat, comm_id in communities.items():
        if comm_id not in comm_groups:
            comm_groups[comm_id] = []
        comm_groups[comm_id].append(cat)

    for comm_id in sorted(comm_groups.keys()):
        members = comm_groups[comm_id]
        print(f"  Community {comm_id}: {', '.join(members)}")

    if articulation_points:
        print(f"\nArticulation Points (critical categories):")
        print("-" * 60)
        for cat in sorted(articulation_points):
            print(f"  - {cat}")

    print(f"\nResults saved to: {output_dir}")
    print("="*60)


if __name__ == '__main__':
    main()
