#!/usr/bin/env python
"""
API 测试脚本 - 测试 API 是否正常运行
"""

import requests
import json

# 禁用代理
import os
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("=" * 50)
    print("API 测试")
    print("=" * 50)
    print()

    # 测试 1: 健康检查
    print("1. 测试健康检查端点...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        print("   ✓ 健康检查通过")
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    print()

    # 测试 2: 根端点
    print("2. 测试根端点...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"   状态码: {response.status_code}")
        data = response.json()
        print(f"   API 版本: {data.get('version')}")
        print("   ✓ 根端点通过")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

    print()

    # 测试 3: Run_ID 管理端点
    print("3. 测试 Run_ID 管理端点...")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/run-ids/active", timeout=5)
        print(f"   状态码: {response.status_code}")
        data = response.json()
        print(f"   活跃 run_id 数量: {data.get('count', 0)}")
        print("   ✓ Run_ID 管理端点通过")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

    print()

    # 测试 4: 空间热点端点
    print("4. 测试空间热点端点...")
    try:
        response = requests.get(f"{BASE_URL}/api/spatial/hotspots", timeout=5)
        print(f"   状态码: {response.status_code}")
        data = response.json()
        if isinstance(data, list):
            print(f"   热点数量: {len(data)}")
            if len(data) > 0:
                print(f"   第一个热点: {data[0]}")
        print("   ✓ 空间热点端点通过")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

    print()
    print("=" * 50)
    print("测试完成！")
    print("=" * 50)
    print()
    print("你现在可以:")
    print("1. 在浏览器中打开: http://127.0.0.1:8000/docs")
    print("2. 使用 curl 命令查询")
    print("3. 使用 Python requests 库")
    print()

    return True

if __name__ == "__main__":
    test_api()
