# Villages ML Project

广东省自然村机器学习项目 (Guangdong Province Natural Villages Machine Learning Project)

## 项目简介 (Project Overview)

This project focuses on analyzing and modeling village data from Guangdong Province, China. The dataset includes geographic coordinates, administrative divisions, and language distribution information for natural villages.

## 数据结构 (Data Structure)

The project uses a SQLite database (`data/villages.db`) containing information about villages including:
- Administrative hierarchy (city, county, township, village committee)
- Village names and pinyin romanization
- Geographic coordinates (longitude, latitude)
- Language distribution
- Data sources and update timestamps

## 开发环境 (Development Environment)

### Requirements

- Python 3.8+
- See `requirements.txt` for Python dependencies

### Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
source venv/Scripts/activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 自定义技能 (Custom Skills)

This project includes custom Claude Code skills in `.claude/skills/`. Use them by typing `/skill-name` in Claude Code CLI.

## 频率分析管道 (Frequency Analysis Pipeline)

### 运行分析 (Running Analysis)

```bash
# Run frequency analysis pipeline
python scripts/run_frequency_analysis.py --run-id run_003

# Results will be saved to results/run_003/
```

### 数据库持久化 (Database Persistence)

Analysis results are automatically persisted to the SQLite database in the following tables:

- `analysis_runs`: Run metadata and configuration
- `char_frequency_global`: Global character frequency statistics
- `char_frequency_regional`: Regional character frequency (city/county/township levels)
- `regional_tendency`: Regional tendency analysis (lift, log-odds, z-score)

### 查询结果 (Querying Results)

Use the query script to retrieve analysis results from the database:

```bash
# List all analysis runs
python scripts/query_results.py --list-runs

# Query global frequency (top 20 characters)
python scripts/query_results.py --run-id run_002 --type global --top 20

# Query regional frequency for a specific region
python scripts/query_results.py --run-id run_002 --type regional --level city --region 广州市 --top 20

# Query character tendency across regions
python scripts/query_results.py --run-id run_002 --type char-tendency --char 村 --level city

# Query region tendency profile (most characteristic characters)
python scripts/query_results.py --run-id run_002 --type region-profile --level city --region 广州市 --top 20

# Query top polarized characters (highest absolute tendency)
python scripts/query_results.py --run-id run_002 --type polarized --level city --top 20

# Save results to CSV
python scripts/query_results.py --run-id run_002 --type global --top 100 --output results.csv
```

### 查询接口 (Query API)

You can also use the Python query API directly:

```python
import sqlite3
from src.data.db_query import (
    get_latest_run_id,
    get_global_frequency,
    get_regional_frequency,
    get_char_tendency_by_region,
    get_top_polarized_chars,
    get_region_tendency_profile
)

# Connect to database
conn = sqlite3.connect('data/villages.db')

# Get latest run
run_id = get_latest_run_id(conn)

# Query global frequency
df = get_global_frequency(conn, run_id, top_n=20)
print(df)

# Query character tendency across cities
df = get_char_tendency_by_region(conn, run_id, '村', 'city')
print(df)

conn.close()
```

## 形态学分析管道 (Morphology Analysis Pipeline)

### 概述 (Overview)

形态学分析提取并分析村名中的结构模式，包括：
- **后缀模式**：末尾1、2或3个字符（例如：村、新村、老围村）
- **前缀模式**：开头2或3个字符（例如：新X、老X、大X）

这揭示了命名惯例、区域模式和功能性形态学规律（例如：水系相关后缀 vs 地形相关后缀）。

### 运行分析 (Running Analysis)

```bash
# 使用默认设置运行形态学分析
python scripts/run_morphology_analysis.py --run-id morph_001

# 自定义后缀和前缀长度
python scripts/run_morphology_analysis.py --run-id morph_002 \
    --suffix-lengths 1,2,3 \
    --prefix-lengths 2,3

# 结果将保存到 results/morph_001/
```

### 数据库表 (Database Tables)

形态学分析结果持久化到以下数据表：

- `pattern_frequency_global`：全局模式频率统计
- `pattern_frequency_regional`：区域模式频率（市/县/镇三级）
- `pattern_tendency`：区域模式倾向性分析（lift、log-odds、z-score）

### 查询形态学结果 (Querying Morphology Results)

