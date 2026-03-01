# 语义词典版本管理

本文档记录项目中使用的语义词典版本及其对应的数据表和脚本。

## 词典版本概览

| 版本 | 类别数 | 字符数 | 类型 | 文件路径 |
|------|--------|--------|------|----------|
| v1 | 9 | 242 | 主类别 | `data/semantic_lexicon_v1.json` |
| v2_demo | 9 | 244 | 主类别 | `data/semantic_lexicon_v2_demo.json` |
| v3_expanded | 78 | 335 | 细分类别 | `data/semantic_lexicon_v3_expanded.json` |
| v4_pilot | 16 | 66 | 子类别（试点） | `data/semantic_lexicon_v4_pilot.json` |
| v4_hybrid | 76 | 313 | 子类别（混合） | `data/semantic_lexicon_v4_hybrid.json` |

## 版本详情

### v1 - 基础版本（9大类别）

**类别：**
- mountain, water, settlement, direction, clan, symbolic, agriculture, vegetation, infrastructure

**用途：**
- 基础语义分析
- 区域倾向性分析
- VTF 计算

**使用的脚本：**
- `scripts/core/regenerate_semantic_analysis.py`
- `scripts/core/run_semantic_analysis.py`
- `scripts/core/populate_semantic_indices.py`
- `scripts/core/generate_village_features.py`

**生成的数据表：**
- `semantic_regional_analysis` (15,489 records)
- `semantic_vtf_global`
- `semantic_vtf_regional`

---

### v2_demo - 演示版本（9大类别）

**说明：**
- v1 的演示版本，字符数略有增加（244 vs 242）
- 主要用于早期开发和测试

**用途：**
- 已废弃，不再推荐使用
- 被 v1 或 v3 替代

---

### v3_expanded - 扩展版本（78细分类别）

**类别示例：**
- mountain_peak, mountain_slope, mountain_valley, mountain_ridge, mountain_rock, mountain_plateau
- water_river, water_stream, water_port, water_pond, water_lake, water_bay
- settlement_village, settlement_market, settlement_district, settlement_building
- direction_cardinal, direction_center, direction_vertical, direction_horizontal
- clan_chen, clan_li, clan_huang, clan_zhang, clan_liu
- symbolic_animal, symbolic_religion, symbolic_fortune, symbolic_peace
- agriculture_field, agriculture_garden, agriculture_crop, agriculture_storage
- vegetation_forest, vegetation_bamboo, vegetation_pine, vegetation_fruit
- infrastructure_bridge, infrastructure_road, infrastructure_station, infrastructure_port
- 其他：number_small, number_large, size_large, size_small, color, shape, time, other

**用途：**
- 细粒度语义组合分析
- 语义 bigram/trigram 分析
- 修饰-中心词模式识别

**使用的脚本：**
- `scripts/core/phase14_semantic_composition.py` ⭐
- `src/semantic_composition.py` (默认词典)

**生成的数据表：**
- `semantic_bigrams` (4,332 records)
- `semantic_trigrams`
- `semantic_composition_patterns`
- `semantic_conflicts`
- `semantic_pmi`

---

### v4_pilot - 试点版本（16子类别）

**说明：**
- Phase 17 试点版本
- 仅细化 mountain 和 water 两个类别
- 6 个 mountain 子类别 + 10 个 water 子类别

**用途：**
- Phase 17 早期试点
- 已被 v4_hybrid 替代

---

### v4_hybrid - 混合版本（76子类别）⭐ 推荐

**说明：**
- Phase 17 最终版本
- 结合 LLM 标注和专家知识
- 覆盖所有 9 大类别的细分

**类别数量：**
- 76 个子类别
- 313 个字符

**用途：**
- 精细化语义分析
- 子类别倾向性分析
- 区域语义特征提取

**使用的脚本：**
- `scripts/core/phase17_semantic_subcategory.py` ⭐
- `scripts/core/phase17_create_hybrid.py`
- `scripts/core/phase17_llm_validation_v2.py`

**生成的数据表：**
- `semantic_subcategory_labels` (313 records)
- `semantic_subcategory_vtf_global` (76 records)
- `semantic_subcategory_vtf_regional` (1,578 records)

---

## 数据表与词典版本对应关系

| 数据表 | 词典版本 | 类别数 | 记录数 |
|--------|----------|--------|--------|
| `semantic_regional_analysis` | v1 | 9 | 15,489 |
| `semantic_bigrams` | v3_expanded | 78 | 4,332 |
| `semantic_trigrams` | v3_expanded | 78 | - |
| `semantic_composition_patterns` | v3_expanded | 78 | 25 |
| `semantic_pmi` | v3_expanded | 78 | 100 |
| `semantic_subcategory_labels` | v4_hybrid | 76 | 313 |
| `semantic_subcategory_vtf_global` | v4_hybrid | 76 | 76 |
| `semantic_subcategory_vtf_regional` | v4_hybrid | 76 | 1,578 |

---

## 脚本词典版本硬编码规则

**原则：每个脚本明确硬编码使用的词典版本，不支持动态切换。**

### Phase 14 - 语义组合分析
```python
# src/semantic_composition.py
lexicon_path = 'data/semantic_lexicon_v3_expanded.json'  # 硬编码 v3
```

### Phase 17 - 语义子类别细化
```python
# scripts/core/phase17_semantic_subcategory.py
LEXICON_V4_HYBRID_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v4_hybrid.json"  # 硬编码 v4_hybrid
```

### 语义分析重新生成
```python
# scripts/core/regenerate_semantic_analysis.py
lexicon_path = project_root / 'data' / 'semantic_lexicon_v1.json'  # 硬编码 v1
```

---

## 常见问题

### Q: 为什么不同表使用不同的词典版本？

A: 不同分析任务需要不同粒度的语义分类：
- **v1 (9类)**：适合宏观倾向性分析，计算效率高
- **v3 (78类)**：适合细粒度组合分析，发现更多模式
- **v4 (76类)**：适合精细化特征提取，结合 LLM 优势

### Q: 如何选择使用哪个版本？

A: 根据分析目标选择：
- 区域倾向性分析 → v1
- 语义组合模式 → v3
- 精细化特征提取 → v4

### Q: 可以切换词典版本吗？

A: 不推荐。每个脚本硬编码了词典版本，切换会导致数据不一致。如需使用不同版本，应：
1. 修改脚本中的硬编码路径
2. 清空相关数据表
3. 重新运行脚本生成数据

### Q: 为什么 semantic_bigrams 的 PMI 之前是 NULL？

A: 因为表使用 v3 词典生成，但 PMI 计算代码使用 v2 词典，类别名称不匹配导致更新失败。已通过 `fix_semantic_bigrams_pmi.py` 修复。

---

## 维护指南

### 添加新词典版本

1. 创建新的 JSON 文件：`data/semantic_lexicon_vX.json`
2. 更新本文档，添加版本说明
3. 修改相关脚本，硬编码新版本路径
4. 在脚本注释中明确标注词典版本

### 修改现有词典

1. 不要直接修改现有词典文件
2. 创建新版本（如 v1 → v1.1）
3. 更新使用该词典的所有脚本
4. 重新生成相关数据表

---

**最后更新：** 2026-02-25
**维护者：** Claude Code
