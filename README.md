# Villages ML Project

广东省自然村机器学习项目 (Guangdong Province Natural Villages Machine Learning Project)

## 项目简介 (Project Overview)

本项目专注于广东省自然村数据的统计分析和机器学习建模，包含 **285,000+ 自然村**的地理坐标、行政区划、语言分布等信息。

主要功能：
- 字符频率统计与区域倾向性分析
- 语义标注与共现网络分析
- 空间分布模式与热点检测
- 聚类分析与命名模式识别
- N-gram 模式提取与语义组合分析

**📖 想了解完整功能？** 查看 [功能总览文档](docs/FEATURE_OVERVIEW.md)（6300+ 行详细说明）

---

## 🚀 第一次使用？从这里开始！

### 1️⃣ 环境准备

**系统要求**：
- Python 3.8+ （推荐 3.10+）
- 2GB+ 可用内存
- 5GB+ 磁盘空间

**安装依赖**：

```bash
# 克隆项目后，进入项目目录
cd villages-ML

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows (Git Bash):
source venv/Scripts/activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖包
pip install -r requirements.txt
```

### 2️⃣ 检查数据库

确认数据库文件存在：

```bash
# 检查数据库文件
ls -lh data/villages.db

# 应该看到一个 2GB+ 的文件
# 如果文件不存在或太小，请联系项目维护者获取完整数据库
```

### 3️⃣ 运行第一个分析

**⚠️ 重要：必须先运行 Phase 0（数据预处理）**

Phase 0 会创建预处理表 `广东省自然村_预处理`，所有其他阶段都依赖这个表。

```bash
# 第一步：运行数据预处理（必须！）
python run_all_phases.py --phases 0

# 第二步：查看所有可用阶段
python run_all_phases.py --list

# 第三步：运行核心分析阶段（Phase 0-7，约 30-50 分钟）
python run_all_phases.py --group core

# 或者运行所有 15 个阶段（约 1-2 小时）
python run_all_phases.py --all
```

### 4️⃣ 查看结果

```bash
# 查询分析结果
python scripts/query_results.py --list-runs

# 查看全局字符频率（前 20 个）
python scripts/query_results.py --run-id <run_id> --type global --top 20
```

---

## 📖 快速参考

### 常用命令

```bash
# 查看所有阶段
python run_all_phases.py --list

# 查看某个阶段的详细信息
python run_all_phases.py --info 12

# 预览执行计划（不实际运行）
python run_all_phases.py --all --dry-run

# 运行特定阶段
python run_all_phases.py --phases 0,1,2,3

# 运行阶段组
python run_all_phases.py --group core        # 核心阶段 (0-7)
python run_all_phases.py --group statistical # 统计阶段 (8-10)
python run_all_phases.py --group advanced    # 高级阶段 (11-17)
```

### 分析阶段概览

项目包含 **17 个分析阶段**，分为三组：

**核心阶段 (Phase 0-7)** - 必需的基础分析：
| Phase | 名称 | 说明 | 时间 |
|-------|------|------|------|
| 0 | 数据预处理 | ⚠️ **必须首先运行** - 清理村名，去除前缀 | 2-5 min |
| 1 | 字符嵌入 | Word2Vec 训练（9,209 字符，100 维） | 5-10 min |
| 2 | 频率分析 | 字符频率与区域倾向性统计 | 3-5 min |
| 3 | 语义分析 | 语义标注与共现网络（9 类别） | 3-5 min |
| 4 | 空间分析 | 空间分布、k-NN、DBSCAN 聚类 | 5-10 min |
| 5 | 特征工程 | 提取 230+ 特征 | 3-5 min |
| 6 | 聚类分析 | KMeans 区域聚类 | 3-5 min |
| 7 | 特征物化 | 预计算特征存储 | 2-3 min |

**统计阶段 (Phase 8-10)** - 统计显著性检验：
| Phase | 名称 | 说明 | 时间 |
|-------|------|------|------|
| 8 | 倾向性分析 | Lift、Log-odds 计算 | 2-3 min |
| 9 | Z-score 标准化 | 标准化倾向性分数 | 2-3 min |
| 10 | 显著性检验 | Chi-square、p-value、效应量 | 2-3 min |

