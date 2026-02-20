#!/bin/bash
# Test script for Spatial-Tendency Integration API endpoints
# Usage: ./test_integration_endpoints.sh

BASE_URL="http://localhost:8000"
API_PREFIX="/api/spatial"

echo "============================================================"
echo "Testing Spatial-Tendency Integration API Endpoints"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
TOTAL=0
PASSED=0

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"

    TOTAL=$((TOTAL + 1))
    echo "Test $TOTAL: $name"
    echo "URL: $url"

    response=$(curl -s -w "\n%{http_code}" "$url")
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (Status: $status_code)"
        PASSED=$((PASSED + 1))

        # Show sample data
        if [ "$status_code" -eq 200 ]; then
            echo "Sample response:"
            echo "$body" | python3 -m json.tool 2>/dev/null | head -20 || echo "$body" | head -5
        fi
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_status, Got: $status_code)"
        echo "Response: $body"
    fi
    echo ""
}

# Check if server is running
echo "Checking if API server is running..."
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: API server is not running${NC}"
    echo "Please start the server first:"
    echo "  uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"
    exit 1
fi
echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Test 1: Get all integration results
test_endpoint \
    "Get all integration results" \
    "$BASE_URL$API_PREFIX/integration"

# Test 2: Get integration results with limit
test_endpoint \
    "Get integration results (limit=5)" \
    "$BASE_URL$API_PREFIX/integration?limit=5"

# Test 3: Get integration results for character "村"
test_endpoint \
    "Get integration by character (村)" \
    "$BASE_URL$API_PREFIX/integration/by-character/村"

# Test 4: Get integration results for cluster 0
test_endpoint \
    "Get integration by cluster (0)" \
    "$BASE_URL$API_PREFIX/integration/by-cluster/0"

# Test 5: Get integration summary
test_endpoint \
    "Get integration summary" \
    "$BASE_URL$API_PREFIX/integration/summary"

# Test 6: Filter by min_cluster_size
test_endpoint \
    "Filter by min_cluster_size (10000)" \
    "$BASE_URL$API_PREFIX/integration?min_cluster_size=10000&limit=10"

# Test 7: Filter by min_spatial_coherence
test_endpoint \
    "Filter by min_spatial_coherence (0.9)" \
    "$BASE_URL$API_PREFIX/integration?min_spatial_coherence=0.9&limit=10"

# Test 8: Filter by character
test_endpoint \
    "Filter by character (新)" \
    "$BASE_URL$API_PREFIX/integration?character=新"

# Test 9: Invalid character (should return 404)
test_endpoint \
    "Invalid character (should fail)" \
    "$BASE_URL$API_PREFIX/integration/by-character/不存在" \
    404

# Test 10: Invalid cluster (should return 404)
test_endpoint \
    "Invalid cluster (should fail)" \
    "$BASE_URL$API_PREFIX/integration/by-cluster/99999" \
    404

# Summary
echo "============================================================"
echo "Test Results Summary"
echo "============================================================"
echo "Total tests: $TOTAL"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$((TOTAL - PASSED))${NC}"
echo ""

if [ $PASSED -eq $TOTAL ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
