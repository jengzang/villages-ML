# run_all_phases.py 使用指南

## 概述

`run_all_phases.py` 是广东省自然村分析系统的完整流水线执行器，可以自动化运行全部17个分析阶段。

## 快速开始

```bash
# 1. 列出所有可用阶段
python run_all_phases.py --list

# 2. 预览执行计划（不实际运行）
python run_all_phases.py --all --dry-run

# 3. 运行所有阶段
python run_all_phases.py --all

# 4. 运行特定阶段
python run_all_phases.py --phases 0,1,2,3

# 5. 运行阶段组
python run_all_phases.py --group core
```

---

## 命令行参数详解

### 执行模式 (Execution Mode)

#### `--all`
运行所有17个阶段（Phase 0-17）

```bash
python run_all_phases.py --all
```

**注意**: 完整运行需要1-2小时

#### `--phases PHASE_IDS`
运行指定的阶段，支持多种格式：

```bash
# 单个阶段
python run_all_phases.py --phases 0

# 多个阶段（逗号分隔）
python run_all_phases.py --phases 0,1,2,3

# 范围表示法
python run_all_phases.py --phases 0-5

# 混合表示法
python run_all_phases.py --phases 0-5,12,14-17
```

#### `--group GROUP_NAME`
运行指定分组的所有阶段

```bash
# 核心阶段 (Phase 0-7)
python run_all_phases.py --group core

# 高级阶段 (Phase 10-15)
python run_all_phases.py --group advanced
```

---

### 配置选项 (Configuration)

#### `--db-path PATH`
指定数据库文件路径（默认: `data/villages.db`）

```bash
python run_all_phases.py --all --db-path data/raw/villages.db
```

#### `--run-id-prefix PREFIX`
指定运行ID前缀（默认: `run`）

```bash
python run_all_phases.py --all --run-id-prefix production
# 生成的run_id格式: production_01_20260304_153045
```

---

### 行为选项 (Behavior)

#### `--dry-run`
预览执行计划，不实际运行

```bash
python run_all_phases.py --all --dry-run
```

**用途**:
- 检查哪些阶段会被执行
- 查看执行顺序
- 估算执行时间
- 验证依赖关系

#### `--continue-on-error`
某个阶段失败后继续执行后续阶段

```bash
python run_all_phases.py --all --continue-on-error
```

**默认行为**: 遇到失败立即停止
**使用场景**:
- 调试特定阶段
- 部分阶段可选时
- 重新运行失败的阶段

#### `--skip-dependencies`
跳过依赖检查（高级用户）

```bash
python run_all_phases.py --phases 5,6,7 --skip-dependencies
```

**警告**: 可能导致阶段失败，仅在确认依赖已满足时使用

---

### 信息查询 (Information)

#### `--list`
列出所有可用阶段

```bash
python run_all_phases.py --list
```

**输出示例**:
```
Core Phases (核心阶段 0-7):
  Phase  0: Data Preprocessing (数据预处理) ⚠️ CRITICAL
            Clean village names, remove administrative prefixes
            Time: 2-5 min

  Phase  1: Character Embeddings (字符嵌入) ⚠️ CRITICAL
            Train Word2Vec embeddings (Skip-gram, 100-dim)
            Time: 5-10 min
  ...
```

#### `--info PHASE_ID`
显示指定阶段的详细信息

```bash
python run_all_phases.py --info 12
```

**输出示例**:
```
================================================================================
Phase 12: N-gram Analysis (N-gram分析)
================================================================================

📝 Description:
   EN: Extract bigrams, trigrams, 4-grams (1,909,959 patterns)
   ZH: 提取bigram、trigram、4-gram（1,909,959个模式）

📂 Script: scripts/core/phase12_ngram_analysis.py
🏷️  Group: advanced
⏱️  Estimated Time: 5-10 min
🔑 Critical: No
🔗 Dependencies: Phase 0

📊 Output Tables:
   - ngram_frequency
   - structural_patterns

⚙️  Arguments:
   --db-path data/villages.db
```

#### `--show-groups`
显示阶段分组信息

```bash
python run_all_phases.py --show-groups
```

---

## 阶段分组详解

### Core Phases (核心阶段 0-7)

**必需阶段**，构成基础分析流程：