**高级阶段 (Phase 11-17)** - 可选的深度分析：
| Phase | 名称 | 说明 | 时间 |
|-------|------|------|------|
| 11 | 查询策略 | 在线服务策略框架 | 1-2 min |
| 12 | N-gram 分析 | 提取 1,909,959 个模式 | 5-10 min |
| 13 | 空间热点 | 热点检测（8 个热点） | 2-3 min |
| 14 | 语义组合 | 语义组合模式（8 种） | 3-5 min |
| 15 | 区域相似度 | 区域命名相似度分析 | 2-3 min |
| 16 | 语义中心性 | 语义网络中心性分析 | 2-3 min |
| 17 | 混合分析 | 混合特征分析 | 3-5 min |

**完整运行时间**：约 1-2 小时（全部 17 个阶段）

---

## 📚 详细文档

### 🌟 核心文档（必读）

- **📖 功能总览（最详细）**：[docs/FEATURE_OVERVIEW.md](docs/FEATURE_OVERVIEW.md) ⭐
  - 6300+ 行完整文档
  - 系统架构、前后端技术栈
  - 7 大功能模块详解（搜索、字符、语义、空间、模式、区域、ML）
  - 30+ API 端点完整说明
  - 数据库架构、算法详情
  - **推荐：想深入了解项目的所有功能，从这里开始！**

- **🚀 运行指南**：[docs/RUN_ALL_PHASES_GUIDE.md](docs/RUN_ALL_PHASES_GUIDE.md)
  - 如何使用 `run_all_phases.py`
  - 17 个分析阶段详解
  - 命令行参数说明
  - 常见问题解答

### 📊 其他文档

- **项目状态报告**：[docs/reports/PROJECT_STATUS.md](docs/reports/PROJECT_STATUS.md)
- **API 参考文档**：[docs/frontend/API_REFERENCE.md](docs/frontend/API_REFERENCE.md)
- **文档索引**：[docs/README.md](docs/README.md)

---

## 🔧 高级功能

### 配置常量 (Configuration Constants)

所有预处理常量集中在 `src/preprocessing/constants.py` 中：

```python
# 行政分隔符
DELIMITERS = ["社区", "村", "寨", "片", "管区", "农场", "区"]

# 方位和大小修饰词
MODIFIERS = ["大", "小", "新", "老", "東", "西", "南", "北", "上", "下"]

# 同音字映射
HOMOPHONE_PAIRS = {
    "湖下": ["湖厦", "湖夏"],
    "石": ["时"],
}
```

修改这些常量后，重新运行 Phase 0 即可应用新配置：

```bash
python run_all_phases.py --phases 0
```

### 数据库结构 (Database Structure)

项目使用 SQLite 数据库 (`data/villages.db`)，包含 44 个表：

**原始数据表**：
- `广东省自然村`：原始村庄数据（285K+ 记录）
- `广东省自然村_预处理`：预处理后的数据（Phase 0 生成）

**分析结果表**（部分）：
- `char_regional_analysis`：字符区域分析（频率+倾向性）
- `pattern_regional_analysis`：模式区域分析
- `semantic_regional_analysis`：语义区域分析
- `village_features`：村庄特征（物化）
- `spatial_clusters`：空间聚类结果
- `ngram_frequency`：N-gram 频率
- 更多表请参考 [docs/reports/DATABASE_STATUS_REPORT.md](docs/reports/DATABASE_STATUS_REPORT.md)

---

## 🛠️ 开发指南

### 项目结构

```
villages-ML/
├── data/                   # SQLite 数据库
├── scripts/                # 分析脚本
│   ├── core/              # 核心阶段脚本 (Phase 0-17)
│   └── experimental/      # 实验性功能
├── src/                    # 源代码模块
│   ├── preprocessing/     # 数据预处理
│   ├── analysis/          # 分析算法
│   ├── clustering/        # 聚类算法
│   └── data/              # 数据访问层
├── docs/                   # 文档
├── api/                    # FastAPI 后端（30+ 端点）
├── tests/                  # 单元测试
├── run_all_phases.py      # 主执行脚本
└── requirements.txt       # Python 依赖
```

### 自定义技能 (Custom Skills)

项目包含 Claude Code 自定义技能（`.claude/skills/`）：
- `/tendency-analysis`：倾向性分析技能
- 在 Claude Code CLI 中使用 `/skill-name` 调用

