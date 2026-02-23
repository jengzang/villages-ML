"""
Semantic Network Analysis Module

Constructs and analyzes semantic networks from category co-occurrence patterns.
Nodes represent semantic categories, edges represent co-occurrence strength.
"""

import sqlite3
import json
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms import community


class SemanticNetwork:
    """
    Semantic network builder and analyzer.

    Constructs networks where:
    - Nodes: semantic categories
    - Edges: co-occurrence relationships (weighted by PMI)
    - Communities: semantic clusters
    """

    def __init__(self, db_path: str):
        """
        Initialize semantic network analyzer.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.graph = None
        self.communities = None

    def build_network(
        self,
        run_id: str,
        min_pmi: float = 0.0,
        min_cooccurrence: int = 5,
        significant_only: bool = True
    ) -> nx.Graph:
        """
        Build semantic network from co-occurrence data.

        Args:
            run_id: Co-occurrence analysis run ID
            min_pmi: Minimum PMI threshold for edges
            min_cooccurrence: Minimum co-occurrence count
            significant_only: Only include statistically significant pairs

        Returns:
            NetworkX graph with categories as nodes
        """
        conn = sqlite3.connect(self.db_path)

        # Load co-occurrence data
        query = """
        SELECT category1, category2, cooccurrence_count, pmi, is_significant
        FROM semantic_cooccurrence
        WHERE run_id = ?
        """
        df = pd.read_sql_query(query, conn, params=(run_id,))
        conn.close()

        # Filter by criteria
        if significant_only:
            df = df[df['is_significant'] == 1]
        df = df[df['pmi'] >= min_pmi]
        df = df[df['cooccurrence_count'] >= min_cooccurrence]

        # Build graph
        G = nx.Graph()

        # Add edges with weights
        for _, row in df.iterrows():
            cat1, cat2 = row['category1'], row['category2']
            pmi = row['pmi']
            count = row['cooccurrence_count']

            G.add_edge(
                cat1, cat2,
                weight=pmi,
                cooccurrence=count
            )

        self.graph = G
        return G

    def build_network_from_bigrams(
        self,
        min_pmi: float = 0.0,
        min_frequency: int = 100
    ) -> nx.Graph:
        """
        Build semantic network from semantic_bigrams table.

        Args:
            min_pmi: Minimum PMI threshold for edges
            min_frequency: Minimum co-occurrence frequency

        Returns:
            NetworkX graph with categories as nodes
        """
        conn = sqlite3.connect(self.db_path)

        query = """
        SELECT category1, category2, frequency, pmi
        FROM semantic_bigrams
        WHERE pmi >= ? AND frequency >= ?
        """
        df = pd.read_sql_query(query, conn, params=(min_pmi, min_frequency))
        conn.close()

        # Build graph
        G = nx.Graph()
        for _, row in df.iterrows():
            G.add_edge(
                row['category1'], row['category2'],
                weight=row['pmi'],
                frequency=row['frequency']
            )

        self.graph = G
        return G

    def detect_communities(
        self,
        method: str = 'louvain',
        resolution: float = 1.0
    ) -> Dict[str, int]:
        """
        Detect communities in semantic network.

        Args:
            method: Community detection method ('louvain', 'label_propagation', 'greedy')
            resolution: Resolution parameter for modularity (louvain only)

        Returns:
            Dictionary mapping category to community ID
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        if method == 'louvain':
            communities_generator = community.louvain_communities(
                self.graph,
                weight='weight',
                resolution=resolution
            )
        elif method == 'label_propagation':
            communities_generator = community.label_propagation_communities(self.graph)
        elif method == 'greedy':
            communities_generator = community.greedy_modularity_communities(
                self.graph,
                weight='weight'
            )
        else:
            raise ValueError(f"Unknown method: {method}")

        # Convert to dict
        category_to_community = {}
        for comm_id, comm_set in enumerate(communities_generator):
            for category in comm_set:
                category_to_community[category] = comm_id

        self.communities = category_to_community
        return category_to_community

    def compute_centrality(self) -> Dict[str, Dict[str, float]]:
        """
        Compute centrality measures for all nodes.

        Returns:
            Dictionary with centrality metrics for each category
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        centrality_metrics = {}

        # Degree centrality
        degree_cent = nx.degree_centrality(self.graph)

        # Betweenness centrality
        betweenness_cent = nx.betweenness_centrality(
            self.graph,
            weight='weight'
        )

        # Closeness centrality
        if nx.is_connected(self.graph):
            closeness_cent = nx.closeness_centrality(
                self.graph,
                distance='weight'
            )
        else:
            # For disconnected graphs, compute per component
            closeness_cent = {}
            for component in nx.connected_components(self.graph):
                subgraph = self.graph.subgraph(component)
                closeness = nx.closeness_centrality(subgraph, distance='weight')
                closeness_cent.update(closeness)

        # Eigenvector centrality
        try:
            eigenvector_cent = nx.eigenvector_centrality(
                self.graph,
                weight='weight',
                max_iter=1000
            )
        except nx.PowerIterationFailedConvergence:
            eigenvector_cent = {node: 0.0 for node in self.graph.nodes()}

        # PageRank centrality
        pagerank_cent = self.compute_pagerank()

        # Combine all metrics
        for node in self.graph.nodes():
            centrality_metrics[node] = {
                'degree': degree_cent.get(node, 0.0),
                'betweenness': betweenness_cent.get(node, 0.0),
                'closeness': closeness_cent.get(node, 0.0),
                'eigenvector': eigenvector_cent.get(node, 0.0),
                'pagerank': pagerank_cent.get(node, 0.0)
            }

        return centrality_metrics

    def compute_pagerank(self, alpha: float = 0.85) -> Dict[str, float]:
        """
        Compute PageRank centrality.

        Args:
            alpha: Damping parameter (default 0.85)

        Returns:
            Dictionary mapping node to PageRank score
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        return nx.pagerank(
            self.graph,
            alpha=alpha,
            weight='weight'
        )

    def get_network_stats(self) -> Dict:
        """
        Compute network-level statistics.

        Returns:
            Dictionary with network statistics
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        stats = {
            'num_nodes': self.graph.number_of_nodes(),
            'num_edges': self.graph.number_of_edges(),
            'density': nx.density(self.graph),
            'is_connected': nx.is_connected(self.graph),
            'num_components': nx.number_connected_components(self.graph)
        }

        # Average clustering coefficient
        stats['avg_clustering'] = nx.average_clustering(
            self.graph,
            weight='weight'
        )

        # Diameter (only for connected graphs)
        if stats['is_connected']:
            stats['diameter'] = nx.diameter(self.graph)
            stats['avg_shortest_path'] = nx.average_shortest_path_length(
                self.graph,
                weight='weight'
            )
        else:
            stats['diameter'] = None
            stats['avg_shortest_path'] = None

        # Modularity (if communities detected)
        if self.communities:
            # Convert to list of sets
            comm_sets = defaultdict(set)
            for cat, comm_id in self.communities.items():
                comm_sets[comm_id].add(cat)
            comm_list = list(comm_sets.values())

            stats['modularity'] = community.modularity(
                self.graph,
                comm_list,
                weight='weight'
            )
            stats['num_communities'] = len(comm_list)
        else:
            stats['modularity'] = None
            stats['num_communities'] = None

        return stats

    def find_bridges(self) -> List[Tuple[str, str]]:
        """
        Find bridge edges (edges whose removal disconnects the graph).

        Returns:
            List of bridge edges (category pairs)
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        bridges = list(nx.bridges(self.graph))
        return bridges

    def find_articulation_points(self) -> Set[str]:
        """
        Find articulation points (nodes whose removal disconnects the graph).

        Returns:
            Set of articulation point categories
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        return set(nx.articulation_points(self.graph))

    def get_neighbors(
        self,
        category: str,
        top_k: int = 10,
        sort_by: str = 'weight'
    ) -> List[Tuple[str, float]]:
        """
        Get top-K neighbors of a category.

        Args:
            category: Category name
            top_k: Number of neighbors to return
            sort_by: Sort by 'weight' (PMI) or 'cooccurrence'

        Returns:
            List of (neighbor_category, value) tuples
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        if category not in self.graph:
            return []

        neighbors = []
        for neighbor in self.graph.neighbors(category):
            edge_data = self.graph[category][neighbor]
            value = edge_data.get(sort_by, 0.0)
            neighbors.append((neighbor, value))

        # Sort and return top-K
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors[:top_k]

    def export_to_json(self, output_path: str):
        """
        Export network to JSON format for visualization.

        Args:
            output_path: Output JSON file path
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        # Prepare nodes
        nodes = []
        centrality = self.compute_centrality()

        for node in self.graph.nodes():
            node_data = {
                'id': node,
                'label': node,
                'degree': self.graph.degree(node),
                'centrality': centrality.get(node, {})
            }

            if self.communities:
                node_data['community'] = self.communities.get(node)

            nodes.append(node_data)

        # Prepare edges
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                'source': u,
                'target': v,
                'weight': data.get('weight', 0.0),
                'cooccurrence': data.get('cooccurrence', 0)
            })

        # Export
        output_data = {
            'nodes': nodes,
            'edges': edges,
            'stats': self.get_network_stats()
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    def save_to_database(self, run_id: str):
        """
        Save network analysis results to database.

        Args:
            run_id: Network analysis run ID
        """
        if self.graph is None:
            raise ValueError("Must build network first")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables if not exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_network_stats (
            run_id TEXT PRIMARY KEY,
            num_nodes INTEGER,
            num_edges INTEGER,
            density REAL,
            is_connected INTEGER,
            num_components INTEGER,
            avg_clustering REAL,
            diameter INTEGER,
            avg_shortest_path REAL,
            modularity REAL,
            num_communities INTEGER,
            created_at REAL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_network_centrality (
            run_id TEXT NOT NULL,
            category TEXT NOT NULL,
            degree_centrality REAL,
            betweenness_centrality REAL,
            closeness_centrality REAL,
            eigenvector_centrality REAL,
            pagerank REAL,
            community_id INTEGER,
            PRIMARY KEY (run_id, category)
        )
        """)

        # Save network stats
        stats = self.get_network_stats()
        cursor.execute("""
        INSERT OR REPLACE INTO semantic_network_stats
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            stats['num_nodes'],
            stats['num_edges'],
            stats['density'],
            1 if stats['is_connected'] else 0,
            stats['num_components'],
            stats['avg_clustering'],
            stats['diameter'],
            stats['avg_shortest_path'],
            stats['modularity'],
            stats['num_communities'],
            pd.Timestamp.now().timestamp()
        ))

        # Save centrality measures
        centrality = self.compute_centrality()
        for category, metrics in centrality.items():
            community_id = self.communities.get(category) if self.communities else None
            cursor.execute("""
            INSERT OR REPLACE INTO semantic_network_centrality
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                category,
                metrics['degree'],
                metrics['betweenness'],
                metrics['closeness'],
                metrics['eigenvector'],
                metrics['pagerank'],
                community_id
            ))

        conn.commit()
        conn.close()

