# 广东省自然村分析系统 API

FastAPI-based REST API for querying analysis results of 285K+ natural villages in Guangdong Province.

## 🆕 Latest Update (2026-02-21)

**New Endpoints Added:** Spatial-Tendency Integration API

- ✅ 4 new endpoints for querying spatial-tendency integration analysis
- ✅ 643 integration records combining spatial clustering with character tendency
- ✅ Complete documentation: `docs/SPATIAL_TENDENCY_INTEGRATION_API.md`

See [API Implementation Update](../docs/API_IMPLEMENTATION_UPDATE_20260221.md) for details.

---

## 📚 完整文档

**新增完整API文档！** 查看以下文档获取详细信息：

- **[API Reference](../docs/frontend/API_REFERENCE.md)** - 完整的端点文档（18个端点，包含请求/响应示例）
- **[Frontend Integration Guide](../docs/frontend/FRONTEND_INTEGRATION_GUIDE.md)** - Vue 3 集成指南（含代码示例）
- **[API Deployment Guide](../docs/frontend/API_DEPLOYMENT_GUIDE.md)** - 部署和配置指南（Docker、Nginx、生产环境）
- **[API Quick Reference](../docs/frontend/API_QUICK_REFERENCE.md)** - 快速参考手册（一页速查）

---

## 架构设计

### 两阶段架构

1. **离线数据处理** (已完成)
   - 重计算、特征工程、聚类分析
   - 所有结果存储在 `data/villages.db`
   - 26+ 张表，1.7GB 数据

2. **在线API服务** (本模块)
   - 轻量级查询、过滤、分页
   - 仅从数据库读取预计算结果
   - 无重计算，响应快速

## 目录结构

```
api/
├── __init__.py
├── main.py                      # FastAPI主应用
├── config.py                    # 配置文件（数据库路径）
├── dependencies.py              # 数据库连接依赖
├── models.py                    # Pydantic响应模型
├── character/                   # 字符分析API
│   ├── frequency.py            # 字符频率
│   ├── tendency.py             # 字符倾向性
│   ├── embeddings.py           # 字符嵌入
│   └── significance.py         # 字符显著性
├── semantic/                    # 语义分析API
│   ├── category.py             # 语义类别
│   └── labels.py               # 语义标签
├── spatial/                     # 空间分析API
│   ├── hotspots.py             # 空间热点
│   └── integration.py          # 空间-倾向性整合 (NEW)
├── clustering/                  # 聚类分析API
│   └── assignments.py          # 聚类分配
├── ngrams/                      # N-gram分析API
│   └── frequency.py            # N-gram频率
├── village/                     # 村庄查询API
│   └── search.py               # 搜索查询
└── metadata/                    # 元数据API
    └── stats.py                # 统计概览
```

## 快速开始

**推荐**: 查看 `../docs/API_QUICKSTART.md` 获取详细的快速启动指南。

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

**方式1: 使用启动脚本（推荐）**

```bash
# 从项目根目录运行
./start_api.sh        # Linux/Mac/Cygwin
start_api.bat         # Windows
```

启动脚本会自动检查数据库和依赖。

**方式2: 手动启动**

```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 验证运行

```bash
# 使用测试脚本
python scripts/test_api.py