---

## 🔧 高级功能

以下是项目的高级功能，适合深入研究和定制化分析。

### 查询分析结果

```bash
# 列出所有运行记录
python scripts/query_results.py --list-runs

# 查询全局字符频率（前 20 个）
python scripts/query_results.py --run-id <run_id> --type global --top 20

# 查询特定区域的字符频率
python scripts/query_results.py --run-id <run_id> --type regional --level city --region 广州市 --top 20

# 查询字符的区域倾向性
python scripts/query_results.py --run-id <run_id> --type char-tendency --char 村 --level city

# 导出结果到 CSV
python scripts/query_results.py --run-id <run_id> --type global --top 100 --output results.csv
```

### Python API 查询

```python
import sqlite3
from src.data.db_query import (
    get_latest_run_id,
    get_global_frequency,
    get_regional_frequency,
    get_char_tendency_by_region
)

# 连接数据库
conn = sqlite3.connect('data/villages.db')

# 获取最新运行 ID
run_id = get_latest_run_id(conn)

# 查询全局频率
df = get_global_frequency(conn, run_id, top_n=20)
print(df)

# 查询字符跨城市倾向性
df = get_char_tendency_by_region(conn, run_id, '村', 'city')
print(df)

conn.close()
```

### 单独运行特定分析

除了使用 `run_all_phases.py`，你也可以单独运行特定的分析脚本：

```bash
# 形态学分析
python scripts/run_morphology_analysis.py --run-id morph_001

# 村级聚类（MiniBatchKMeans）
python scripts/run_village_clustering.py --db-path data/villages.db --output-dir results/clustering --k 50

# DBSCAN 聚类（异常检测）
python scripts/run_dbscan_clustering.py --db-path data/villages.db --output-dir results/dbscan --eps 0.5

# GMM 聚类（软聚类）
python scripts/run_gmm_clustering.py --db-path data/villages.db --output-dir results/gmm --n-components 50

# 聚类可视化
python scripts/visualize_clusters.py --db-path data/villages.db --cluster-file results/clustering/village_clusters.csv --output-dir results/viz
```

---

## 📊 分析结果示例

### 字符频率分析

全局高频字符（前 10）：
- 村 (87,919 次，30.76%)
- 新 (45,123 次，15.82%)
- 大 (38,456 次，13.47%)
- 坑 (35,789 次，12.54%)
- ...

### 区域倾向性分析

珠三角地区特征字符：
- 涌（Lift: 8.5）- 水系相关
- 围（Lift: 6.2）- 聚落形态
- 塘（Lift: 4.8）- 水系相关

山区特征字符：
- 坑（Lift: 7.3）- 地形相关
- 岭（Lift: 5.9）- 地形相关
- 坳（Lift: 4.5）- 地形相关

### 语义标签统计

| 语义类别 | 村庄数量 | 百分比 |
|---------|---------|--------|
| settlement（聚落） | 87,919 | 30.76% |
| direction（方位） | 77,069 | 26.96% |
| mountain（山地） | 75,030 | 26.25% |
| water（水系） | 47,324 | 16.55% |
| clan（姓氏） | 29,599 | 10.35% |

---

## 🚢 部署说明

### 在线服务策略

项目实现了"离线重、在线轻"的部署策略：

**离线阶段**（无性能限制）：
- 运行所有 17 个分析阶段
- 预计算所有特征和统计结果
- 存储到数据库

**在线阶段**（2 核 / 2GB 服务器）：
- 仅加载预计算结果
- 强制查询限制（最大 500-5000 行）
- 禁止全表扫描
- 支持分页查询

### 启动 API 服务器

```bash
# 启动 FastAPI 服务器
bash start_api.sh

# 或手动启动
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```

API 文档：访问 `http://localhost:8000/docs`

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率的测试
pytest --cov=src tests/

