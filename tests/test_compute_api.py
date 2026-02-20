"""
在线计算API测试脚本
Test script for online computation APIs
"""

import requests
import json
import time
from typing import Dict, Any


BASE_URL = "http://localhost:8000/api"


def test_clustering_run():
    """测试聚类计算"""
    print("\n=== Testing Clustering Run ===")

    params = {
        "algorithm": "kmeans",
        "k": 4,
        "region_level": "county",
        "features": {
            "use_semantic": True,
            "use_morphology": True,
            "use_diversity": True,
            "top_n_suffix2": 100,
            "top_n_suffix3": 100
        },
        "preprocessing": {
            "use_pca": True,
            "pca_n_components": 50,
            "standardize": True
        },
        "random_state": 42
    }

    # 首次请求（无缓存）
    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/clustering/run", json=params)
    first_time = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ First request: {first_time:.2f}s")
        print(f"  - Run ID: {result['run_id']}")
        print(f"  - Regions: {result['n_regions']}")
        print(f"  - Silhouette: {result['metrics']['silhouette_score']:.3f}")
        print(f"  - From cache: {result.get('from_cache', False)}")
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return

    # 第二次请求（有缓存）
    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/clustering/run", json=params)
    cached_time = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Cached request: {cached_time:.2f}s")
        print(f"  - From cache: {result.get('from_cache', False)}")
        print(f"  - Speedup: {first_time/cached_time:.1f}x")
    else:
        print(f"✗ Cached request failed: {response.status_code}")


