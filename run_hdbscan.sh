#!/bin/bash

echo "=========================================="
echo "HDBSCAN 空间聚类 - 安装和运行"
echo "=========================================="

# 1. 检查并安装 hdbscan
echo ""
echo "Step 1: 检查 hdbscan 库..."
if python -c "import hdbscan" 2>/dev/null; then
    echo "✓ hdbscan 已安装"
else
    echo "✗ hdbscan 未安装，正在安装..."
    pip install hdbscan
fi

# 2. 运行 HDBSCAN 聚类
echo ""
echo "Step 2: 运行 HDBSCAN 聚类..."
python scripts/core/run_hdbscan_clustering.py \
    --run-id spatial_hdbscan_v1 \
    --min-cluster-size 10 \
    --min-samples 5 \
    --delete-optimized-kde

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
