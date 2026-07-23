# 后端区域层级统一配置指南

## 背景

ML 模块已完成重构：**所有 `'city'/'county'/'township'/'committee'` 硬编码字符串已消除**。
现在 `src/schema.py` 中的 `REGION_LEVELS` 是唯一数据源，切换广东→全国数据只需改一行。

后端（api/ 目录）目前仍有大量硬编码，建议采用相同模式统一。

---

## ML 模块的方案

### 核心机制

```python
# src/schema.py —— 唯一的层级定义
_DEFAULT_REGION_LEVELS = ['city', 'county', 'township', 'committee']
REGION_LEVELS = list(_DEFAULT_REGION_LEVELS)

def init_region_levels(levels: list[str]) -> None:
    """原地替换，所有已有的 import 自动更新"""
    REGION_LEVELS.clear()
    REGION_LEVELS.extend(levels)

def level_index(level: str) -> int:
    """返回 1-based 索引"""
    return REGION_LEVELS.index(level) + 1
```

### 使用方式

```python
# 所有代码用位置索引，从不写死字符串
from src.schema import REGION_LEVELS

REGION_LEVELS[0]  # 'city'
REGION_LEVELS[1]  # 'county'
REGION_LEVELS[2]  # 'township'
REGION_LEVELS[3]  # 'committee'

# SQL 中用 f-string 插值
f"WHERE region_level = '{REGION_LEVELS[0]}'"

# 遍历层级
for level in REGION_LEVELS[:3]:
    process(level)
```

### 切换数据源

```json
// config/pipeline.guangdong.json
{ "region_levels": ["city", "county", "township", "committee"] }

// config/pipeline.national.json（未来）
{ "region_levels": ["province", "city", "county", "town"] }
```

改 config 后，`merge_phase_definitions()` 自动调用 `init_region_levels()`，
所有 import 过 `REGION_LEVELS` 的模块立刻看到新值。

---

## 后端现状分析

### 已发现的硬编码点

`api/` 目录中大量 endpoint 直接使用字符串 `'city'`/`'county'`/`'township'`：

```python
# api/character/frequency.py
region_level: str = Query(..., regex="^(city|county|township)$")

# api/character/tendency.py
elif city is not None and region_level == 'township':  # 硬编码

# api/schema_runtime.py
_REGION_LEVEL_MAP = {"市级": "city", "区县级": "county", "乡镇级": "township"}
```

### `town` vs `township` 不一致

部分表用 `town` 而非 `township` 作为物理列名：

| 表 | 实际列名 |
|---|---|
| `village_features` | `town` |
| `village_spatial_features` | `town` |
| `region_spatial_aggregates` | `town` |
| `town_aggregates` | `town` |
| `char_regional_analysis` | `township` |
| `tendency_significance` | `township` |
| `semantic_regional_analysis` | `township` |
| `pattern_regional_analysis` | `township` |

`schema_config.py` 第 742-768 行中 `township` 层级的 `region_col` 是 `"town"`，
但 API endpoint 接受的参数值又是 `township`。这不一致容易导致 bug。

---

## 建议：后端统一方案

### Step 1: 引入 REGION_LEVELS

```python
# api/schema_keys.py（新文件或加到现有文件）
REGION_LEVELS = ['city', 'county', 'township']

# 简写
CITY, COUNTY, TOWNSHIP = REGION_LEVELS  # 如果确定永远只用这三层
```

或者直接 import ML 模块的定义：
```python
from src.schema import REGION_LEVELS
```

### Step 2: 替换所有硬编码

**Before（现状）:**
```python
region_level: str = Query(..., regex="^(city|county|township)$")
if region_level == 'city':
    group_cols = ['city']
elif region_level == 'county':
    group_cols = ['city', 'county']
elif region_level == 'township':
    group_cols = ['city', 'county', 'township']
```

**After（建议）:**
```python
from src.schema import REGION_LEVELS

LEVEL_CHOICES = "|".join(REGION_LEVELS[:3])
region_level: str = Query(..., regex=f"^({LEVEL_CHOICES})$")

# 用位置而非名字
LEVEL_GROUP_COLS = {
    REGION_LEVELS[0]: [REGION_LEVELS[0]],
    REGION_LEVELS[1]: [REGION_LEVELS[0], REGION_LEVELS[1]],
    REGION_LEVELS[2]: [REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2]],
}
```

### Step 3: 统一 `town` → `township`

- `schema_config.py` 中 `town` 列名改为 `township`
- 如不能改 DB 列名（兼容旧数据），至少在配置层做映射：`"physical_col": "town", "logical_col": "township"`

### Step 4: 特殊城市处理去硬编码

```python
# 现状：硬编码东莞市/中山市
elif city is not None and region_level == 'township':
    AND ({county_col} IS NULL OR {county_col} = '')

# 建议：用配置驱动
DIRECT_ADMIN_CITIES = {'东莞市', '中山市'}  # 或从 region_hierarchy_stats 表查询
if city in DIRECT_ADMIN_CITIES and region_level == REGION_LEVELS[2]:
    ...
```

---

## 当前数据状态

### 核心表

| 表名 | 用途 | 层级字段 |
|------|------|---------|
| `广东省自然村` | 原始数据（285K+ 自然村） | `市级`, `区县级`, `乡镇级`, `村委会` |
| `广东省自然村_预处理` | 预处理后（去前缀、规范名、字符集） | 同原始表 |
| `char_regional_analysis` | 字符频率 + 倾向性 + 显著性 | `region_level`, `region_name`, `city`, `county`, `township` |
| `char_frequency_global` | 全局字符频率 | — |
| `pattern_regional_analysis` | 后缀/前缀模式频率 + 倾向性 | 同 char_regional_analysis |
| `semantic_regional_analysis` | 语义 VTF + 倾向性 | 同 char_regional_analysis |
| `village_features` | 村庄级特征（230+ 维度） | `city`, `county`, `town` ← 注意是 town |
| `village_spatial_features` | 空间特征（k-NN、密度、隔离度） | `city`, `county`, `town` |
| `spatial_clusters` | 空间聚类结果 | — |

`run_id` 已从合并表中移除。查询时不再需要 `run_id` 参数（少数表例外，见下文）。

### 仍需要 run_id 的表

- `char_embeddings` — 嵌入向量可能有多个训练版本
- `char_similarity` — 字符相似度预计算
- `cluster_assignments` — 聚类分配
- `village_features` — 村庄特征
- `spatial_hotspots` — 空间热点
- `active_run_ids` — 后端查询最新 run_id 的索引表

### active_run_ids 表

```sql
SELECT run_id FROM active_run_ids WHERE analysis_type = 'char_embeddings'
```

后端应优先查 `active_run_ids`，fallback 到 `ORDER BY run_id DESC LIMIT 1`。

---

## 给后端同事的关键信息

1. **层级名字不再硬编码**。如果要新增「省级」分析，改 `REGION_LEVELS` 一行即可，所有循环、SQL、校验自动生效。

2. **config 驱动切换数据源**。广东用 `['city','county','township','committee']`，全国用 `['province','city','county','town']`，改 config.json 就行，不用改代码。

3. **pipelines 现在统一在 `src/pipelines/`**。如果后端需要触发重新计算，直接 import pipeline 函数而非 subprocess 调用脚本：
   ```python
   from src.pipelines.tendency_pipeline import run_tendency_pipeline
   result = run_tendency_pipeline(db_path, run_id)
   ```

4. **`town` vs `township` 建议统一**。目前部分特征表用 `town`，分析表用 `township`，建议逐步迁移到 `township` 或至少在配置层显式映射。
