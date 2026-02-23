"""
Test Phase 15-16 API Endpoints

Quick test script to verify the new endpoints work correctly.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"


def test_region_similarity():
    """Test region similarity endpoints."""
    print("=" * 60)
    print("Testing Phase 15: Region Similarity Endpoints")
    print("=" * 60)

    # Test 1: List regions
    print("\n[Test 1] GET /regions/list")
    response = requests.get(f"{BASE_URL}/regions/list?region_level=county")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Total regions: {data['count']}")
        print(f"  Sample regions: {data['regions'][:3]}")
    else:
        print(f"  Status: FAILED ({response.status_code})")

    # Test 2: Search similar regions
    print("\n[Test 2] GET /regions/similarity/search")
    response = requests.get(
        f"{BASE_URL}/regions/similarity/search",
        params={"region": "广州市", "top_k": 5, "metric": "cosine"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Target: {data['target_region']}")
        print(f"  Similar regions: {len(data['similar_regions'])}")
        for i, region in enumerate(data['similar_regions'][:3], 1):
            print(f"    {i}. {region['region']}: {region['similarity']}")
    else:
        print(f"  Status: FAILED ({response.status_code})")

    # Test 3: Get pair similarity
    print("\n[Test 3] GET /regions/similarity/pair")
    response = requests.get(
        f"{BASE_URL}/regions/similarity/pair",
        params={"region1": "广州市", "region2": "深圳市"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Cosine: {data['cosine_similarity']}")
        print(f"  Jaccard: {data['jaccard_similarity']}")
        print(f"  Common chars: {data['common_chars'][:5]}")
    else:
        print(f"  Status: FAILED ({response.status_code})")

    # Test 4: Get similarity matrix
    print("\n[Test 4] GET /regions/similarity/matrix")
    response = requests.get(
        f"{BASE_URL}/regions/similarity/matrix",
        params={"regions": "广州市,深圳市,佛山市", "metric": "cosine"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Regions: {data['regions']}")
        print(f"  Matrix shape: {len(data['matrix'])}x{len(data['matrix'][0])}")
    else:
        print(f"  Status: FAILED ({response.status_code})")


def test_semantic_centrality():
    """Test semantic centrality endpoints."""
    print("\n" + "=" * 60)
    print("Testing Phase 16: Semantic Centrality Endpoints")
    print("=" * 60)

    # Test 1: Get centrality ranking
    print("\n[Test 1] GET /semantic/centrality/ranking")
    response = requests.get(
        f"{BASE_URL}/semantic/centrality/ranking",
        params={"metric": "pagerank", "top_k": 5}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Metric: {data['metric']}")
        print(f"  Top categories:")
        for i, cat in enumerate(data['categories'], 1):
            print(f"    {i}. {cat['category']}: {cat['pagerank']}")
    else:
        print(f"  Status: FAILED ({response.status_code})")

    # Test 2: Get category centrality
    print("\n[Test 2] GET /semantic/centrality/category")
    response = requests.get(
        f"{BASE_URL}/semantic/centrality/category",
        params={"category": "settlement"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Category: {data['category']}")
        print(f"  PageRank: {data['pagerank']}")
        print(f"  Degree: {data['degree_centrality']}")
        print(f"  Betweenness: {data['betweenness_centrality']}")
    else:
        print(f"  Status: FAILED ({response.status_code})")

    # Test 3: Compare centrality
    print("\n[Test 3] GET /semantic/centrality/compare")
    response = requests.get(f"{BASE_URL}/semantic/centrality/compare")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Total categories: {data['count']}")
        print(f"  Sample: {data['categories'][0]['category']}")
    else:
        print(f"  Status: FAILED ({response.status_code})")

    # Test 4: Get network stats
    print("\n[Test 4] GET /semantic/network/stats")
    response = requests.get(f"{BASE_URL}/semantic/network/stats")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Nodes: {data['num_nodes']}")
        print(f"  Edges: {data['num_edges']}")
        print(f"  Density: {data['density']}")
        print(f"  Communities: {data['num_communities']}")
    else:
        print(f"  Status: FAILED ({response.status_code})")

    # Test 5: Get communities
    print("\n[Test 5] GET /semantic/communities")
    response = requests.get(f"{BASE_URL}/semantic/communities")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Total communities: {data['count']}")
        for comm in data['communities']:
            print(f"    Community {comm['community_id']}: {comm['size']} members - {comm['members']}")
    else:
        print(f"  Status: FAILED ({response.status_code})")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 15-16 API Endpoint Tests")
    print("=" * 60)
    print("\nMake sure the API server is running:")
    print("  bash start_api.sh")
    print("\nPress Enter to start tests...")
    input()

    try:
        test_region_similarity()
        test_semantic_centrality()

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Cannot connect to API server.")
        print("Please start the API server first: bash start_api.sh")
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