# 运行特定测试
pytest tests/test_preprocessing.py
```

---

## 📝 更新日志

### 2026-03-04
- ✅ 完善 README.md，添加"第一次使用"指南
- ✅ 优化文档结构，突出快速开始部分

### 2026-02-24
- ✅ 数据库优化：从 5.45GB 减少到 2.3GB（58% 减少）
- ✅ 移除 run_id 冗余，合并频率+倾向性表
- ✅ 添加 17 个索引优化查询性能

### 2026-02-16
- ✅ 实现在线服务策略框架（Phase 11）
- ✅ 实现特征物化管道（Phase 10）
- ✅ 实现村级聚类分析（MiniBatchKMeans, DBSCAN, GMM）
- ✅ 实现 UMAP 可视化

### 2026-02-15
- ✅ 实现形态学模式分析功能
- ✅ 添加 N-gram 分析（Phase 12）
- ✅ 添加空间热点检测（Phase 13）

### 2026-02-14
- ✅ 实现语义分析管道（Phase 3）
- ✅ 实现形态学分析管道
- ✅ 添加 9 个语义类别的虚拟词频（VTF）分析

### 2026-02-13
- ✅ 实现字符频率分析管道（Phase 2）
- ✅ 实现区域倾向性分析
- ✅ 添加数据库持久化功能

---

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

TBD

---

## 📧 联系方式

如有问题或建议，请：
- 提交 Issue
- **查看完整功能文档**：[docs/FEATURE_OVERVIEW.md](docs/FEATURE_OVERVIEW.md) ⭐（最详细）
- 查看文档索引：[docs/README.md](docs/README.md)
- 参考运行指南：[docs/RUN_ALL_PHASES_GUIDE.md](docs/RUN_ALL_PHASES_GUIDE.md)

---

## 🙏 致谢

感谢所有为广东省自然村数据收集和整理做出贡献的人员。

---

<details>
<summary>📦 详细功能列表（点击展开）</summary>

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
- `tendency_significance`: Statistical significance testing (p-values, effect sizes, confidence intervals) ✨ NEW

### 统计显著性检验 (Statistical Significance Testing) ✨ NEW

The system now includes statistical significance testing to identify meaningful regional naming patterns:

```bash
# Initialize database tables
python scripts/init_tendency_tables.py

# Run analysis with significance testing
python scripts/test_significance.py

# Query significant patterns
python scripts/query_tendency.py --run-id test_sig_1771260439 --significant-only

# Filter by effect size
python scripts/query_tendency.py --run-id test_sig_1771260439 --min-effect-size 0.1

# Export to CSV
python scripts/query_tendency.py --run-id test_sig_1771260439 --output results.csv
```

**Features**:
- Chi-square test for character-region associations
- P-values and significance levels (***,  **, *, ns)
- Effect sizes (Cramér's V) for measuring association strength
- 95% confidence intervals (Wilson score method)
- Fast computation: 27,000+ tests in ~3 seconds

**Documentation**: See `docs/TENDENCY_SIGNIFICANCE_GUIDE.md` for complete usage guide.

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

## 聚类分析管道 (Clustering Analysis Pipeline)

### 概述 (Overview)

聚类分析基于语义和形态学特征对区域进行分组，揭示广东省村名的深层模式。该系统使用KMeans算法对县级/市级/镇级区域进行聚类，生成可解释的聚类画像。

### 运行分析 (Running Analysis)

```bash
# 运行县级聚类分析
python scripts/run_clustering_analysis.py \
    --semantic-run-id semantic_001 \
    --morphology-run-id morph_001 \
    --output-run-id cluster_001 \
    --region-level county
```

### 数据库表 (Database Tables)

聚类分析结果持久化到以下数据表：

- `region_vectors`：区域特征向量（语义+形态学+多样性特征）
- `cluster_assignments`：区域聚类分配结果
- `cluster_profiles`：聚类画像（区分性特征、代表性区域）
- `clustering_metrics`：聚类评估指标（轮廓系数、DB指数等）

### 查询聚类结果 (Querying Clustering Results)

```bash
# 查询聚类分配
python scripts/query_results.py --run-id cluster_001 --type cluster-assignments

# 查询特定聚类的画像
python scripts/query_results.py --run-id cluster_001 --type cluster-profile --cluster-id 0