| Phase | 名称 | 时间 | 说明 |
|-------|------|------|------|
| 0 | Data Preprocessing | 2-5 min | ⚠️ **必须首先运行** |
| 1 | Character Embeddings | 5-10 min | Word2Vec训练 |
| 2 | Frequency Analysis | 3-5 min | 字符频率统计 |
| 3 | Semantic Analysis | 3-5 min | 语义标注和共现 |
| 4 | Spatial Analysis | 5-10 min | 空间分布分析 |
| 5 | Feature Engineering | 3-5 min | 特征提取 |
| 6 | Clustering Analysis | 3-5 min | 聚类分析 |
| 7 | Feature Materialization | 2-3 min | 特征物化 |

**总时间**: 26-48分钟

### Advanced Phases (高级阶段 10-15)

**高级分析**，可选但提供深度洞察：

| Phase | 名称 | 时间 | 说明 |
|-------|------|------|------|
| 10 | Significance Testing | 2-3 min | 显著性检验 |
| 11 | Query Policy Framework | 1-2 min | 查询策略框架 |
| 12 | N-gram Analysis | 5-10 min | N-gram模式分析 |
| 13 | Spatial Hotspots | 2-3 min | 空间热点检测 |
| 14 | Semantic Composition | 3-5 min | 语义组合模式 |
| 15 | Region Similarity | 2-3 min | 区域相似度 |
| 17 | Hybrid Analysis | 3-5 min | 混合分析 |

**总时间**: 18-31分钟

---

## 依赖关系图

```
Phase 0 (预处理) ← 必须首先运行
    ├─→ Phase 1 (嵌入)
    │       ├─→ Phase 14 (语义组合)
    │       ├─→ Phase 16 (语义中心性)
    │       └─→ Phase 17 (混合分析)
    │
    ├─→ Phase 2 (频率 + 倾向性 + 统计检验)
    │       └─→ Phase 10 (显著性)
    │
    ├─→ Phase 3 (语义)
    │       ├─→ Phase 14 (语义组合)
    │       ├─→ Phase 16 (语义中心性)
    │       └─→ Phase 17 (混合分析)
    │
    ├─→ Phase 4 (空间)
    │       ├─→ Phase 5 (特征工程)
    │       └─→ Phase 13 (空间热点)
    │
    ├─→ Phase 5 (特征工程)
    │       ├─→ Phase 6 (聚类)
    │       ├─→ Phase 7 (物化)
    │       └─→ Phase 15 (区域相似度)
    │
    └─→ Phase 11 (查询策略)
    └─→ Phase 12 (N-gram)
```

---

## 使用场景示例

### 场景1: 首次完整运行

```bash
# 1. 确保使用原始数据库
cp data/raw/villages.db data/villages.db

# 2. 预览执行计划
python run_all_phases.py --all --dry-run

# 3. 运行所有阶段
python run_all_phases.py --all --run-id-prefix initial
```

### 场景2: 只运行核心分析

```bash
# 运行核心阶段 (0-7)
python run_all_phases.py --group core
```

### 场景3: 重新运行失败的阶段

```bash
# 假设Phase 12失败了，重新运行
python run_all_phases.py --phases 12 --run-id-prefix retry
```

### 场景4: 运行高级分析

```bash
# 前提: 核心阶段已完成
python run_all_phases.py --group advanced
```

### 场景5: 自定义阶段组合

```bash
# 运行预处理 + 嵌入 + 语义相关分析
python run_all_phases.py --phases 0,1,3,14,16,17
```

### 场景6: 调试模式

```bash
# 失败后继续，查看所有阶段的执行情况
python run_all_phases.py --all --continue-on-error --run-id-prefix debug
```

---

## 执行输出说明

### 阶段执行输出

```
================================================================================
Phase 12: N-gram Analysis (N-gram分析)
================================================================================
Description: Extract bigrams, trigrams, 4-grams (1,909,959 patterns)
描述: 提取bigram、trigram、4-gram（1,909,959个模式）
Group: advanced
Estimated time: 5-10 min
Script: scripts/core/phase12_ngram_analysis.py
Dependencies: Phase 0
Output tables: ngram_frequency, structural_patterns

Command: python scripts/core/phase12_ngram_analysis.py --run-id run_12_20260304_153045 --db-path data/villages.db

▶️  [START] Starting at 2026-03-04 15:30:45
... (阶段执行日志) ...
✅ [OK] Phase 12 completed successfully in 487.3s (8.1 min)
```

### 执行总结

```
================================================================================
Execution Summary (执行总结)
================================================================================

📊 Results:
   Total phases: 17
   ✅ Successful: 17
   ❌ Failed: 0

⏱️  Timing:
   Total time: 4523.7s (75.4 min)
   End time: 2026-03-04 16:46:08

📋 Phase Results:
--------------------------------------------------------------------------------
  ✅ OK   | Phase  0: Data Preprocessing
  ✅ OK   | Phase  1: Character Embeddings
  ✅ OK   | Phase  2: Frequency Analysis
  ...
  ✅ OK   | Phase 17: Hybrid Analysis
```

