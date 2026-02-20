"""
Test script for spatial_tendency_integration API endpoints
"""
import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_integration_list():
    """Test GET /api/spatial/integration"""
    response = client.get("/api/spatial/integration")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Records returned: {len(data)}")
        if data:
            print(f"Sample record: {data[0]}")
    else:
        print(f"Error: {response.json()}")
    return response.status_code == 200

def test_integration_by_character():
    """Test GET /api/spatial/integration/by-character/{character}"""
    response = client.get("/api/spatial/integration/by-character/村")
    print(f"\nStatus: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Character: {data.get('character')}")
        print(f"Total clusters: {data.get('total_clusters')}")
        if data.get('clusters'):
            print(f"Sample cluster: {data['clusters'][0]}")
    else:
        print(f"Error: {response.json()}")
    return response.status_code == 200

def test_integration_by_cluster():
    """Test GET /api/spatial/integration/by-cluster/{cluster_id}"""
    response = client.get("/api/spatial/integration/by-cluster/0")
    print(f"\nStatus: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Cluster ID: {data.get('cluster_id')}")
        print(f"Total characters: {data.get('total_characters')}")
        if data.get('characters'):
            print(f"Sample character: {data['characters'][0]}")
    else:
        print(f"Error: {response.json()}")
    return response.status_code == 200

def test_integration_summary():
    """Test GET /api/spatial/integration/summary"""
    response = client.get("/api/spatial/integration/summary")
    print(f"\nStatus: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Run ID: {data.get('run_id')}")
        print(f"Overall stats: {data.get('overall')}")
        print(f"Top characters: {len(data.get('top_characters', []))}")
        print(f"Top clusters: {len(data.get('top_clusters', []))}")
    else:
        print(f"Error: {response.json()}")
    return response.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Spatial-Tendency Integration API Endpoints")
    print("=" * 60)

    tests = [
        ("Integration List", test_integration_list),
        ("Integration by Character", test_integration_by_character),
        ("Integration by Cluster", test_integration_by_cluster),
        ("Integration Summary", test_integration_summary)
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Test: {name}")
        print("=" * 60)
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"Exception: {e}")
            results.append((name, False))

    print(f"\n{'=' * 60}")
    print("Test Results Summary")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{total} tests passed")