# 查询聚类评估指标
python scripts/query_results.py --run-id cluster_001 --type cluster-metrics
```

## 更新日志

### 2026-02-16 - 村级聚类分析扩展

**新增功能：** 实现三种互补的村级聚类方法

**新增脚本：**
- `scripts/run_dbscan_clustering.py` - DBSCAN聚类（异常检测）
  - 基于密度的聚类算法
  - 自动识别噪声点（异常村名）
  - 无需预先指定聚类数量
  - 支持任意形状的聚类

- `scripts/run_gmm_clustering.py` - GMM聚类（软聚类）
  - 高斯混合模型
  - 提供概率分布（每个村庄属于各聚类的概率）
  - 不确定性量化（识别命名模式模糊的村庄）
  - 支持多种协方差类型（full, tied, diag, spherical）

- `scripts/visualize_clusters.py` - 聚类可视化
  - UMAP降维至2D空间
  - 生成聚类散点图
  - 支持PCA降维作为备选方案
  - 导出2D坐标数据

**分析价值：**
- **DBSCAN**：识别独特/罕见村名（噪声点），揭示文化异常点
- **GMM**：量化命名模式的不确定性，识别文化/语言边界村庄
- **可视化**：直观展示聚类质量，发现子聚类和过渡区域

**性能特征：**
- 数据规模：284,764个自然村
- 特征维度：106维 → PCA降至50维
- 运行时间：DBSCAN约3-5分钟，GMM约5-8分钟，UMAP约10-15分钟
- 内存占用：< 2GB（符合部署约束）

**方法对比：**
- **MiniBatchKMeans**（已有）：快速、硬聚类、需指定k
- **DBSCAN**（新增）：异常检测、无需指定k、基于密度
- **GMM**（新增）：软聚类、概率分布、不确定性量化

### 2026-02-16 - 区域级聚类分析功能

**新增功能：** 实现区域级聚类分析系统

**新增模块：**
- `src/clustering/feature_builder.py` - 区域特征构建器（语义+形态学+多样性特征）
- `src/clustering/clustering_engine.py` - KMeans聚类引擎
- `src/clustering/cluster_profiler.py` - 聚类画像生成器
- `src/pipelines/clustering_pipeline.py` - 聚类分析管道

**新增表：**
- `region_vectors` - 区域特征向量
- `cluster_assignments` - 聚类分配
- `cluster_profiles` - 聚类画像
- `clustering_metrics` - 聚类评估指标

**新增脚本：**
- `scripts/run_clustering_analysis.py` - 运行聚类分析

**支持粒度：** 市级、县级、鎮级聚类

**性能：** 121个县区，230维特征，运行时间约3-5秒，最佳k=4（轮廓系数0.62）

## 村级聚类分析 (Village-Level Clustering)

### 概述 (Overview)

村级聚类直接对284,764个自然村进行聚类分析，提供三种互补的聚类方法：

1. **MiniBatchKMeans**：快速聚类，适合大规模数据
2. **DBSCAN**：基于密度的聚类，自动识别异常村名（噪声点）
3. **GMM**：软聚类，提供概率分布和不确定性量化

### 运行村级聚类 (Running Village-Level Clustering)

#### 1. MiniBatchKMeans聚类

```bash
# 运行MiniBatchKMeans聚类（k=50）
python scripts/run_village_clustering.py \
    --db-path data/villages.db \
    --output-dir results/village_clustering \
    --k 50 \
    --batch-size 10000 \
    --pca-components 50

# 结果保存在 results/village_clustering/
# - village_clusters.csv: 聚类分配结果
# - cluster_statistics.csv: 聚类统计信息
```

#### 2. DBSCAN聚类（异常检测）

```bash
# 运行DBSCAN聚类
python scripts/run_dbscan_clustering.py \
    --db-path data/villages.db \
    --output-dir results/dbscan_clustering \
    --eps 0.5 \
    --min-samples 10 \
    --pca-components 50

# 结果保存在 results/dbscan_clustering/
# - village_clusters_dbscan.csv: 聚类分配结果
# - noise_points.csv: 异常村名（噪声点）
# - cluster_statistics.csv: 聚类统计信息
```

**DBSCAN优势：**
- 自动识别异常村名（label=-1）
- 无需预先指定聚类数量
- 发现任意形状的聚类
- 基于密度的聚类，更符合地理分布特征

#### 3. GMM聚类（软聚类）

```bash
# 运行GMM聚类
python scripts/run_gmm_clustering.py \
    --db-path data/villages.db \
    --output-dir results/gmm_clustering \
    --n-components 50 \
    --covariance-type full \
    --pca-components 50

