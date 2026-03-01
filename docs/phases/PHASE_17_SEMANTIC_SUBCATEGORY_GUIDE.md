# Phase 17: 语义子类别细化实施指南

## 概述

**目标：** 将 9 大语义类别细化为 30+ 子类别，提供更精细的语义分析能力

**试点策略：** 先细化 mountain 和 water 两个类别（16 个子类别），验证价值后再扩展

**预期成果：**
- 16 个细分子类别（6 个 mountain + 10 个 water）
- 73 个字符重新标注
- 新的语义词典 v4_pilot.json
- 更新数据表和 API 端点
- 产出试点评估报告

---

## 细分类别体系

### Mountain（山地地形）→ 6 个子类别

| 子类别 | 英文名 | 语义描述 | 示例字符 |
|--------|--------|----------|----------|
| 山峰 | mountain_peak | 山体的顶部、高耸部分 | 山、峰、岭、顶、巅 |
| 山坡 | mountain_slope | 山体的倾斜面 | 坡、坳、坎、岗、冈 |
| 山谷 | mountain_valley | 山间的低洼地带 | 峡、峪、峒、坑、谷 |
| 山脊 | mountain_ridge | 山体的脊梁部分 | 脊、岐、嶂、峦 |
| 岩石 | mountain_rock | 山体的岩石构成 | 石、岩、崖、壁 |
| 平台 | mountain_plateau | 山间的平坦地带 | 台、坪、坝、塱 |

### Water（水系相关）→ 10 个子类别

| 子类别 | 英文名 | 语义描述 | 示例字符 |
|--------|--------|----------|----------|
| 河流 | water_river | 大型自然水道 | 江、河、溪、涧、川 |
| 溪流 | water_stream | 小型人工或自然水道 | 涌、沥、渠、沟、圳 |
| 港口 | water_port | 水运交通设施 | 港、津、渡、埠、码 |
| 池塘 | water_pond | 小型静水体 | 塘、池、潭、泊、淀 |
| 湖泊 | water_lake | 大型静水体 | 湖、泽、洼 |
| 海湾 | water_bay | 海岸凹入部分 | 湾、浦、滘、濠 |
| 岸边 | water_shore | 水体边缘 | 滨、岸、汀、渚、沿 |
| 岛屿 | water_island | 水中陆地 | 洲、屿、岛 |
| 滩涂 | water_beach | 水边沙地 | 滩、沙 |
| 泉井 | water_spring | 地下水出口 | 泉、井 |

---

## 标注规则

### 1. 优先原则

当一个字符可能属于多个子类别时，按以下优先级选择：

1. **最常见语义**：选择在村名中最常出现的语义
2. **地理特征**：优先选择地理特征更明显的类别
3. **区域习惯**：考虑广东地区的命名习惯

### 2. 边界案例处理

| 字符 | 可能类别 | 最终选择 | 理由 |
|------|----------|----------|------|
| 坡 | mountain_slope / mountain_valley | mountain_slope | 更强调倾斜面而非低洼 |
| 坑 | mountain_valley / water_pond | mountain_valley | 在村名中多指地形而非水体 |
| 塱 | mountain_plateau / agriculture_field | mountain_plateau | 强调地形平坦而非农业用途 |
| 沟 | water_stream / mountain_valley | water_stream | 强调水道而非地形 |
| 渠 | water_stream / agriculture_irrigation | water_stream | 在村名中多指水道 |

### 3. 验证标准

**语义一致性：** 同一子类别的字符应在 Word2Vec 嵌入空间中相似度 ≥ 0.7

**覆盖完整性：** 所有原类别字符都应分配到子类别

**标注准确率：** 人工验证准确率 ≥ 90%

---

## 实施步骤

### Phase 1: 准备阶段（0.5 天）

1. 创建项目文档（本文件）
2. 提取 mountain 和 water 字符列表
3. 统计字符频率和示例村名
4. 准备 Word2Vec 嵌入数据

