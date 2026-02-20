"""
API测试脚本
Simple test script to verify API endpoints
"""
import requests
import json
import os

# 禁用代理 - 修复 localhost 连接问题
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

# 创建不使用代理的 session
session = requests.Session()
session.trust_env = False
session.proxies = {'http': None, 'https': None}

BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查"""
    print("Testing health check...")
    response = session.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")


def test_system_overview():
    """测试系统概览"""
    print("Testing system overview...")
    response = session.get(f"{BASE_URL}/api/metadata/stats/overview")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total villages: {data['total_villages']}")
        print(f"Total cities: {data['total_cities']}")
        print(f"Total counties: {data['total_counties']}")
        print(f"Database size: {data['database_size_mb']} MB\n")
    else:
        print(f"Error: {response.text}\n")


def test_character_frequency():
    """测试字符频率"""
    print("Testing character frequency...")
    response = session.get(
        f"{BASE_URL}/api/character/frequency/global",
        params={"top_n": 10}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Top 10 characters:")
        for item in data[:5]:
            print(f"  {item['character']}: {item['frequency']} (rank {item['rank']})")
        print()
    else:
        print(f"Error: {response.text}\n")


def test_village_search():
    """测试村庄搜索"""
    print("Testing village search...")
    response = session.get(
        f"{BASE_URL}/api/village/search",
        params={"query": "村", "limit": 5}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data)} villages:")
        for village in data[:3]:
            print(f"  {village['village_name']} ({village['city']}, {village['county']})")
        print()
    else:
        print(f"Error: {response.text}\n")


def test_semantic_categories():
    """测试语义类别"""
    print("Testing semantic categories...")
    response = session.get(f"{BASE_URL}/api/semantic/category/list")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data)} semantic categories:")
        for cat in data[:5]:
            print(f"  {cat['category']}: {cat['character_count']} characters")
        print()
    else:
        print(f"Error: {response.text}\n")


def test_clustering_metrics():
    """测试聚类指标"""
    print("Testing clustering metrics...")
    response = session.get(
        f"{BASE_URL}/api/clustering/metrics",
        params={"algorithm": "kmeans"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data)} clustering configurations:")
        for metric in data[:3]:
            print(f"  k={metric['k']}: silhouette={metric['silhouette_score']:.3f}")
        print()
    else:
        print(f"Error: {response.text}\n")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("广东省自然村分析系统 API 测试")
    print("=" * 60)
    print()

    try:
        test_health()
        test_system_overview()
        test_character_frequency()
        test_village_search()
        test_semantic_categories()
        test_clustering_metrics()

        print("=" * 60)
        print("所有测试完成！")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到API服务器")
        print("请确保API服务器正在运行: python -m api.main")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