# 结果保存在 results/gmm_clustering/
# - village_clusters_gmm.csv: 聚类分配结果（含概率分布）
# - uncertain_villages.csv: 命名模式模糊的村庄
# - cluster_statistics.csv: 聚类统计信息
```

**GMM优势：**
- 软聚类：提供每个村庄属于各聚类的概率
- 不确定性量化：识别命名模式模糊的村庄
- 灵活的聚类形状：可以建模椭圆形聚类
- 概率基础：有明确的统计假设

#### 4. 聚类可视化

```bash
# 使用UMAP可视化聚类结果
python scripts/visualize_clusters.py \
    --db-path data/villages.db \
    --cluster-file results/village_clustering/village_clusters.csv \
    --output-dir results/visualization \
    --method umap

# 或使用PCA可视化
python scripts/visualize_clusters.py \
    --db-path data/villages.db \
    --cluster-file results/dbscan_clustering/village_clusters_dbscan.csv \
    --output-dir results/visualization_dbscan \
    --method pca

# 结果保存在 results/visualization/
# - villages_2d.csv: 2D坐标数据
# - cluster_visualization.png: 聚类散点图
```

### 村级聚类特征 (Village-Level Features)

村级聚类使用以下特征：

1. **基础特征**：
   - `name_length`：村名长度

2. **后缀特征**（独热编码）：
   - `suffix_1`：末尾1个字符（例如：村、坑、围）
   - `suffix_2`：末尾2个字符（例如：新村、老围）
   - 保留前50个最常见后缀

3. **语义特征**（二元指标）：
   - `sem_mountain`：山地相关（山、岭、坑、岗、峰、坳）
   - `sem_water`：水系相关（水、河、江、湖、塘、涌、沙、洲）
   - `sem_direction`：方位相关（东、西、南、北、中、上、下、前、后）
   - `sem_settlement`：聚落相关（村、庄、寨、围、堡、屯）
   - `sem_clan`：姓氏相关（陈、李、王、张、刘、黄、林、吴、周、郑）

**特征矩阵维度**：约106维（1个基础特征 + 5个语义特征 + 100个后缀特征）

**预处理**：
- StandardScaler标准化
- PCA降维至50维（可选）

### 预期发现 (Expected Insights)

村级聚类揭示：

**MiniBatchKMeans发现：**
- Cluster 17（8.8%）："村"后缀村庄
- Cluster 41（4.7%）："坑"后缀村庄（山地地形）
- Cluster 12（2.2%）："围"后缀村庄（珠三角水乡）
- Cluster 5（3.5%）：水系相关村庄（涌、塘、沙）

**DBSCAN发现：**
- 核心聚类：常见命名模式（村、坑、围等）
- 边界点：过渡性命名模式
- 噪声点：独特/罕见村名（潜在文化意义）

**GMM发现：**
- 高概率村庄：典型命名模式
- 低概率村庄：混合命名模式（例如：同时包含山地和水系特征）
- 高熵村庄：命名模式模糊，可能位于文化/语言边界

### 性能特征 (Performance)

- **数据规模**：284,764个自然村
- **运行时间**：
  - MiniBatchKMeans：约2分钟
  - DBSCAN：约3-5分钟
  - GMM：约5-8分钟
  - UMAP可视化：约10-15分钟
- **内存占用**：< 2GB（符合部署约束）
- **特征维度**：106维 → PCA降至50维

## 特徵物化管道 (Feature Materialization Pipeline)

### 概述 (Overview)

特徵物化管道將村莊級別的語義和形態學特徵預計算並存儲到數據庫中，實現"離線重、在線輕"的部署策略。

### 運行管道 (Running Pipeline)

```bash
# 運行特徵物化管道
python scripts/run_feature_materialization.py \
    --run-id feature_001 \
    --output-dir results/feature_001

# 可選：關聯聚類結果
python scripts/run_feature_materialization.py \
    --run-id feature_001 \
    --clustering-run-id village_cluster_001 \
    --output-dir results/feature_001