```bash
# 查询全局 suffix_1 频率（前20个模式）
python scripts/query_results.py --run-id morph_001 --type pattern-global \
    --pattern-type suffix_1 --top 20

# 查询特定区域的区域后缀模式
python scripts/query_results.py --run-id morph_001 --type pattern-regional \
    --pattern-type suffix_1 --level city --region 珠海市 --top 20

# 查询模式跨区域倾向性
python scripts/query_results.py --run-id morph_001 --type pattern-tendency \
    --pattern-type suffix_1 --pattern 涌 --level city

# 查询区域特征模式
python scripts/query_results.py --run-id morph_001 --type pattern-profile \
    --pattern-type suffix_1 --level city --region 佛山市 --top 20

# 查询最极化模式
python scripts/query_results.py --run-id morph_001 --type pattern-polarized \
    --pattern-type suffix_1 --level city --top 20
```

### 形态学查询 API (Morphology Query API)

```python
import sqlite3
from src.data.db_query import (
    get_pattern_frequency_global,
    get_pattern_frequency_regional,
    get_pattern_tendency_by_region,
    get_top_polarized_patterns,
    get_region_pattern_profile
)

# 连接数据库
conn = sqlite3.connect('data/villages.db')

# 查询全局 suffix_1 频率
df = get_pattern_frequency_global(conn, 'morph_001', 'suffix_1', top_n=20)
print(df)

# 查询模式跨城市倾向性
df = get_pattern_tendency_by_region(conn, 'morph_001', 'suffix_1', '涌', 'city')
print(df)

# 查询区域特征后缀模式
df = get_region_pattern_profile(conn, 'morph_001', 'suffix_1', 'city', '珠海市', top_n=20)
print(df)

conn.close()
```

### 预期发现 (Expected Insights)

形态学分析揭示：
- **三角洲地区**：涌、围、塘等水系相关后缀高频出现
- **山区**：坑、岭、坳等地形相关后缀高频出现
- **城乡差异**：命名多样性模式不同
- **历史模式**：老村、新村、大村、小村的分布规律
- **功能性形态学**：系统性的区域差异

## 更新日志

### 2026-02-15 - 形态学模式分析功能

**新增模块：**
- `src/preprocessing/morphology_extractor.py` - 形态学特征提取
  - 后缀模式提取：suffix_1（末1字）、suffix_2（末2字）、suffix_3（末3字）
  - 前缀模式提取：prefix_2（首2字）、prefix_3（首3字）
  - 支持可配置n-gram长度

- `src/analysis/morphology_frequency.py` - 形态学频率分析
  - 全局模式频率计算
  - 区域模式频率计算（市/县/镇三级）
  - Lift值计算（区域倾向性度量）

- `src/pipelines/morphology_pipeline.py` - 形态学分析管道
  - 端到端工作流编排
  - 支持5种模式类型并行分析
  - 自动生成分析报告

**数据库扩展：**
- 新增表：`pattern_frequency_global` - 全局模式频率
- 新增表：`pattern_frequency_regional` - 区域模式频率
- 新增表：`pattern_tendency` - 区域模式倾向性
- 新增索引：优化模式类型、区域层级、模式查询性能

**查询接口扩展（db_query.py）：**
- `get_pattern_frequency_global()` - 查询全局模式频率
- `get_pattern_frequency_regional()` - 查询区域模式频率
- `get_pattern_tendency_by_region()` - 查询模式跨区域倾向性
- `get_top_polarized_patterns()` - 查询最极化模式
- `get_region_pattern_profile()` - 查询区域特征模式

**CLI工具：**
- `scripts/run_morphology_analysis.py` - 运行形态学分析
- `scripts/test_morphology.py` - 功能验证测试

**统计方法：**
- 复用字频分析统计框架
- Lift（倾向性比值）、Log-odds（对数几率）、Z-score（显著性检验）
- 支持最小支持度过滤（min_global_support, min_regional_support）

**分析价值：**
- 揭示水系后缀（涌、围、塘、沙）在珠三角地区的高频分布规律
- 揭示地形后缀（坑、岭、坳、寨）在山区的高频分布规律
- 识别历史命名模式（新村、老村、大村、小村）的区域差异
- 量化城乡命名多样性差异（熵值分析）
- 发现功能性形态学规律（如X涌 vs X坑的地理分布差异）

**性能特征：**
- 数据规模：20万+自然村
- 运行时间：约2-3分钟（完整分析）
- 数据库增长：约150-250MB/次运行
- 模式类型：5种（suffix_1/2/3, prefix_2/3）
- 区域层级：3级（市/县/镇）

## License

TBD

