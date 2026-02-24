# API 使用指南 - 快速开始

## 1. 启动 API 服务器

### 方法 A: 使用启动脚本（推荐）

```bash
./start_api.sh
```

### 方法 B: 直接使用 uvicorn

```bash
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

启动后，你会看到：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 2. 访问 API 文档

启动后，在浏览器中打开：

- **Swagger UI（推荐）**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

Swagger UI 提供交互式界面，可以直接在浏览器中测试 API。

## 3. 查询方式

### 方式 1: 使用浏览器（最简单）

直接在浏览器地址栏输入 URL：

```
http://127.0.0.1:8000/api/spatial/hotspots
http://127.0.0.1:8000/api/spatial/hotspots?min_density=0.5
http://127.0.0.1:8000/api/spatial/hotspots?min_village_count=100
```

### 方式 2: 使用 Swagger UI（推荐）

1. 打开 http://127.0.0.1:8000/docs
2. 找到你想测试的端点（例如 `/api/spatial/hotspots`）
3. 点击端点展开
4. 点击 "Try it out" 按钮
5. 输入参数值
6. 点击 "Execute" 按钮
7. 查看响应结果

### 方式 3: 使用 curl 命令

```bash
# 基本查询
curl "http://127.0.0.1:8000/api/spatial/hotspots"

# 带参数查询
curl "http://127.0.0.1:8000/api/spatial/hotspots?min_density=0.5"

# 多个参数
curl "http://127.0.0.1:8000/api/spatial/hotspots?min_density=0.5&min_village_count=100"

# 格式化输出（需要安装 jq）
curl "http://127.0.0.1:8000/api/spatial/hotspots" | jq
```

### 方式 4: 使用 Python requests

```python
import requests

# 基本查询
response = requests.get("http://127.0.0.1:8000/api/spatial/hotspots")
data = response.json()
print(data)

# 带参数查询
params = {
    "min_density": 0.5,
    "min_village_count": 100
}
response = requests.get("http://127.0.0.1:8000/api/spatial/hotspots", params=params)
data = response.json()
print(data)
```

## 4. 常用端点示例

### 4.1 空间热点分析

```bash
# 获取所有热点
curl "http://127.0.0.1:8000/api/spatial/hotspots"

# 筛选高密度热点
curl "http://127.0.0.1:8000/api/spatial/hotspots?min_density=0.8"

# 筛选大规模热点
curl "http://127.0.0.1:8000/api/spatial/hotspots?min_village_count=200"

# 组合条件
curl "http://127.0.0.1:8000/api/spatial/hotspots?min_density=0.5&min_village_count=100"

# 使用特定 run_id
curl "http://127.0.0.1:8000/api/spatial/hotspots?run_id=final_03_20260219_225259"
```

### 4.2 字符嵌入查询

```bash
# 查询单个字符的嵌入
curl "http://127.0.0.1:8000/api/character/embeddings?char=村"

# 查询相似字符
curl "http://127.0.0.1:8000/api/character/embeddings/similar?char=村&top_k=10"

# 筛选高相似度
curl "http://127.0.0.1:8000/api/character/embeddings/similar?char=村&top_k=10&min_similarity=0.7"
```

### 4.3 语义标签查询

```bash
# 查询字符的语义标签
curl "http://127.0.0.1:8000/api/semantic/labels/by-character?char=村"

# 查询某个类别的所有字符
curl "http://127.0.0.1:8000/api/semantic/labels/by-category?category=settlement"

# 筛选高置信度
curl "http://127.0.0.1:8000/api/semantic/labels/by-category?category=settlement&min_confidence=0.8"
```

### 4.4 聚类分析

```bash
# 获取聚类分配
curl "http://127.0.0.1:8000/api/clustering/assignments?region_level=county&algorithm=kmeans"

# 筛选特定聚类
curl "http://127.0.0.1:8000/api/clustering/assignments?region_level=county&algorithm=kmeans&cluster_id=0"

# 查询聚类画像
curl "http://127.0.0.1:8000/api/clustering/profiles?algorithm=kmeans"
```

### 4.5 N-gram 分析

```bash
# 查询 2-gram
curl "http://127.0.0.1:8000/api/ngrams/frequency?n=2&region_level=city"

