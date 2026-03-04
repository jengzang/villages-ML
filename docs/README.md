# Documentation Index

广东省自然村分析系统 - 文档索引

本目录包含项目的所有文档，按类别组织。

---

## 📁 Directory Structure

```
docs/
├── README.md                          # 本文件 - 文档索引
├── RUN_ALL_PHASES_GUIDE.md          # ⭐ 执行指南（新）
├── FEATURE_OVERVIEW.md               # 功能概览
├── LEXICON_VERSIONS.md               # 词典版本
├── DATABASE_OPTIMIZATION_2026-03-02.md  # 数据库优化记录
│
├── frontend/                          # 前端/API文档（3个）
│   ├── API_REFERENCE.md              # 完整API参考
│   ├── API_QUICK_REFERENCE.md        # 快速参考
│   └── FRONTEND_INTEGRATION_GUIDE.md # 前端集成指南
│
├── guides/                            # 实现指南（8个）
│   ├── CHAR_EMBEDDINGS_GUIDE.md
│   ├── SPATIAL_ANALYSIS_GUIDE.md
│   ├── LLM_LABELING_GUIDE.md
│   ├── DATABASE_MIGRATION_FOR_BACKEND.md
│   ├── TENDENCY_SIGNIFICANCE_GUIDE.md
│   ├── ZSCORE_NORMALIZATION_GUIDE.md
│   ├── RUN_ID_MANAGEMENT_QUICK_GUIDE.md
│   └── DATABASE_MAINTENANCE_SCRIPTS.md
│
├── phases/                            # Phase实现文档（10个）
│   ├── PHASE_0_PREPROCESSING_SUMMARY.md
│   ├── PHASE_01_IMPLEMENTATION_SUMMARY.md
│   ├── PHASE_02_IMPLEMENTATION_SUMMARY.md
│   ├── PHASE_03_IMPLEMENTATION_SUMMARY.md
│   ├── PHASE_11_SUMMARY.md
│   ├── PHASE_12_SUMMARY.md
│   ├── PHASE_13_SUMMARY.md
│   ├── PHASE_14_SUMMARY.md
│   ├── PHASE_15_16_IMPLEMENTATION_SUMMARY.md
│   └── PHASE_17_IMPLEMENTATION_SUMMARY.md
│
└── reports/                           # 分析报告（5个）
    ├── PROJECT_STATUS.md
    ├── COMPREHENSIVE_ANALYSIS_REPORT.md
    ├── DATABASE_STATUS_REPORT.md
    ├── ANALYSIS_RESULTS_SHOWCASE.md
    └── 分析结果展示_中文版.md
```

**文档总数**: 31个（精简后，原73个）

---

## 🚀 Quick Start

**新用户？从这里开始：**

1. **项目概览**: `../README.md` (根目录)
2. **项目指南**: `../CLAUDE.md` (开发指南)
3. **执行指南**: `RUN_ALL_PHASES_GUIDE.md` ⭐ **推荐**
4. **API快速参考**: `frontend/API_QUICK_REFERENCE.md`
5. **项目状态**: `reports/PROJECT_STATUS.md`

---

## 📚 Documentation by Category

### 1. 执行与配置

**如何运行分析流水线？**

- **`RUN_ALL_PHASES_GUIDE.md`** ⭐ - 完整执行指南
  - 所有17个phase的详细说明
  - 命令行参数详解
  - 使用场景示例
  - 常见问题解答

- **`FEATURE_OVERVIEW.md`** - 功能概览
- **`LEXICON_VERSIONS.md`** - 语义词典版本管理
- **`DATABASE_OPTIMIZATION_2026-03-02.md`** - 数据库优化记录

---

### 2. Frontend & API Documentation

**如何使用API？**

📂 `frontend/` (3个文档)

- **`API_REFERENCE.md`** - 完整API参考
  - 94个端点详细说明
  - 请求/响应示例
  - 错误处理

- **`API_QUICK_REFERENCE.md`** - 快速参考（一页）
  - 常用端点速查
  - 快速上手

- **`FRONTEND_INTEGRATION_GUIDE.md`** - 前端集成指南
  - Vue 3集成示例
  - 最佳实践

**适用场景**: 构建前端应用、API集成

---

### 3. Implementation Guides

**如何实现特定功能？**

📂 `guides/` (8个文档)

#### 核心分析指南

- **`CHAR_EMBEDDINGS_GUIDE.md`** - 字符嵌入
  - Word2Vec训练
  - 相似度计算

- **`SPATIAL_ANALYSIS_GUIDE.md`** - 空间分析
  - k-NN、DBSCAN、KDE
  - 热点检测

- **`LLM_LABELING_GUIDE.md`** - LLM语义标注
  - API配置
  - 标注流程

#### 统计分析指南

- **`TENDENCY_SIGNIFICANCE_GUIDE.md`** - 倾向性与显著性
  - Lift计算
  - 卡方检验

- **`ZSCORE_NORMALIZATION_GUIDE.md`** - Z分数标准化
  - 标准化方法
  - 应用场景

#### 数据库与管理

- **`DATABASE_MIGRATION_FOR_BACKEND.md`** ⭐ - 数据库迁移
  - Schema变更
  - 后端适配

- **`DATABASE_MAINTENANCE_SCRIPTS.md`** - 数据库维护
  - 维护脚本
  - 最佳实践

- **`RUN_ID_MANAGEMENT_QUICK_GUIDE.md`** - Run ID管理
  - 版本控制
  - 查询策略