# 或手动测试
curl http://127.0.0.1:8000/health
```

### 4. 访问API文档

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### 配置数据库路径（可选）

数据库默认位置: `data/villages.db`

如需更改，编辑 `api/config.py` 或使用环境变量:

```bash
export VILLAGES_DB_PATH="/path/to/villages.db"
```

## API端点概览

### 字符分析 (`/api/character`)

- `GET /character/frequency/global` - 全局字符频率
- `GET /character/frequency/regional` - 区域字符频率
- `GET /character/tendency/by-region` - 区域字符倾向性
- `GET /character/tendency/by-char` - 字符跨区域倾向性

### 语义分析 (`/api/semantic`)

- `GET /semantic/category/list` - 语义类别列表
- `GET /semantic/category/vtf/global` - 全局语义VTF
- `GET /semantic/category/vtf/regional` - 区域语义VTF
- `GET /semantic/category/tendency` - 语义倾向性

### 聚类分析 (`/api/clustering`)

- `GET /clustering/assignments` - 聚类分配结果
- `GET /clustering/assignments/by-region` - 指定区域聚类
- `GET /clustering/profiles` - 聚类画像
- `GET /clustering/metrics` - 聚类质量指标
- `GET /clustering/metrics/best` - 最优聚类配置

### 村庄查询 (`/api/village`)

- `GET /village/search` - 搜索村庄
- `GET /village/search/detail` - 村庄详情

### 元数据 (`/api/metadata`)

- `GET /metadata/stats/overview` - 系统概览
- `GET /metadata/stats/tables` - 数据库表信息

## 使用示例

### 1. 获取全局字符频率（前100个）

```bash
curl "http://localhost:8000/api/character/frequency/global?top_n=100"
```

### 2. 获取广州市的字符倾向性

```bash
curl "http://localhost:8000/api/character/tendency/by-region?region_level=city&region_name=广州市&top_n=50"
```

### 3. 搜索包含"水"的村庄

```bash
curl "http://localhost:8000/api/village/search?query=水&limit=50"
```

### 4. 获取聚类分配（KMeans, k=4）

```bash
curl "http://localhost:8000/api/clustering/assignments?algorithm=kmeans&region_level=county"
```

### 5. 获取系统概览

```bash
curl "http://localhost:8000/api/metadata/stats/overview"
```

## 查询参数说明

### 通用参数

- `run_id`: 分析运行ID（默认: `final_02_20260219`）
- `limit`: 返回数量（默认: 50，最大: 1000）
- `offset`: 偏移量（用于分页）

### 区域参数

- `region_level`: 区域级别 (`city` | `county` | `township`)
- `region_name`: 区域名称

### 过滤参数

- `top_n`: 返回前N条记录
- `min_frequency`: 最小频次过滤
- `cluster_id`: 聚类ID过滤
- `category`: 语义类别过滤

## 性能特性

### 轻量级操作（现场计算）

✅ 过滤 (WHERE条件)
✅ 排序 (ORDER BY)
✅ 分页 (LIMIT/OFFSET)
✅ Top N筛选
✅ 关键词搜索 (LIKE)
✅ 基础聚合 (COUNT, AVG)

### 预计算数据（从数据库读取）

✅ 字符频率、倾向性、显著性
✅ N-gram模式
✅ 语义VTF、共现、网络
✅ 空间特征、聚类、热点
✅ 区域聚类画像
✅ 聚类质量指标

### 禁止操作（太重）

❌ 字符嵌入训练
❌ 聚类算法运行
❌ 空间密度计算
❌ PMI/统计检验
❌ 全表扫描聚合

## 扩展指南

### 添加新的API端点

1. 在相应目录创建新文件（如 `api/pattern/ngram.py`）
2. 定义路由和端点函数
3. 在 `api/main.py` 中注册路由

示例:

```python
# api/pattern/ngram.py
from fastapi import APIRouter, Depends, Query
from ..dependencies import get_db, execute_query
from ..models import NgramFrequency

router = APIRouter(prefix="/pattern/ngram", tags=["pattern"])

@router.get("/frequency", response_model=List[NgramFrequency])
def get_ngram_frequency(
    n: int = Query(..., ge=2, le=3),
    db: sqlite3.Connection = Depends(get_db)
):
    query = "SELECT pattern, frequency, village_count FROM ngram_patterns WHERE n = ?"
    return execute_query(db, query, (n,))
```

```python
# api/main.py
from .pattern import ngram as pattern_ngram

app.include_router(pattern_ngram.router, prefix="/api")
```

### 添加新的响应模型

在 `api/models.py` 中定义:

```python
class NgramFrequency(BaseModel):
    pattern: str = Field(..., description="N-gram模式")
    frequency: int = Field(..., description="频次")
    village_count: int = Field(..., description="村庄数量")
```

## 部署建议

### 开发环境

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 生产环境

```bash
# 使用Gunicorn + Uvicorn workers
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用Docker
docker build -t villages-api .
docker run -p 8000:8000 -v /path/to/data:/app/data villages-api
```

### 性能优化

1. **数据库索引**: 确保关键字段有索引
2. **连接池**: 使用连接池管理数据库连接
3. **缓存**: 对热点数据使用Redis缓存
4. **限流**: 使用slowapi限制请求频率

## 故障排查

### 数据库连接失败

检查 `api/config.py` 中的 `DB_PATH` 是否正确:

```python
DB_PATH = "data/villages.db"  # 确保路径正确
```

### 查询返回404

确认 `run_id` 参数正确，可以先查询可用的run_id:

```bash
curl "http://localhost:8000/api/metadata/stats/tables"
```

### 响应慢

检查是否有全表扫描，确保查询使用了索引:

```sql
EXPLAIN QUERY PLAN SELECT ...
```

## 许可证

本项目为内部研究项目，未公开许可。

## 联系方式

如有问题，请联系项目维护者。