### Phase 2: LLM 辅助标注（1-2 天）

1. 配置 DeepSeek API
2. 设计标注 prompt
3. 批量标注 73 个字符
4. 人工审核和修正

### Phase 3: 数据生成（1-2 天）

1. 生成 v4_pilot.json 词典
2. 创建数据表
3. 计算子类别 VTF
4. 数据验证

### Phase 4: API 集成（0.5 天）

1. 创建子类别端点
2. 更新现有端点
3. 编写 API 文档

### Phase 5: 评估报告（0.5 天）

1. 数据质量评估
2. 实用价值评估
3. 成本效益分析
4. 产出试点报告

---

## 数据表设计

### semantic_subcategory_labels

存储字符到子类别的映射关系

```sql
CREATE TABLE semantic_subcategory_labels (
    char TEXT PRIMARY KEY,
    parent_category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    confidence REAL,
    labeling_method TEXT,
    created_at REAL
);
```

### semantic_subcategory_vtf_global

全局子类别虚拟词频统计

```sql
CREATE TABLE semantic_subcategory_vtf_global (
    subcategory TEXT PRIMARY KEY,
    parent_category TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    village_count INTEGER NOT NULL,
    vtf REAL NOT NULL,
    percentage REAL NOT NULL,
    created_at REAL
);
```

### semantic_subcategory_vtf_regional

区域子类别虚拟词频统计

```sql
CREATE TABLE semantic_subcategory_vtf_regional (
    region_level TEXT NOT NULL,
    region_name TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    parent_category TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    village_count INTEGER NOT NULL,
    vtf REAL NOT NULL,
    percentage REAL NOT NULL,
    tendency REAL,
    created_at REAL,
    PRIMARY KEY (region_level, region_name, subcategory)
);
```

---

## API 端点设计

### 新增端点

1. `GET /api/semantic/subcategories` - 获取所有子类别列表
2. `GET /api/semantic/subcategory/{category}` - 获取特定子类别的字符
3. `GET /api/semantic/subcategory/regional` - 区域子类别分布
4. `GET /api/semantic/subcategory/vtf` - 子类别虚拟词频

### 更新端点

在现有语义端点中添加 `use_subcategory` 参数，支持按子类别过滤和聚合

---

## 成本估算

### LLM 标注成本

- DeepSeek API: ~$0.008（约 0.06 元人民币）
- 73 个字符 × 500 tokens/字符 = 36,500 tokens

### 人工成本

- LLM 标注审核：2-3 小时
- 边界案例处理：1-2 小时
- 数据验证：1 小时
- 总计：4-6 小时

### 计算成本

- 数据生成：1-2 小时
- API 开发：2-3 小时
- 文档编写：1-2 小时
- 总计：4-7 小时

**总投入：** 8-13 小时（约 1-2 个工作日）

---

## 成功标准

1. ✅ 标注准确率 ≥ 90%
2. ✅ 语义一致性 ≥ 0.7
3. ✅ API 端点正常工作
4. ✅ 前端团队认可实用价值
5. ✅ 总投入 ≤ 2 个工作日
6. ✅ 向后兼容现有功能

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 子类别边界模糊 | 制定清晰标注规则，记录边界案例 |
| LLM 标注不准确 | 使用 Word2Vec 验证，人工审核所有结果 |
| 实用价值不足 | 采用试点策略，收集前端反馈 |
| 向后兼容问题 | 保留原有表和 API，新增作为可选功能 |

---

## 参考资料

- `data/semantic_lexicon_v1.json` - 原始 9 大类别词典
- `data/semantic_lexicon_v3_expanded.json` - 50+ 细分类别参考
- `scripts/analysis/llm_label_characters.py` - LLM 标注工具
- `docs/phases/PHASE_02_IMPLEMENTATION_SUMMARY.md` - Phase 2 实施总结

---

**创建时间：** 2026-02-25
**状态：** 实施中
**负责人：** Claude Code
