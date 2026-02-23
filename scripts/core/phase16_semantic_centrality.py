"""
Phase 16: Semantic Network Centrality Analysis

Computes centrality metrics for semantic categories using network analysis.

Output:
- semantic_network_centrality table with 5 centrality metrics
- semantic_network_stats table with network statistics
"""

import sqlite3
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.nlp.semantic_network import SemanticNetwork


def create_indexes(conn: sqlite3.Connection):
    """Create indexes for centrality tables."""
    cursor = conn.cursor()

    # Check if indexes already exist
    cursor.execute("""
    SELECT name FROM sqlite_master
    WHERE type='index' AND name='idx_semantic_centrality_degree'
    """)
    if cursor.fetchone():
        print("  Indexes already exist, skipping creation")
        return

    # Create indexes
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_semantic_centrality_degree
    ON semantic_network_centrality(degree_centrality DESC)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_semantic_centrality_pagerank
    ON semantic_network_centrality(pagerank DESC)
    """)

    conn.commit()
    print("  Created indexes on centrality table")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Phase 16: Semantic Network Centrality Analysis")
    print("=" * 60)

    db_path = project_root / "data" / "villages.db"
    run_id = f"phase16_{int(time.time())}"

    # Step 1: Initialize network analyzer
    print("\n[Step 1] Initializing semantic network analyzer...")
    network = SemanticNetwork(str(db_path))

    # Step 2: Build network from bigrams
    print("\n[Step 2] Building network from semantic_bigrams...")
    graph = network.build_network_from_bigrams(
        min_pmi=0.0,
        min_frequency=100
    )
    print(f"  Nodes: {graph.number_of_nodes()}")
    print(f"  Edges: {graph.number_of_edges()}")

    # Step 3: Compute centrality metrics
    print("\n[Step 3] Computing centrality metrics...")
    centrality = network.compute_centrality()
    print(f"  Computed 5 centrality metrics for {len(centrality)} categories")

    # Step 4: Detect communities
    print("\n[Step 4] Detecting communities...")
    communities = network.detect_communities(method='louvain')
    print(f"  Detected {len(set(communities.values()))} communities")

    # Step 5: Get network statistics
    print("\n[Step 5] Computing network statistics...")
    stats = network.get_network_stats()
    print(f"  Density: {stats['density']:.4f}")
    print(f"  Average clustering: {stats['avg_clustering']:.4f}")
    print(f"  Connected: {stats['is_connected']}")

    # Step 6: Save to database
    print("\n[Step 6] Saving to database...")
    network.save_to_database(run_id)
    print(f"  Saved with run_id: {run_id}")

    # Step 7: Create indexes
    print("\n[Step 7] Creating indexes...")
    conn = sqlite3.connect(db_path)
    create_indexes(conn)

    # Step 8: Generate summary
    print("\n[Step 8] Summary Statistics")
    print("=" * 60)

    cursor = conn.cursor()

    # Network stats
    cursor.execute("""
    SELECT num_nodes, num_edges, density, avg_clustering,
           num_components, num_communities, modularity
    FROM semantic_network_stats
    WHERE run_id = ?
    """, (run_id,))
    stats_row = cursor.fetchone()

    print(f"Network Statistics:")
    print(f"  Nodes: {stats_row[0]}")
    print(f"  Edges: {stats_row[1]}")
    print(f"  Density: {stats_row[2]:.4f}")
    print(f"  Avg Clustering: {stats_row[3]:.4f}")
    print(f"  Components: {stats_row[4]}")
    print(f"  Communities: {stats_row[5]}")
    print(f"  Modularity: {stats_row[6]:.4f}")

    # Top categories by PageRank
    print(f"\n[Top Categories by PageRank]")
    cursor.execute("""
    SELECT category, pagerank, degree_centrality, betweenness_centrality
    FROM semantic_network_centrality
    WHERE run_id = ?
    ORDER BY pagerank DESC
    """, (run_id,))
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {row[0]}: PR={row[1]:.4f}, Deg={row[2]:.4f}, Bet={row[3]:.4f}")

    # Top categories by Betweenness (bridge categories)
    print(f"\n[Top Bridge Categories (Betweenness)]")
    cursor.execute("""
    SELECT category, betweenness_centrality, pagerank, degree_centrality
    FROM semantic_network_centrality
    WHERE run_id = ?
    ORDER BY betweenness_centrality DESC
    LIMIT 5
    """, (run_id,))
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {row[0]}: Bet={row[1]:.4f}, PR={row[2]:.4f}, Deg={row[3]:.4f}")

    # Community distribution
    print(f"\n[Community Distribution]")
    cursor.execute("""
    SELECT community_id, COUNT(*) as size,
           GROUP_CONCAT(category, ', ') as members
    FROM semantic_network_centrality
    WHERE run_id = ?
    GROUP BY community_id
    ORDER BY size DESC
    """, (run_id,))
    for row in cursor.fetchall():
        print(f"  Community {row[0]}: {row[1]} members - {row[2]}")

    conn.close()

    print("\n" + "=" * 60)
    print("Phase 16 Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

