# Phase 2 进度报告：数据生成脚本重构

## 已完成的工作

### 1. 字符频率计算模块 ✅

**文件**: `src/analysis/char_frequency.py`

**修改内容**:
- 重构了 `compute_char_frequency_by_region()` 函数（第 72-148 行）
- **关键改进**:
  - 添加了层级分组逻辑：
    - City 级别：按 `市级` 分组
    - County 级别：按 `(市级, 区县级)` 分组
    - Township 级别：按 `(市级, 区县级, 乡镇级)` 分组
  - 在结果中添加了 `city`、`county`、`township` 列
  - 保留了 `region_name` 列用于显示和向后兼容
  - 使用层级键进行排名，而不是只使用 region_name

**影响**: 现在字符频率计算会正确分离重复地名（如"太平镇"）

### 2. 区域倾向性分析模块 ✅

**文件**: `src/analysis/regional_analysis.py`

**修改内容**:
- 重构了 `compute_regional_tendency()` 函数中的排名逻辑（第 294-314 行）
- **关键改进**:
  - 检测是否存在层级列（city, county, township）
  - 根据 region_level 自动选择正确的分组列
  - 如果层级列不存在，回退到使用 region_name（向后兼容）
  - 使用层级键进行排名计算

**影响**: 倾向性分析现在会为每个独立的地理位置计算正确的排名

### 3. 数据库写入模块 ✅

**文件**: `src/data/db_writer.py`

**新增函数**:

#### 3.1 `write_char_regional_analysis()`
- 写入字符区域分析数据到优化后的表
- 支持层级列（city, county, township）
- 合并了频率和倾向性数据
- 批量插入，性能优化

#### 3.2 `write_pattern_regional_analysis()`
- 写入模式区域分析数据
- 支持层级列
- 包含 pattern_type 字段

#### 3.3 `write_semantic_regional_analysis()`
- 写入语义区域分析数据
- 支持层级列
- 包含 category 和 vtf_count 字段

**影响**: 现在可以直接将带有层级列的数据写入优化后的表

---

## 待完成的工作

### 4. 语义 VTF 计算器 ⏳

**文件**: `src/semantic/vtf_calculator.py`

**需要修改**:
- `calculate_regional_vtf()` 方法（约第 76-147 行）
- 按层级键分组，而不是只按 region_name
- 在结果中添加 city、county、township 列

**修改模式**:
```python
# Before
regions = level_df['region_name'].unique()
for region in regions:
    region_df = level_df[level_df['region_name'] == region]

# After
if region_level == 'city':
    group_cols = ['市级']
elif region_level == 'county':
    group_cols = ['市级', '区县级']
else:  # township
    group_cols = ['市级', '区县级', '乡镇级']

for group_key, region_df in level_df.groupby(group_cols):
    # Extract hierarchical values
    # Add to results with city, county, township columns
```

### 5. N-gram 分析脚本 ⏳

**文件**: `scripts/core/phase12_ngram_analysis.py`

**需要修改**:
- 加载村庄数据时保留 city/county/township 列
- 按层级键分组计算区域 n-gram 频率
- 将层级列写入数据库

**涉及的表**:
- `regional_ngram_frequency`
- `ngram_tendency`
- `ngram_significance`

### 6. 模式分析脚本 ⏳

**文件**: `scripts/core/run_morphology_analysis.py`

**需要修改**:
- 类似于字符频率分析
- 按层级键分组
- 写入层级列到数据库

### 7. 管道集成 ⏳

**文件**: `src/pipelines/frequency_pipeline.py`

**需要修改**:
- 修改 `_compute_regional_tendencies()` 方法
- 使用新的 `write_char_regional_analysis()` 函数
- 确保数据流正确传递层级列

**当前问题**:
- 管道调用 `persist_results_to_db()` 写入旧表
- 需要改为调用新的写入函数

---

## 技术细节

### 层级分组逻辑

```python
# 根据 region_level 确定分组列
if region_level == 'city':
    group_cols = ['市级']
elif region_level == 'county':
    group_cols = ['市级', '区县级']
else:  # township
    group_cols = ['市级', '区县级', '乡镇级']

# 分组并提取层级值
for group_key, group in df.groupby(group_cols):
    if isinstance(group_key, tuple):
        city, county, *township = group_key + (None,) * (3 - len(group_key))
    else:
        city = group_key
        county = None
        township = None

    # 添加到结果
    results.append({
        'city': city,
        'county': county,
        'township': township,
        'region_name': group[region_col].iloc[0],
        # ... other fields
    })
```

### 数据库写入模式

```python
# 准备数据
columns = [
    'region_level', 'city', 'county', 'township', 'region_name', 'char',
    'village_count', 'total_villages', 'frequency', 'rank_within_region',
    'global_village_count', 'global_frequency',
    'lift', 'log_lift', 'log_odds', 'z_score', 'support_flag',
    'rank_overrepresented', 'rank_underrepresented'
]

# 批量插入
cursor.executemany("""
    INSERT OR REPLACE INTO char_regional_analysis
    (region_level, city, county, township, region_name, char, ...)
    VALUES (?, ?, ?, ?, ?, ?, ...)
""", batch)
```

---

## 下一步行动

### 立即执行（优先级高）

1. **修改 VTF 计算器** (`src/semantic/vtf_calculator.py`)
   - 这是语义分析的核心
   - 影响 `semantic_regional_analysis` 表

2. **修改 N-gram 分析** (`scripts/core/phase12_ngram_analysis.py`)
   - 影响 3 个表
   - 需要更新写入逻辑

3. **修改模式分析** (`scripts/core/run_morphology_analysis.py`)
   - 影响 `pattern_regional_analysis` 表

### 后续执行（优先级中）

4. **集成到管道** (`src/pipelines/frequency_pipeline.py`)
   - 确保所有组件正确连接
   - 测试端到端流程

5. **创建测试脚本**
   - 测试单个模块
   - 验证数据正确性

---

## 预计时间

- **VTF 计算器**: 1-2 小时
- **N-gram 分析**: 2-3 小时
- **模式分析**: 1-2 小时
- **管道集成**: 1-2 小时
- **测试**: 1-2 小时

**总计**: 6-11 小时

---

## 风险和注意事项

### 1. 数据一致性
- 确保所有模块使用相同的层级分组逻辑
- 验证 NULL 值处理（某些级别可能为 NULL）

### 2. 性能影响
- 层级分组可能比简单分组慢
- 需要监控执行时间
- 批量插入已优化

### 3. 向后兼容性
- 保留 region_name 列
- 旧代码仍可使用 region_name（但会返回多条记录）

### 4. 测试覆盖
- 需要测试"太平镇"等重复地名
- 验证 7 个位置都被正确分离
- 检查村庄总数是否匹配

---

## 成功标准

✅ **Phase 2 完成标准**:
1. 所有数据生成脚本都使用层级分组
2. 所有区域分析表都包含 city、county、township 列
3. 重复地名被正确分离（如"太平镇"有 7 条记录）
4. 数据可以成功写入优化后的表
5. 向后兼容性保持（region_name 仍可用）

---

**最后更新**: 2026-02-24
**状态**: Phase 2 进行中（约 40% 完成）
**下一步**: 修改 VTF 计算器
