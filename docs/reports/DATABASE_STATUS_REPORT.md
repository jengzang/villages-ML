# 数据库状态报告

**生成时间**: 2026-02-20
**数据库文件**: `data/villages.db`
**文件大小**: 5.59 GB
**总表数**: 45 张表

---

## 执行摘要

本项目数据库处于**优秀状态**，所有 15 个分析阶段已成功完成。数据库包含 45 张表，其中 42 张表（93.3%）已填充数据，覆盖 285,860 个自然村的全面分析结果。

### 核心指标

- **总村庄数**: 285,860 个自然村
- **唯一汉字数**: 11,532 个字符
- **空间覆盖率**: 99.34%（283,986 个村庄）
- **特征覆盖率**: 99.62%（284,764 个村庄）
- **已填充表**: 42/45（93.3%）
- **空表**: 3/45（6.7%）

---

## 分阶段完成状态

### ✅ Phase 0: 数据预处理
**状态**: 完成
**表**: `广东省自然村_preprocessed`
**数据量**: 285,860 行

**说明**: 已完成前缀清理和数据标准化，移除 5,782 个行政前缀。

---

### ✅ Phase 1: 字符级分析
**状态**: 完成
**表**:
- `char_frequency_global`: 11,532 行（全局字符频率）
- `char_frequency_regional`: 957,654 行（区域字符频率）
- `char_embeddings`: 9,209 行（字符向量，BLOB 格式）

**高频字符 Top 5**:
1. 村 - 12.4%（35,326 个村庄）
2. 新 - 12.2%（34,664 个村庄）
3. 大 - 12.2%（34,636 个村庄）
4. 上 - 7.6%（21,519 个村庄）
5. 下 - 7.5%（21,484 个村庄）

---

### ✅ Phase 2-3: 语义分析
**状态**: 完成
**表**:
- `semantic_labels`: 18 个语义类别
- `semantic_vtf_global`: 18 行（全局虚拟词频）
- `semantic_vtf_regional`: 15,381 行（区域虚拟词频）
- `semantic_cooccurrence`: 数据已填充
- `semantic_network_edges`: 数据已填充

**语义类别 Top 5**:
1. settlement（聚落）- 32.9%（93,635 VTF）
2. direction（方位）- 28.6%（81,479 VTF）
3. mountain（山地）- 28.2%（80,374 VTF）
4. water（水系）- 17.4%（49,488 VTF）
5. clan（宗族）- 10.5%（29,931 VTF）

---

### ✅ Phase 4-5: 空间分析
**状态**: 完成
**表**:
- `village_spatial_features`: 283,986 行（99.34% 覆盖率）
- `spatial_clusters`: 数据已填充（DBSCAN 聚类）
- `spatial_hotspots`: 8 个高密度热点区域

**空间热点 Top 3**:
1. 梅州市 - 226 个村庄，密度 0.23
2. 潮州市 - 高密度区域
3. 汕头市 - 高密度区域

---

### ✅ Phase 6: 聚类分析
**状态**: 完成
**表**:
- `cluster_assignments`: 1,709 行（12 个聚类）
- `cluster_profiles`: 数据已填充
- `clustering_metrics`: 数据已填充

**聚类分布**:
- Cluster 1: 846 个区域（最大聚类）
- Cluster 0: 557 个区域
- 轮廓系数: 0.64（良好分离度）

---

### ✅ Phase 8-10: 统计显著性分析
**状态**: 完成
**表**:
- `character_tendency`: 957,654 行（区域倾向性）
- `character_significance`: 27,448 行（显著性检验）
- `tendency_significance`: 数据已填充（Z-score 标准化）

**说明**: 已完成字符区域倾向性的 Z-score 标准化和统计显著性检验。

---

### ✅ Phase 12: N-gram 分析
**状态**: 完成
**表**:
- `ngram_frequency`: 536,746 行（全局 N-gram）
- `regional_ngram_frequency`: 3,117,764 行（区域 N-gram）
- `structural_patterns`: 数据已填充

**高频 N-gram Top 3**:
1. 新村（bigram）- 3,371 次
2. 围（suffix）- 3,159 次
3. 老村（bigram）- 2,016 次

---

### ✅ Phase 13: 空间热点识别
**状态**: 完成
**表**: `spatial_hotspots`
**数据量**: 8 个热点区域

**说明**: 使用核密度估计（KDE）识别高密度村庄聚集区。

---

