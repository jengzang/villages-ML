#!/usr/bin/env python3
"""
Test semantic co-occurrence and network analysis.

Usage:
    python scripts/test_semantic_analysis.py
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import numpy as np

from src.nlp.semantic_cooccurrence import SemanticCooccurrence
from src.nlp.semantic_network import SemanticNetwork


def test_cooccurrence_analysis():
    """Test semantic co-occurrence analysis."""
    print("\n" + "="*60)
    print("TEST: Semantic Co-occurrence Analysis")
    print("="*60)

    # Create test data
    test_villages = pd.DataFrame({
        '自然村': [
            '东山村', '西山村', '南山村', '北山村',  # Direction + Mountain
            '东河村', '西河村', '南河村', '北河村',  # Direction + Water
            '大田村', '小田村', '新田村', '老田村',  # Size/Age + Agriculture
            '石桥村', '木桥村', '铁桥村',           # Material + Structure
            '上村', '下村', '中村'                  # Position
        ]
    })

    # Create test lexicon
    test_lexicon = {
        '方位': ['东', '西', '南', '北', '上', '下', '中'],
        '地形': ['山', '河', '桥'],
        '农业': ['田'],
        '材料': ['石', '木', '铁'],
        '规模': ['大', '小'],
        '时间': ['新', '老']
    }

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize analyzer
        analyzer = SemanticCooccurrence(
            db_path=db_path,
            lexicon=test_lexicon
        )

        # Analyze co-occurrence
        print("\n[TEST] Analyzing co-occurrence...")
        cooccur_matrix = analyzer.analyze_villages(
            test_villages,
            village_col='自然村'
        )

        assert cooccur_matrix.shape[0] > 0, "Co-occurrence matrix is empty"
        print(f"[PASS] Co-occurrence matrix: {cooccur_matrix.shape}")

        # Compute PMI
        print("\n[TEST] Computing PMI...")
        pmi_df = analyzer.compute_pmi()
        assert len(pmi_df) > 0, "PMI dataframe is empty"
        print(f"[PASS] PMI computed for {len(pmi_df)} pairs")

        # Find significant pairs
        print("\n[TEST] Finding significant pairs...")
        significant_pairs = analyzer.find_significant_pairs(min_cooccurrence=2)
        print(f"[PASS] Found {len(significant_pairs)} significant pairs")

        # Save to database
        print("\n[TEST] Saving to database...")
        analyzer.save_to_database('test_run_001')

        # Verify database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM semantic_cooccurrence WHERE run_id='test_run_001'"
        )
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0, "No records saved to database"
        print(f"[PASS] Saved {count} records to database")

        # Extract composition rules
        print("\n[TEST] Extracting composition rules...")
        rules = analyzer.extract_composition_rules(top_k=5)
        assert len(rules) > 0, "No composition rules found"
        print(f"[PASS] Found {len(rules)} composition rules")
        print(f"  Top rule: {' + '.join(rules[0]['categories'])} (count={rules[0]['count']})")

        # Compute entropy
        print("\n[TEST] Computing category entropy...")
        entropy_df = analyzer.compute_category_entropy()
        assert len(entropy_df) > 0, "Entropy dataframe is empty"
        print(f"[PASS] Computed entropy for {len(entropy_df)} categories")

        print("\n[PASS] All co-occurrence tests passed!")
        return db_path

    except Exception as e:
        print(f"\n[FAIL] Co-occurrence test failed: {e}")
        Path(db_path).unlink(missing_ok=True)
        raise


def test_network_analysis(db_path: str):
    """Test semantic network analysis."""
    print("\n" + "="*60)
    print("TEST: Semantic Network Analysis")
    print("="*60)

    try:
        # Initialize network analyzer
        analyzer = SemanticNetwork(db_path=db_path)

        # Build network
        print("\n[TEST] Building network...")
        graph = analyzer.build_network(
            run_id='test_run_001',
            min_pmi=0.0,
            min_cooccurrence=2,
            significant_only=False
        )

        assert graph.number_of_nodes() > 0, "Network has no nodes"
        assert graph.number_of_edges() > 0, "Network has no edges"
        print(f"[PASS] Network built: {graph.number_of_nodes()} nodes, "
              f"{graph.number_of_edges()} edges")

        # Detect communities
        print("\n[TEST] Detecting communities...")
        communities = analyzer.detect_communities(method='louvain')
        assert len(communities) > 0, "No communities detected"
        num_communities = len(set(communities.values()))
        print(f"[PASS] Found {num_communities} communities")

        # Compute centrality
        print("\n[TEST] Computing centrality...")
        centrality = analyzer.compute_centrality()
        assert len(centrality) > 0, "No centrality measures computed"
        print(f"[PASS] Computed centrality for {len(centrality)} nodes")

        # Get network stats
        print("\n[TEST] Computing network statistics...")
        stats = analyzer.get_network_stats()
        assert stats['num_nodes'] > 0, "Invalid network stats"
        print(f"[PASS] Network stats computed")
        print(f"  Density: {stats['density']:.4f}")
        print(f"  Avg clustering: {stats['avg_clustering']:.4f}")
        print(f"  Modularity: {stats['modularity']:.4f}")

        # Find bridges
        print("\n[TEST] Finding bridges...")
        bridges = analyzer.find_bridges()
        print(f"[PASS] Found {len(bridges)} bridge edges")

        # Find articulation points
        print("\n[TEST] Finding articulation points...")
        articulation_points = analyzer.find_articulation_points()
        print(f"[PASS] Found {len(articulation_points)} articulation points")

        # Get neighbors
        print("\n[TEST] Getting neighbors...")
        if graph.number_of_nodes() > 0:
            first_node = list(graph.nodes())[0]
            neighbors = analyzer.get_neighbors(first_node, top_k=5)
            print(f"[PASS] Found {len(neighbors)} neighbors for '{first_node}'")

        # Save to database
        print("\n[TEST] Saving network to database...")
        analyzer.save_to_database('test_network_001')

        # Verify database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM semantic_network_centrality WHERE run_id='test_network_001'"
        )
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0, "No network records saved to database"
        print(f"[PASS] Saved {count} centrality records to database")

        # Export to JSON
        print("\n[TEST] Exporting to JSON...")
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / 'network.json'
            analyzer.export_to_json(str(json_path))
            assert json_path.exists(), "JSON export failed"

            # Verify JSON structure
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert 'nodes' in data, "JSON missing nodes"
            assert 'edges' in data, "JSON missing edges"
            assert 'stats' in data, "JSON missing stats"
            print(f"[PASS] JSON export successful")

        print("\n[PASS] All network tests passed!")

    except Exception as e:
        print(f"\n[FAIL] Network test failed: {e}")
        raise


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SEMANTIC ANALYSIS TEST SUITE")
    print("="*60)

    db_path = None
    try:
        # Test co-occurrence analysis
        db_path = test_cooccurrence_analysis()

        # Test network analysis
        test_network_analysis(db_path)

        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)

    except Exception as e:
        print("\n" + "="*60)
        print("TESTS FAILED!")
        print("="*60)
        print(f"Error: {e}")
        return 1

    finally:
        # Cleanup
        if db_path:
            Path(db_path).unlink(missing_ok=True)

    return 0


if __name__ == '__main__':
    exit(main())