```

### 物化特徵 (Materialized Features)

**村莊級別特徵**（village_features表）：
- 基礎信息：city, county, town, village_name, pinyin
- 形態學特徵：suffix_1/2/3, prefix_1/2/3, name_length
- 語義標籤（9個二元特徵）：
  - sem_mountain：山地相關
  - sem_water：水系相關
  - sem_settlement：聚落相關
  - sem_direction：方位相關
  - sem_clan：姓氏相關
  - sem_symbolic：象徵相關
  - sem_agriculture：農業相關
  - sem_vegetation：植被相關
  - sem_infrastructure：基礎設施相關
- 聚類分配：kmeans_cluster_id, dbscan_cluster_id, gmm_cluster_id

**區域聚合統計**（city/county/town_aggregates表）：
- 村莊總數和平均名稱長度
- 語義標籤計數和百分比
- Top N後綴和前綴
- 聚類分佈

### 查詢特徵 (Querying Features)

```python
import sqlite3
from src.data.db_query import (
    get_village_features,
    get_villages_by_semantic_tag,
    get_villages_by_suffix,
    get_villages_by_cluster,
    get_region_aggregates,
    get_semantic_tag_statistics
)

conn = sqlite3.connect('data/villages.db')

# 查詢特定區域的村莊特徵
df = get_village_features(conn, run_id='feature_001', city='广州市', limit=100)

# 查詢包含山地特徵的村莊
df = get_villages_by_semantic_tag(conn, run_id='feature_001', semantic_category='mountain', limit=100)

# 查詢以"村"結尾的村莊
df = get_villages_by_suffix(conn, run_id='feature_001', suffix='村', suffix_length=1, limit=100)

# 查詢特定聚類中的村莊
df = get_villages_by_cluster(conn, run_id='feature_001', cluster_id=17, algorithm='kmeans', limit=100)

# 查詢縣級聚合統計
df = get_region_aggregates(conn, run_id='feature_001', region_level='county')

# 查詢全局語義標籤統計
df = get_semantic_tag_statistics(conn, run_id='feature_001')

conn.close()
```

### 性能指標 (Performance Metrics)

- **數據規模**：284,764個自然村
- **運行時間**：約67秒（~1分鐘）
- **內存占用**：< 1GB
- **數據庫大小**：
  - village_features：284,764條記錄
  - city_aggregates：21條記錄
  - county_aggregates：121條記錄
  - town_aggregates：1,579條記錄

### 語義標籤統計 (Semantic Tag Statistics)

基於feature_001運行結果：

| 語義類別 | 村莊數量 | 百分比 |
|---------|---------|--------|
| settlement（聚落） | 87,919 | 30.76% |
| direction（方位） | 77,069 | 26.96% |
| mountain（山地） | 75,030 | 26.25% |
| water（水系） | 47,324 | 16.55% |
| clan（姓氏） | 29,599 | 10.35% |
| symbolic（象徵） | 24,886 | 8.71% |
| vegetation（植被） | 21,092 | 7.38% |
| agriculture（農業） | 20,356 | 7.12% |
| infrastructure（基建） | 6,748 | 2.36% |

## 在線服務策略 (Online Serving Policy)

### 概述 (Overview)

在線服務策略框架確保查詢在2核/2GB部署環境中安全執行，防止內存耗盡和性能問題。

### 核心功能 (Core Features)

1. **查詢驗證**：阻止全表掃描和昂貴操作
2. **行數限制**：強制執行最大行數限制
3. **分頁支持**：提供高效的分頁查詢
4. **配置管理**：支持生產/開發環境配置

### 配置模式 (Configuration Modes)

**生產模式（Production）**：
- 最大行數：500（默認）/ 5,000（絕對上限）
- 全表掃描：禁用
- 運行時聚類：禁用
- 查詢超時：3秒
- 內存限制：300MB

**開發模式（Development）**：
- 最大行數：10,000（默認）/ 50,000（絕對上限）
- 全表掃描：允許
- 運行時聚類：禁用
- 查詢超時：10秒
- 內存限制：1GB

**默認模式（Default）**：
- 最大行數：1,000（默認）/ 10,000（絕對上限）
- 全表掃描：禁用
- 運行時聚類：禁用
- 查詢超時：5秒
- 內存限制：500MB

### 使用方法 (Usage)

#### 命令行查詢（CLI）

```bash
# 使用默認配置
python scripts/query_results.py --run-id feature_001 --type global --top 20

# 使用生產配置（嚴格限制）
python scripts/query_results.py --run-id feature_001 --type global --top 20 --config production

# 使用開發配置（寬鬆限制）
python scripts/query_results.py --run-id feature_001 --type global --top 20 --config development

