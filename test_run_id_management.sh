#!/bin/bash
# Run_ID 管理系统测试脚本
# Test script for Run_ID Management System

echo "=========================================="
echo "Run_ID 管理系统测试"
echo "Run_ID Management System Test"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
PASSED=0
FAILED=0

# 测试函数
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"

    echo -n "测试: $name ... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $http_code)${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "1. 测试健康检查端点"
echo "-------------------"
test_endpoint "Health Check" "GET" "/health"
echo ""

echo "2. 测试管理 API - 查询所有活跃 run_id"
echo "--------------------------------------"
test_endpoint "Get All Active Run IDs" "GET" "/api/admin/run-ids/active"
echo ""

echo "3. 测试管理 API - 查询特定分析类型"
echo "-----------------------------------"
test_endpoint "Get Spatial Hotspots Run ID" "GET" "/api/admin/run-ids/active/spatial_hotspots"
test_endpoint "Get Char Embeddings Run ID" "GET" "/api/admin/run-ids/active/char_embeddings"
test_endpoint "Get Semantic Run ID" "GET" "/api/admin/run-ids/active/semantic"
echo ""

echo "4. 测试管理 API - 列出可用 run_id"
echo "----------------------------------"
test_endpoint "List Available Run IDs" "GET" "/api/admin/run-ids/available/spatial_hotspots"
echo ""

echo "5. 测试端点默认行为（使用活跃版本）"
echo "------------------------------------"
test_endpoint "Spatial Hotspots (default)" "GET" "/api/spatial/hotspots"
test_endpoint "Char Embeddings (default)" "GET" "/api/character/embeddings?char=村"
test_endpoint "Semantic Labels (default)" "GET" "/api/semantic/labels/by-character?char=村"
echo ""

echo "6. 测试端点显式指定 run_id"
echo "--------------------------"
test_endpoint "Spatial Hotspots (explicit)" "GET" "/api/spatial/hotspots?run_id=final_03_20260219_225259"
echo ""

echo "7. 测试管理 API - 更新活跃 run_id"
echo "---------------------------------"
echo "注意: 此测试会修改数据库配置"
read -p "是否继续? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    test_endpoint "Update Run ID" "PUT" "/api/admin/run-ids/active/spatial_hotspots" \
        '{"run_id":"final_03_20260219_225259","updated_by":"test_script","notes":"测试更新"}'

    # 验证更新
    test_endpoint "Verify Update" "GET" "/api/admin/run-ids/active/spatial_hotspots"
else
    echo "跳过更新测试"
fi
echo ""

echo "8. 测试管理 API - 刷新缓存"
echo "--------------------------"
test_endpoint "Refresh Cache" "POST" "/api/admin/run-ids/refresh"
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分测试失败${NC}"
    exit 1
fi