**适用场景**: 实现或修改分析功能

---

### 4. Phase Implementation Summaries

**每个Phase做了什么？**

📂 `phases/` (10个文档)

#### 核心Phases (0-3)

- **`PHASE_0_PREPROCESSING_SUMMARY.md`** - 数据预处理
  - 前缀清理（5,782个）
  - 文本标准化

- **`PHASE_01_IMPLEMENTATION_SUMMARY.md`** - 字符嵌入
  - Word2Vec训练（9,209字符）
  - 相似度预计算

- **`PHASE_02_IMPLEMENTATION_SUMMARY.md`** - 频率分析
  - 字符频率统计
  - 区域倾向性

- **`PHASE_03_IMPLEMENTATION_SUMMARY.md`** - 语义分析
  - LLM标注（9类）
  - 共现网络（15,432边）

#### 高级Phases (11-17)

- **`PHASE_11_SUMMARY.md`** - 查询策略框架
- **`PHASE_12_SUMMARY.md`** - N-gram分析（1,909,959模式）
- **`PHASE_13_SUMMARY.md`** - 空间热点（8个热点）
- **`PHASE_14_SUMMARY.md`** - 语义组合（8种模式）
- **`PHASE_15_16_IMPLEMENTATION_SUMMARY.md`** - 区域相似度 + 语义中心性
- **`PHASE_17_IMPLEMENTATION_SUMMARY.md`** - 混合分析

**适用场景**: 理解分析流程、复现实验

---

### 5. Analysis & Status Reports

**项目进展如何？分析结果是什么？**

📂 `reports/` (5个文档)

#### 项目状态

- **`PROJECT_STATUS.md`** ⭐ - 项目总体状态
  - 完成度：95%
  - 代码规模：51,782行
  - 数据库：70张表，2.5GB

- **`DATABASE_STATUS_REPORT.md`** - 数据库状态
  - 表结构验证
  - 数据质量报告

#### 分析结果

- **`COMPREHENSIVE_ANALYSIS_REPORT.md`** ⭐ - 综合分析报告（中文）
  - 8000字完整报告
  - 15个phase结果
  - 深度洞察

- **`ANALYSIS_RESULTS_SHOWCASE.md`** - 结果展示（英文）
  - 可视化结果
  - 关键发现

- **`分析结果展示_中文版.md`** - 结果展示（中文）
  - 中文版本
  - 详细解读

**适用场景**: 了解项目进展、查看分析结果

---

## 🔍 Documentation by Task

### 任务1: 我想运行分析

1. 阅读 `RUN_ALL_PHASES_GUIDE.md`
2. 检查 `reports/PROJECT_STATUS.md` 了解当前状态
3. 运行 `python run_all_phases.py --list`

### 任务2: 我想使用API

1. 快速上手: `frontend/API_QUICK_REFERENCE.md`
2. 完整参考: `frontend/API_REFERENCE.md`
3. 前端集成: `frontend/FRONTEND_INTEGRATION_GUIDE.md`

### 任务3: 我想理解某个Phase

1. 查看 `phases/PHASE_XX_SUMMARY.md`
2. 如需实现细节，查看对应的 `guides/` 文档

### 任务4: 我想修改数据库

1. 阅读 `guides/DATABASE_MIGRATION_FOR_BACKEND.md`
2. 参考 `guides/DATABASE_MAINTENANCE_SCRIPTS.md`
3. 检查 `DATABASE_OPTIMIZATION_2026-03-02.md`

### 任务5: 我想查看分析结果

1. 中文版: `reports/COMPREHENSIVE_ANALYSIS_REPORT.md`
2. 英文版: `reports/ANALYSIS_RESULTS_SHOWCASE.md`
3. 项目状态: `reports/PROJECT_STATUS.md`

---

## 📊 Documentation Statistics

- **总文档数**: 31个
- **总行数**: ~12,000行
- **语言**: 中英文双语
- **最后更新**: 2026-03-04

### 文档分布

| 类别 | 文档数 | 说明 |
|------|--------|------|
| 根目录 | 5 | 执行指南、功能概览 |
| frontend/ | 3 | API文档 |
| guides/ | 8 | 实现指南 |
| phases/ | 10 | Phase文档 |
| reports/ | 5 | 分析报告 |

---

## 🔄 Recent Updates

### 2026-03-04
- ✅ 新增 `RUN_ALL_PHASES_GUIDE.md` - 完整执行指南
- ✅ 精简文档：73个 → 31个（减少58%）
- ✅ 删除重复/过时文档
- ✅ 更新文档索引

### 2026-03-02
- 数据库优化：5.45GB → 2.3GB
- 新增优化记录文档

### 2026-02-25
- Phase 17完成
- 语义子类别分析

---

## 💡 Tips

1. **新用户**: 从 `RUN_ALL_PHASES_GUIDE.md` 开始
2. **开发者**: 查看 `guides/` 目录
3. **研究者**: 阅读 `reports/COMPREHENSIVE_ANALYSIS_REPORT.md`
4. **API用户**: 使用 `frontend/API_QUICK_REFERENCE.md`

---

## 📞 Need Help?

- **项目指南**: `../CLAUDE.md`
- **项目README**: `../README.md`
- **执行指南**: `RUN_ALL_PHASES_GUIDE.md`
- **项目状态**: `reports/PROJECT_STATUS.md`

---

**Last Updated**: 2026-03-04
**Documentation Version**: 2.0 (Simplified)
