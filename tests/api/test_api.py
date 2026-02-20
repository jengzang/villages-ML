#!/usr/bin/env python3
"""
API 测试脚本
API Test Script

测试API的基本功能是否正常
"""
import requests
import sys
import time
import os

# 禁用代理 - 修复 localhost 连接问题
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

# 创建不使用代理的 session
session = requests.Session()
session.trust_env = False
session.proxies = {'http': None, 'https': None}

API_BASE = "http://127.0.0.1:8000"

def test_endpoint(name, url, expected_keys=None):
    """测试单个端点"""
    try:
        print(f"测试: {name}...", end=" ")
        response = session.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # 检查预期的键
            if expected_keys:
                for key in expected_keys:
                    if key not in data:
                        print(f"❌ (缺少键: {key})")
                        return False

            print("✓")

        if response.status_code == 200:
            data = response.json()

            # 检查预期的键
            if expected_keys:
                for key in expected_keys:
                    if key not in data:
                        print(f"❌ (缺少键: {key})")
                        return False

            print("✓")
            return True
        else:
            print(f"❌ (状态码: {response.status_code})")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ (无法连接)")
        return False
    except requests.exceptions.Timeout:
        print("❌ (超时)")
        return False
    except Exception as e:
        print(f"❌ ({e})")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("API 功能测试")
    print("API Functionality Test")
    print("=" * 60)
    print()

    # 检查API是否运行
    print("检查API服务...")
    try:
        response = session.get(f"{API_BASE}/", timeout=5)
        if response.status_code != 200:
            print("❌ API服务未运行")
            print("   请先启动API: uvicorn api.main:app --reload")
            sys.exit(1)
        print("✓ API服务正在运行")
        print()
    except:
        print("❌ 无法连接到API服务")
        print("   请先启动API: uvicorn api.main:app --reload")
        sys.exit(1)

    # 测试各个端点
    tests = [
        ("根端点", f"{API_BASE}/", ["message", "version"]),
        ("健康检查", f"{API_BASE}/health", ["status"]),
        ("表统计", f"{API_BASE}/api/metadata/stats/tables", ["tables"]),
        ("系统概览", f"{API_BASE}/api/metadata/stats/overview", None),
        ("字符频率", f"{API_BASE}/api/character/frequency?limit=10", ["characters"]),
        ("村庄搜索", f"{API_BASE}/api/village/search?query=村&limit=5", ["villages"]),
    ]

    print("测试端点:")
    print("-" * 60)

    passed = 0
    failed = 0

    for name, url, keys in tests:
        if test_endpoint(name, url, keys):
            passed += 1
        else:
            failed += 1
        time.sleep(0.5)  # 避免请求过快

    print("-" * 60)
    print()

    # 总结
    print("=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("✓ 所有测试通过！API运行正常。")
    else:
        print(f"❌ {failed} 个测试失败，请检查API配置。")

    print("=" * 60)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