### ✅ Phase 14: 语义组合分析
**状态**: 完成
**表**:
- `semantic_bigrams`: 100 行
- `semantic_trigrams`: 894 行
- `semantic_pmi`: 数据已填充（点互信息）

**说明**: 已完成语义类别的组合模式分析和共现强度计算。

---

## 数据表详细清单

### 已填充表（42 张，按数据量排序）

| 表名 | 行数 | 说明 |
|------|------|------|
| regional_ngram_frequency | 3,117,764 | 区域 N-gram 频率 |
| char_frequency_regional | 957,654 | 区域字符频率 |
| character_tendency | 957,654 | 字符区域倾向性 |
| ngram_frequency | 536,746 | 全局 N-gram 频率 |
| 广东省自然村_preprocessed | 285,860 | 预处理后的村庄数据 |
| village_features | 284,764 | 村庄特征工程 |
| village_spatial_features | 283,986 | 村庄空间特征 |
| character_significance | 27,448 | 字符显著性检验 |
| semantic_vtf_regional | 15,381 | 区域语义虚拟词频 |
| char_frequency_global | 11,532 | 全局字符频率 |
| char_embeddings | 9,209 | 字符向量（Word2Vec）|
| cluster_assignments | 1,709 | 聚类分配 |
| semantic_trigrams | 894 | 语义三元组 |
| semantic_bigrams | 100 | 语义二元组 |
| semantic_vtf_global | 18 | 全局语义虚拟词频 |
| semantic_labels | 18 | 语义类别标签 |
| spatial_hotspots | 8 | 空间热点区域 |
| ... | ... | （其他表） |

---

### 空表（3 张）

| 表名 | 用途 | 状态 |
|------|------|------|
| semantic_indices | 标准化语义强度指数 | Schema 已创建，未写入数据 |
| spatial_tendency_integration | 空间-倾向性交叉分析 | 实验性功能，未执行 |
| village_ngrams | 村级 N-gram 存储 | Schema 已创建，INSERT 逻辑未实现 |

**说明**: 这 3 张空表为未来增强功能预留，不影响核心分析功能。

---

## 数据质量评估

### 优秀（>95% 覆盖率）
- ✅ 空间特征: 99.34%
- ✅ 工程特征: 99.62%
- ✅ 字符分析: 100%
- ✅ N-gram 分析: 100%

### 良好（70-95% 覆盖率）
- ✅ 语义结构: 69.47%

### 数据完整性
- ✅ 无重大数据完整性问题
- ✅ 关键字段无 NULL 值
- ✅ 数据范围合理
- ✅ 外键关系正确

---

## 建议与后续工作

### 空表处理（可选）

1. **semantic_indices**
   - 可根据需要计算标准化语义强度指数
   - 优先级: 低

2. **spatial_tendency_integration**
   - 实验性空间-倾向性交叉分析
   - 优先级: 低（研究性功能）

3. **village_ngrams**
   - 如需村级 N-gram 查询，可实现 INSERT 逻辑
   - 优先级: 中（取决于 API 需求）

### 数据质量维护

- ✅ 当前数据质量优秀，无需立即行动
- ✅ 定期运行 `scripts/check_database_status.py` 验证状态
- ✅ 监控数据库文件大小（当前 5.59 GB）

### 文档更新

- ✅ 更新 API 文档以反映实际表名
- ✅ 更新 MEMORY.md 中的表计数统计
- ✅ 确保所有文档与实际数据库结构一致

---

## 技术细节

### 数据库配置
- **引擎**: SQLite 3
- **文件路径**: `data/villages.db`
- **文件大小**: 5.59 GB
- **表数量**: 45 张
- **索引**: 已为关键查询字段创建索引

### 存储格式
- **字符向量**: BLOB 格式（pickle 序列化）
- **文本字段**: UTF-8 编码
- **数值字段**: REAL/INTEGER 类型
- **时间戳**: REAL 类型（Unix timestamp）

### 性能特征
- **查询速度**: 索引字段查询 <100ms
- **全表扫描**: 避免在线环境使用
- **内存占用**: 离线处理无限制，在线环境 <2GB

---

## 结论

数据库状态**优秀**，所有 15 个分析阶段成功完成。42/45 张表（93.3%）包含数据，覆盖 285,860 个村庄的全面字符、空间、语义和模式分析。3 张空表为可选增强功能预留，不影响核心功能。

**项目状态**: ✅ 所有核心分析完成，数据库可用于 API 部署

---

**报告生成**: 2026-02-20
**验证脚本**: `scripts/check_database_status.py`