---

## 常见问题

### Q1: Phase 0 必须首先运行吗？

**A**: 是的！Phase 0 创建预处理表 `广东省自然村_预处理`，所有其他阶段都依赖这个表。

### Q2: 可以并行运行多个阶段吗？

**A**: 不可以。`run_all_phases.py` 按顺序执行阶段。但某些阶段（如Phase 2, 4, 12）互不依赖，可以手动在不同终端并行运行。

### Q3: 如何跳过某些阶段？

**A**: 使用 `--phases` 参数指定要运行的阶段：

```bash
# 跳过Phase 11-13，只运行0-10和14-17
python run_all_phases.py --phases 0-10,14-17
```

### Q4: 阶段失败后如何继续？

**A**: 使用 `--continue-on-error` 参数：

```bash
python run_all_phases.py --all --continue-on-error
```

### Q5: 如何查看某个阶段的详细信息？

**A**: 使用 `--info` 参数：

```bash
python run_all_phases.py --info 12
```

### Q6: 执行时间估算准确吗？

**A**: 估算基于285K村庄的全量数据集。实际时间取决于：
- CPU性能
- 内存大小
- 磁盘I/O速度
- 数据库大小

### Q7: 可以使用不同的数据库吗？

**A**: 可以，使用 `--db-path` 参数：

```bash
python run_all_phases.py --all --db-path data/test.db
```

### Q8: run_id 有什么用？

**A**: run_id 用于追踪每次运行的结果，格式为 `prefix_phaseID_timestamp`。某些表使用run_id区分不同版本的分析结果。

---

## 最佳实践

### 1. 首次运行

```bash
# 完整流程
python run_all_phases.py --list                    # 了解所有阶段
python run_all_phases.py --all --dry-run           # 预览执行计划
python run_all_phases.py --all --run-id-prefix v1  # 正式运行
```

### 2. 增量开发

```bash
# 开发新功能时，只运行相关阶段
python run_all_phases.py --phases 0,12 --run-id-prefix dev
```

### 3. 生产部署

```bash
# 使用明确的run-id前缀
python run_all_phases.py --all --run-id-prefix production_$(date +%Y%m%d)
```

### 4. 调试失败

```bash
# 1. 查看阶段详情
python run_all_phases.py --info 12

# 2. 单独运行失败的阶段
python run_all_phases.py --phases 12 --run-id-prefix debug

# 3. 如果依赖缺失，补充运行
python run_all_phases.py --phases 0,12
```

### 5. 性能优化

```bash
# 只运行必需的核心阶段
python run_all_phases.py --group core

# 高级分析可以后续按需运行
python run_all_phases.py --phases 12,14,15
```

---

## 技术细节

### run_id 生成规则

```
格式: {prefix}_{phase_id:02d}_{timestamp}
示例: run_12_20260304_153045

- prefix: 用户指定（默认"run"）
- phase_id: 两位数字（01-17）
- timestamp: YYYYmmdd_HHMMSS
```

### 依赖检查机制

脚本会自动检查依赖关系：

```python
# 示例: 运行Phase 14需要Phase 0, 1, 3
python run_all_phases.py --phases 14

# 输出:
⚠️  Warning: Missing dependencies detected!
  Phase 14 (Semantic Composition) requires: [0, 1, 3]

💡 Tip: Add missing phases or use --skip-dependencies to ignore
```

### 执行确认

运行超过3个阶段时会要求确认：

```
▶️  Proceed with execution? [Y/n]:
```

按 `Y` 或 `Enter` 继续，按 `n` 取消。

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目总体说明
- [PROJECT_STATUS.md](reports/PROJECT_STATUS.md) - 项目状态
- [PHASE_*_SUMMARY.md](phases/) - 各阶段详细文档
- [API_REFERENCE.md](frontend/API_REFERENCE.md) - API文档

---

## 更新日志

### 2026-03-04
- ✅ 添加全部17个阶段支持
- ✅ 添加阶段分组功能 (--group)
- ✅ 添加详细信息查询 (--info)
- ✅ 添加依赖检查
- ✅ 改进帮助信息 (-h)
- ✅ 添加中英文双语支持
- ✅ 添加执行确认机制
- ✅ 改进输出格式（emoji + 颜色）

### 之前版本
- 仅支持7个简化阶段 (Phase 0-6)