# 自定義最大行數
python scripts/query_results.py --run-id feature_001 --type global --top 20 --max-rows 500

# 允許全表掃描（不推薦用於生產環境）
python scripts/query_results.py --run-id feature_001 --type global --top 20 --enable-full-scan
```

#### Python API

```python
import sqlite3
from src.deployment import QueryPolicy, DeploymentConfig, SafeQueryExecutor, PolicyViolationError
from src.data.db_query import get_village_features

conn = sqlite3.connect('data/villages.db')

# 使用生產配置
config = DeploymentConfig.production()
policy = QueryPolicy(
    max_rows=config.max_rows_default,
    max_rows_absolute=config.max_rows_absolute,
    enable_full_scan=config.enable_full_scan
)
executor = SafeQueryExecutor(conn, policy)

# 執行安全查詢
try:
    result = executor.execute(
        get_village_features,
        run_id='feature_001',
        city='广州市',
        limit=100
    )
    print(f"查詢成功，返回 {len(result)} 行")
except PolicyViolationError as e:
    print(f"查詢被阻止：{e}")

# 使用分頁查詢
results, total, has_next = executor.execute_with_pagination(
    get_village_features,
    run_id='feature_001',
    city='广州市',
    page=1,
    page_size=50
)
print(f"第1頁：{len(results)} 行，總計 {total} 行，有下一頁：{has_next}")

conn.close()
```

### 策略規則 (Policy Rules)

**阻止的操作**：
- 無過濾條件的全表掃描（除非明確啟用）
- 超過絕對上限的行數請求（10倍於絕對上限）
- 運行時聚類操作（必須使用預計算的cluster_id）

**允許的過濾條件**：
- city（城市）
- county（縣區）
- town（鄉鎮）
- cluster_id（聚類ID）
- semantic_category（語義類別）
- suffix（後綴）
- algorithm（算法）

**注意**：run_id不被視為有效過濾條件，因為它不能限制結果集大小。

### 測試驗證 (Testing)

```bash
# 運行策略測試
python scripts/test_query_policy.py

# 預期輸出：
# [Test 1] 配置加載 - [OK]
# [Test 2] 帶過濾條件的查詢 - [OK]
# [Test 3] 無過濾條件的查詢 - [OK]（被阻止）
# [Test 4] 超過上限的查詢 - [OK]（自動限制）
# [Test 5] 分頁支持 - [OK]
# [Test 6] 允許全表掃描 - [OK]
```

### 配置文件 (Configuration Files)

配置文件位於 `config/` 目錄：

- `deployment.json`：默認配置
- `deployment.production.json`：生產環境配置
- `deployment.development.json`：開發環境配置

可以根據需要自定義配置文件。

## 更新日志 (Changelog)

### 2026-02-16
- **新增功能**：在線服務策略框架（Phase 11）
- **實現模塊**：
  - 查詢策略（query_policy.py）
  - 配置管理（config.py）
  - 安全查詢執行器（query_wrapper.py）
- **新增配置**：3個部署配置文件（default/production/development）
- **更新模塊**：為db_query.py添加offset參數支持
- **CLI集成**：為query_results.py添加策略標誌
- **測試腳本**：test_query_policy.py
- **新增功能**：特徵物化管道（Phase 10）
- **實現模塊**：
  - 特徵提取器（feature_extractor.py）
  - 物化管道（feature_materialization_pipeline.py）
  - 區域聚合（region_aggregation.py）
- **新增表**：village_features, city_aggregates, county_aggregates, town_aggregates
- **新增腳本**：run_feature_materialization.py
- **新增查詢函數**：6個村莊特徵查詢函數
- **性能**：67秒處理284K村莊，內存占用<1GB

### 2026-02-15
- 實現村級聚類分析（MiniBatchKMeans, DBSCAN, GMM）
- 實現層次聚類分析
- 實現UMAP可視化
- 添加聚類分析腳本

### 2026-02-14
- 實現語義分析管道（semantic_001）
- 實現形態學模式分析管道（morph_001）
- 添加9個語義類別的虛擬詞頻（VTF）分析

### 2026-02-13
- 實現字符頻率分析管道（run_002）
- 實現區域傾向性分析
- 添加數據庫持久化功能

## License

TBD

</details>