# 查询特定区域
curl "http://127.0.0.1:8000/api/ngrams/frequency?n=2&region_level=city&region_name=广州市"

# 限制返回数量
curl "http://127.0.0.1:8000/api/ngrams/frequency?n=2&region_level=city&top_k=20"
```

### 4.6 Run_ID 管理（新功能）

```bash
# 查询所有活跃 run_id
curl "http://127.0.0.1:8000/api/admin/run-ids/active"

# 查询特定分析类型
curl "http://127.0.0.1:8000/api/admin/run-ids/active/spatial_hotspots"

# 列出可用的 run_id
curl "http://127.0.0.1:8000/api/admin/run-ids/available/spatial_hotspots"

# 更新活跃 run_id
curl -X PUT "http://127.0.0.1:8000/api/admin/run-ids/active/spatial_hotspots" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "new_run_id", "notes": "更新说明"}'
```

## 5. 参数说明

### 常用参数类型

**分页参数:**
- `limit`: 返回记录数（默认 100）
- `offset`: 偏移量（默认 0）

**筛选参数:**
- `min_*`: 最小值筛选（如 `min_density`, `min_frequency`）
- `max_*`: 最大值筛选
- `*_name`: 名称筛选（如 `region_name`, `city_name`）

**排序参数:**
- 大多数端点按相关性自动排序

**Run_ID 参数:**
- `run_id`: 指定分析运行版本（留空使用活跃版本）

### URL 编码

如果参数包含中文或特殊字符，需要进行 URL 编码：

```bash
# 错误（中文未编码）
curl "http://127.0.0.1:8000/api/ngrams/frequency?region_name=广州市"

# 正确（使用 --data-urlencode）
curl -G "http://127.0.0.1:8000/api/ngrams/frequency" \
  --data-urlencode "region_name=广州市"

# 或者手动编码
curl "http://127.0.0.1:8000/api/ngrams/frequency?region_name=%E5%B9%BF%E5%B7%9E%E5%B8%82"
```

## 6. 响应格式

所有端点返回 JSON 格式：

```json
{
  "hotspot_id": 1,
  "center_lon": 113.2644,
  "center_lat": 23.1291,
  "density_score": 0.85,
  "village_count": 250,
  "radius_km": 5.2
}
```

## 7. 错误处理

**常见错误码:**
- `200`: 成功
- `404`: 未找到资源
- `422`: 参数验证失败
- `500`: 服务器错误

**错误响应示例:**
```json
{
  "detail": "No spatial hotspots found for run_id: invalid_run_id"
}
```

## 8. 实用技巧

### 技巧 1: 使用 jq 格式化输出

```bash
curl "http://127.0.0.1:8000/api/spatial/hotspots" | jq '.[0]'
```

### 技巧 2: 保存响应到文件

```bash
curl "http://127.0.0.1:8000/api/spatial/hotspots" > hotspots.json
```

### 技巧 3: 查看响应头

```bash
curl -i "http://127.0.0.1:8000/api/spatial/hotspots"
```

### 技巧 4: 测量响应时间

```bash
curl -w "\nTime: %{time_total}s\n" "http://127.0.0.1:8000/api/spatial/hotspots"
```

### 技巧 5: 使用别名简化命令

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
alias api="curl -s http://127.0.0.1:8000/api"

# 使用
api/spatial/hotspots | jq
```

## 9. 停止 API 服务器

按 `Ctrl+C` 停止服务器。

## 10. 故障排除

### 问题 1: 端口已被占用

```bash
# 查找占用端口的进程
netstat -ano | grep :8000

# 或使用不同端口
uvicorn api.main:app --port 8001
```

### 问题 2: 数据库文件未找到

确保在项目根目录运行，且 `data/villages.db` 存在。

### 问题 3: 依赖未安装

```bash
pip install -r requirements.txt
```

## 11. 下一步

1. 浏览 Swagger UI 查看所有可用端点
2. 阅读完整 API 文档: `docs/frontend/API_REFERENCE.md`
3. 查看 Run_ID 管理指南: `docs/guides/RUN_ID_MANAGEMENT_QUICK_GUIDE.md`