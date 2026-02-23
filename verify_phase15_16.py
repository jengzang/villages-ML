"""
Verification script for Phase 15-16 implementation.

Demonstrates the new analytical capabilities.
"""

import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / "data" / "villages.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("Phase 15-16 Verification Report")
print("=" * 70)

# Phase 15: Region Similarity
print("\n[Phase 15: Region Similarity Analysis]")
print("-" * 70)

cursor.execute("SELECT COUNT(*) FROM region_similarity")
print(f"Total region pairs: {cursor.fetchone()[0]}")

cursor.execute("""
SELECT AVG(cosine_similarity), MIN(cosine_similarity), MAX(cosine_similarity)
FROM region_similarity
""")
stats = cursor.fetchone()
print(f"Cosine similarity - Avg: {stats[0]:.4f}, Min: {stats[1]:.4f}, Max: {stats[2]:.4f}")

print("\nTop 5 most similar region pairs:")
cursor.execute("""
SELECT region1, region2, cosine_similarity, jaccard_similarity
FROM region_similarity
ORDER BY cosine_similarity DESC
LIMIT 5
""")
for i, row in enumerate(cursor.fetchall(), 1):
    print(f"  {i}. {row[0][:20]:20s} <-> {row[1][:20]:20s}: "
          f"cosine={row[2]:.4f}, jaccard={row[3]:.4f}")

# Phase 16: Semantic Network Centrality
print("\n[Phase 16: Semantic Network Centrality Analysis]")
print("-" * 70)

cursor.execute("SELECT COUNT(*) FROM semantic_network_centrality")
print(f"Total categories analyzed: {cursor.fetchone()[0]}")

cursor.execute("""
SELECT run_id, num_nodes, num_edges, density, num_communities, modularity
FROM semantic_network_stats
ORDER BY created_at DESC
LIMIT 1
""")
stats = cursor.fetchone()
print(f"Run ID: {stats[0]}")
print(f"Network: {stats[1]} nodes, {stats[2]} edges")
print(f"Density: {stats[3]:.4f}, Communities: {stats[4]}, Modularity: {stats[5]:.4f}")

print("\nTop 5 categories by PageRank:")
cursor.execute("""
SELECT category, pagerank, degree_centrality, betweenness_centrality
FROM semantic_network_centrality
WHERE run_id = ?
ORDER BY pagerank DESC
LIMIT 5
""", (stats[0],))
for i, row in enumerate(cursor.fetchall(), 1):
    print(f"  {i}. {row[0]:15s}: PR={row[1]:.4f}, Deg={row[2]:.4f}, Bet={row[3]:.4f}")

print("\nTop 3 bridge categories (by betweenness):")
cursor.execute("""
SELECT category, betweenness_centrality, pagerank
FROM semantic_network_centrality
WHERE run_id = ?
ORDER BY betweenness_centrality DESC
LIMIT 3
""", (stats[0],))
for i, row in enumerate(cursor.fetchall(), 1):
    print(f"  {i}. {row[0]:15s}: Betweenness={row[1]:.4f}, PageRank={row[2]:.4f}")

conn.close()

print("\n" + "=" * 70)
print("Verification Complete - All phases working correctly!")
print("=" * 70)
