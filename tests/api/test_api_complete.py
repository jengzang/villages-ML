"""
完整API测试脚本
Comprehensive API test script
"""
import requests
import os
import json

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'

# 创建session并禁用代理
session = requests.Session()
session.trust_env = False
session.proxies = {'http': None, 'https': None}

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, url, params=None):
    """测试单个端点"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    if params:
        print(f"参数: {params}")
    print('-'*60)

    try:
        response = session.get(url, params=params, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功")
            print(f"返回数据类型: {type(data)}")
            if isinstance(data, list):
                print(f"返回记录数: {len(data)}")
                if len(data) > 0:
                    print(f"第一条记录: {json.dumps(data[0], ensure_ascii=False, indent=2)}")
            elif isinstance(data, dict):
                print(f"返回数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 失败")
            print(f"错误信息: {response.text}")

    except Exception as e:
        print(f"❌ 异常: {e}")

def main():
    print("="*60)
    print("广东省自然村分析系统 API 测试")
    print("="*60)

    # 1. 健康检查
    test_endpoint("健康检查", f"{BASE_URL}/health")

    # 2. 根端点
    test_endpoint("根端点", f"{BASE_URL}/")

    # 3. 元数据 - 概览
    test_endpoint("元数据概览", f"{BASE_URL}/api/metadata/stats/overview")

    # 4. 元数据 - 表信息
    test_endpoint("表信息", f"{BASE_URL}/api/metadata/stats/tables")

    # 5. 字符频率 - 全局
    test_endpoint("全局字符频率", f"{BASE_URL}/api/character/frequency/global",
                 params={"top_n": 10})

    # 6. 字符频率 - 区域
    test_endpoint("区域字符频率", f"{BASE_URL}/api/character/frequency/regional",
                 params={"region_level": "city", "top_n": 5})

    # 7. 字符倾向性
    test_endpoint("字符倾向性", f"{BASE_URL}/api/character/tendency",
                 params={"region_level": "city", "region_name": "广州市", "top_n": 5})

    # 8. 村庄搜索
    test_endpoint("村庄搜索", f"{BASE_URL}/api/village/search",
                 params={"query": "村", "limit": 5})

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
