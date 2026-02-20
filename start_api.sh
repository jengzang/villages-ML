#!/bin/bash
# API 启动脚本
# API Startup Script

echo "=========================================="
echo "广东省自然村分析系统 API"
echo "Guangdong Villages Analysis API"
echo "=========================================="
echo ""

# 检查数据库文件
if [ ! -f "data/villages.db" ]; then
    echo "❌ 错误: 数据库文件不存在"
    echo "   Error: Database file not found at data/villages.db"
    exit 1
fi

echo "✓ 数据库文件: data/villages.db"

# 检查数据库大小
DB_SIZE=$(du -h data/villages.db | cut -f1)
echo "✓ 数据库大小: $DB_SIZE"
echo ""

# 检查依赖
echo "检查依赖..."
python -c "import fastapi; import uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ FastAPI 依赖未安装"
    echo "   请运行: pip install -r api/requirements.txt"
    exit 1
fi
echo "✓ 依赖已安装"
echo ""

# 启动API
echo "启动 API 服务..."
echo "访问: http://127.0.0.1:8000/docs"
echo "按 Ctrl+C 停止服务"
echo ""
echo "=========================================="
echo ""

uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
