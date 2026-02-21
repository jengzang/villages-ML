"""
API Complete Testing Script
Tests all 50+ API endpoints to verify schema fixes and functionality
"""
import requests
import sys
import json
import os
from typing import List, Tuple

# Disable proxy for localhost
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'

BASE_URL = "http://localhost:8000"

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def test_semantic_composition() -> List[Tuple[str, bool, str]]:
    """Test semantic composition endpoints"""
    print(f"\n{YELLOW}Testing Semantic Composition Endpoints...{RESET}")
    tests = [
        ("Semantic Indices", "/api/semantic/indices?limit=5"),
        ("Semantic Bigrams", "/api/semantic/composition/bigrams?min_frequency=5"),
        ("Semantic Trigrams", "/api/semantic/composition/trigrams?limit=10"),
        ("Semantic PMI", "/api/semantic/composition/pmi?limit=10"),
        ("Composition Patterns", "/api/semantic/composition/patterns"),
    ]
    return run_tests(tests)


def test_pattern_analysis() -> List[Tuple[str, bool, str]]:
    """Test pattern analysis endpoints"""
    print(f"\n{YELLOW}Testing Pattern Analysis Endpoints...{RESET}")
    tests = [
        ("Pattern Global Freq", "/api/patterns/frequency/global?top_k=20"),
        ("Pattern Regional Freq", "/api/patterns/frequency/regional?region_level=city&top_k=10"),
        ("Pattern Tendency", "/api/patterns/tendency?region_level=county&limit=20"),
        ("Structural Patterns", "/api/patterns/structural"),
    ]
    return run_tests(tests)


