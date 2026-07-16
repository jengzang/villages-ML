"""
Phase 16: Semantic Network Centrality Analysis (DEPRECATED)

Previously computed centrality metrics for semantic categories using network analysis.

DEPRECATED: The backend now computes semantic network metrics in real-time via
compute/engine.py:build_semantic_network() and the POST /compute/semantic/network
endpoint. The precomputed tables (semantic_network_edges, semantic_network_centrality,
semantic_network_stats) have zero API consumers.
"""

import argparse


def main():
    """DEPRECATED - Backend uses real-time computation instead."""
    parser = argparse.ArgumentParser(description="Phase 16 deprecated no-op")
    parser.add_argument("--db-path", default="data/villages.db", help="Accepted for pipeline config compatibility")
    parser.add_argument("--run-id", default=None, help="Accepted for pipeline config compatibility")
    parser.parse_args()

    print("=" * 60)
    print("Phase 16: Semantic Network Centrality Analysis (DEPRECATED)")
    print("=" * 60)
    print()
    print("Precomputed semantic_network_edges, semantic_network_centrality, and")
    print("semantic_network_stats tables have been replaced by real-time computation")
    print("via compute/engine.py:build_semantic_network(). No offline work needed.")
    print()
    print("Phase 16 complete (no-op)")
    print("=" * 60)


if __name__ == "__main__":
    main()