def test_clustering_scan():
    """测试聚类参数扫描"""
    print("\n=== Testing Clustering Scan ===")

    params = {
        "algorithm": "kmeans",
        "k_range": [3, 4, 5, 6],
        "region_level": "county",
        "features": {
            "use_semantic": True,
            "use_morphology": True,
            "use_diversity": True
        },
        "metric": "silhouette_score"
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/clustering/scan", json=params)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Scan completed: {elapsed:.2f}s")
        print(f"  - Scan ID: {result['scan_id']}")
        print(f"  - Best k: {result['best_k']}")
        print(f"  - Best score: {result['best_score']:.3f}")
        print(f"  - Total time: {result['total_time_ms']}ms")
        print(f"  - Results:")
        for r in result['results']:
            print(f"    k={r['k']}: {r['silhouette_score']:.3f} ({r['execution_time_ms']}ms)")
    else:
        print(f"✗ Scan failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_semantic_cooccurrence():
    """测试语义共现分析"""
    print("\n=== Testing Semantic Cooccurrence ===")

    params = {
        "region_level": "county",
        "region_name": "天河区",
        "min_support": 10,
        "min_cooccurrence": 5,
        "alpha": 0.05
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/semantic/cooccurrence", json=params)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Analysis completed: {elapsed:.2f}s")
        print(f"  - Analysis ID: {result['analysis_id']}")
        print(f"  - Region: {result['region_name']}")
        print(f"  - Execution time: {result['execution_time_ms']}ms")
        print(f"  - Cooccurrence pairs: {len(result['cooccurrence_matrix'])}")
        print(f"  - Significant pairs: {len(result['significant_pairs'])}")
    else:
        print(f"✗ Analysis failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_semantic_network():
    """测试语义网络构建"""
    print("\n=== Testing Semantic Network ===")

    params = {
        "region_level": "county",
        "region_name": "all",
        "min_edge_weight": 0.5,
        "centrality_metrics": ["degree", "betweenness"]
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/semantic/network", json=params)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Network built: {elapsed:.2f}s")
        print(f"  - Network ID: {result['network_id']}")
        print(f"  - Nodes: {result['node_count']}")
        print(f"  - Edges: {result['edge_count']}")
        print(f"  - Communities: {len(result['communities'])}")
        print(f"  - Execution time: {result['execution_time_ms']}ms")
    else:
        print(f"✗ Network building failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_feature_extraction():
    """测试特征提取"""
    print("\n=== Testing Feature Extraction ===")

    params = {
        "villages": [
            {"name": "某某村", "city": "广州市", "county": "天河区"},
            {"name": "另一村", "city": "广州市", "county": "越秀区"}
        ],
        "features": {
            "semantic_tags": True,
            "morphology": True
        }
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/features/extract", json=params)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Extraction completed: {elapsed:.2f}s")
        print(f"  - Extraction ID: {result['extraction_id']}")
        print(f"  - Village count: {result['village_count']}")
        print(f"  - Execution time: {result['execution_time_ms']}ms")
    else:
        print(f"✗ Extraction failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_feature_aggregation():
    """测试特征聚合"""
    print("\n=== Testing Feature Aggregation ===")

    params = {
        "region_level": "county",
        "region_names": ["天河区", "越秀区"],
        "features": {
            "semantic_distribution": True,
            "morphology_freq": True,
            "cluster_distribution": True
        },
        "top_n": 10
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/features/aggregate", json=params)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Aggregation completed: {elapsed:.2f}s")
        print(f"  - Aggregation ID: {result['aggregation_id']}")
        print(f"  - Region count: {result['region_count']}")
        print(f"  - Execution time: {result['execution_time_ms']}ms")
    else:
        print(f"✗ Aggregation failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_subset_clustering():
    """测试子集聚类"""
    print("\n=== Testing Subset Clustering ===")

    params = {
        "filter": {
            "cities": ["广州市"],
            "sample_size": 1000
        },
        "clustering": {
            "algorithm": "kmeans",
            "k": 5,
            "features": ["semantic"]
        }
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/subset/cluster", json=params)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Clustering completed: {elapsed:.2f}s")
        print(f"  - Subset ID: {result['subset_id']}")
        print(f"  - Matched villages: {result['matched_villages']}")
        print(f"  - Sampled villages: {result['sampled_villages']}")
        print(f"  - Clusters: {len(result['clusters'])}")
        print(f"  - Execution time: {result['execution_time_ms']}ms")
    else:
        print(f"✗ Clustering failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_subset_comparison():
    """测试子集对比"""
    print("\n=== Testing Subset Comparison ===")

    params = {
        "group_a": {
            "filter": {"cities": ["广州市"]},
            "label": "广州"
        },
        "group_b": {
            "filter": {"cities": ["深圳市"]},
            "label": "深圳"
        },
        "analysis": {
            "semantic_distribution": True,
            "morphology_patterns": True,
            "statistical_test": "chi_square"
        }
    }

    start = time.time()
    response = requests.post(f"{BASE_URL}/compute/subset/compare", json=params)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Comparison completed: {elapsed:.2f}s")
        print(f"  - Comparison ID: {result['comparison_id']}")
        print(f"  - Group A size: {result['group_a_size']}")
        print(f"  - Group B size: {result['group_b_size']}")
        print(f"  - Semantic comparisons: {len(result['semantic_comparison'])}")
        print(f"  - Significant differences: {len(result['significant_differences'])}")
        print(f"  - Execution time: {result['execution_time_ms']}ms")
    else:
        print(f"✗ Comparison failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_cache_stats():
    """测试缓存统计"""
    print("\n=== Testing Cache Stats ===")

    response = requests.get(f"{BASE_URL}/compute/clustering/cache-stats")

    if response.status_code == 200:
        stats = response.json()
        print(f"✓ Cache stats retrieved:")
        print(f"  - Cache size: {stats['cache_size']}/{stats['max_size']}")
        print(f"  - Hit count: {stats['hit_count']}")
        print(f"  - Miss count: {stats['miss_count']}")
        print(f"  - Hit rate: {stats['hit_rate']:.1%}")
        print(f"  - TTL: {stats['ttl_seconds']}s")
    else:
        print(f"✗ Stats retrieval failed: {response.status_code}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("在线计算API测试")
    print("=" * 60)

    try:
        test_clustering_run()
        test_clustering_scan()
        test_semantic_cooccurrence()
        test_semantic_network()
        test_feature_extraction()
        test_feature_aggregation()
        test_subset_clustering()
        test_subset_comparison()
        test_cache_stats()

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到API服务器")
        print("  请确保服务器正在运行: uvicorn api.main:app --reload")
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")


if __name__ == "__main__":
    run_all_tests()