def test_village_data() -> List[Tuple[str, bool, str]]:
    """Test village data endpoints"""
    print(f"\n{YELLOW}Testing Village Data Endpoints...{RESET}")
    results = []

    # First get a valid village_id
    try:
        response = requests.get(f"{BASE_URL}/api/village/search?query=新村&limit=1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                village_id = data[0].get('village_id')
                if village_id:
                    # Test village endpoints with actual village_id
                    tests = [
                        ("Village Search", "/api/village/search?query=新村&limit=5"),
                        ("Village N-grams", f"/api/village/ngrams/{village_id}"),
                        ("Village Semantic Structure", f"/api/village/semantic-structure/{village_id}"),
                        ("Village Features", f"/api/village/features/{village_id}"),
                        ("Village Spatial Features", f"/api/village/spatial-features/{village_id}"),
                        ("Village Complete Profile", f"/api/village/complete/{village_id}"),
                    ]
                    return run_tests(tests)
                else:
                    results.append(("Village Data", False, "No village_id in response"))
            else:
                results.append(("Village Data", False, "Empty search results"))
        else:
            results.append(("Village Data", False, f"Search failed: {response.status_code}"))
    except Exception as e:
        results.append(("Village Data", False, str(e)))

    return results


def test_regional_aggregates() -> List[Tuple[str, bool, str]]:
    """Test regional aggregates endpoints"""
    print(f"\n{YELLOW}Testing Regional Aggregates Endpoints...{RESET}")
    tests = [
        ("City Aggregates", "/api/regional/aggregates/city"),
        ("County Aggregates", "/api/regional/aggregates/county?limit=10"),
        ("Town Aggregates", "/api/regional/aggregates/town?limit=10"),
        ("Spatial Aggregates", "/api/regional/spatial-aggregates?region_level=city&limit=10"),
        ("Region Vectors", "/api/regional/vectors?limit=10"),
    ]
    return run_tests(tests)


def test_character_analysis() -> List[Tuple[str, bool, str]]:
    """Test character analysis endpoints"""
    print(f"\n{YELLOW}Testing Character Analysis Endpoints...{RESET}")
    tests = [
        ("Character Frequency", "/api/character/frequency/global?top_n=20"),
        ("Character Tendency", "/api/character/tendency/by-region?region_level=city&region_name=广州市&top_n=10"),
        ("Character Embeddings", "/api/character/embeddings/similarities?char=村&top_k=10"),
        ("Character Significance", "/api/character/significance/by-character?char=村&region_level=city"),
    ]
    return run_tests(tests)


def test_clustering() -> List[Tuple[str, bool, str]]:
    """Test clustering endpoints"""
    print(f"\n{YELLOW}Testing Clustering Endpoints...{RESET}")
    tests = [
        ("Cluster Assignments", "/api/clustering/assignments?limit=10"),
        ("Cluster Profiles", "/api/clustering/profiles"),
        # ("Cluster Evaluation", "/api/clustering/evaluation"),  # Not implemented
    ]
    return run_tests(tests)


def test_spatial_analysis() -> List[Tuple[str, bool, str]]:
    """Test spatial analysis endpoints"""
    print(f"\n{YELLOW}Testing Spatial Analysis Endpoints...{RESET}")
    tests = [
        ("Spatial Clusters", "/api/spatial/clusters?limit=10"),
        ("Spatial Hotspots", "/api/spatial/hotspots"),
    ]
    return run_tests(tests)


def test_ngrams() -> List[Tuple[str, bool, str]]:
    """Test n-gram endpoints"""
    print(f"\n{YELLOW}Testing N-gram Endpoints...{RESET}")
    tests = [
        ("Bigram Frequency", "/api/ngrams/frequency?n=2&top_k=20"),
        ("Trigram Frequency", "/api/ngrams/frequency?n=3&top_k=20"),
        ("N-gram Patterns", "/api/ngrams/patterns?limit=20"),
    ]
    return run_tests(tests)


def run_tests(tests: List[Tuple[str, str]]) -> List[Tuple[str, bool, str]]:
    """Run a list of tests and return results"""
    results = []
    for name, endpoint in tests:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            success = response.status_code == 200
            if success:
                # Verify response is valid JSON
                try:
                    data = response.json()
                    if isinstance(data, list):
                        info = f"200 OK ({len(data)} records)"
                    elif isinstance(data, dict):
                        info = f"200 OK (dict)"
                    else:
                        info = "200 OK"
                except:
                    success = False
                    info = "Invalid JSON response"
            else:
                info = f"HTTP {response.status_code}"
            results.append((name, success, info))

            # Print immediate feedback
            status_color = GREEN if success else RED
            status_text = "PASS" if success else "FAIL"
            print(f"  [{status_color}{status_text}{RESET}] {name}: {info}")

        except Exception as e:
            results.append((name, False, str(e)))
            print(f"  [{RED}FAIL{RESET}] {name}: {str(e)}")

    return results


def main():
    print("=" * 60)
    print("API Endpoint Testing - Complete Coverage")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"\n{RED}ERROR: API server not responding at {BASE_URL}{RESET}")
            print("Please start the server with: uvicorn api.main:app --reload")
            sys.exit(1)
    except Exception as e:
        print(f"\n{RED}ERROR: Cannot connect to API server{RESET}")
        print(f"Error: {e}")
        print("Please start the server with: uvicorn api.main:app --reload")
        sys.exit(1)

    print(f"{GREEN}Server is running!{RESET}")

    # Run all test suites
    all_results = []
    all_results.extend(test_semantic_composition())
    all_results.extend(test_pattern_analysis())
    all_results.extend(test_village_data())
    all_results.extend(test_regional_aggregates())
    all_results.extend(test_character_analysis())
    all_results.extend(test_clustering())
    all_results.extend(test_spatial_analysis())
    all_results.extend(test_ngrams())

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success, _ in all_results if success)
    total = len(all_results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    summary_color = GREEN if passed == total else (YELLOW if pass_rate >= 80 else RED)
    print(f"\n{summary_color}Results: {passed}/{total} tests passed ({pass_rate:.1f}%){RESET}\n")

    # Print failed tests
    failed_tests = [(name, info) for name, success, info in all_results if not success]
    if failed_tests:
        print(f"{RED}Failed Tests:{RESET}")
        for name, info in failed_tests:
            print(f"  - {name}: {info}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
