# 预处理脚本修复总结

## 修复日期
2026-03-05

## 问题描述

在数据库中发现1,096个村庄（ROWID 284,765 ~ 285,860）被错误标记为无效：
- 这些村庄的原始名称包含有效中文字符（如"怡生围"、"石龙"、"西区"等）
- 但预处理后 `自然村_规范名` 和 `自然村_去前缀` 都是空字符串
- `字符数量 = 0`

根本原因：预处理脚本使用"有效"列来过滤村庄，只对有效村庄进行前缀去除和字符提取，导致这些村庄被错误处理。

## 修复内容

### 1. 修复预处理脚本 (`scripts/preprocessing/create_preprocessed_table.py`)

**修改点：**
- 移除了"有效"列的创建和使用
- 对所有村庄统一进行前缀去除处理（不再区分有效/无效）
- 对所有村庄统一提取字符集（不再跳过"无效"村庄）
- 使用 `字符数量 > 0` 作为有效性判断标准

**具体修改：**
1. **Step 1 (基础清洗)**: 移除了 `'有效'` 和 `'无效原因'` 字段的创建
2. **Step 2 (前缀去除)**: 移除了 `valid_df` 和 `df_invalid` 的分离处理，统一处理所有村庄
3. **Step 4 (字符集提取)**: 移除了对 `row['有效']` 的判断，对所有村庄提取字符集
4. **统计输出**: 使用 `字符数量 > 0` 替代 `有效 = 1`

### 2. 移除所有"有效"列引用

修改了以下8个文件，将 `WHERE 有效 = 1` 替换为 `WHERE 字符数量 > 0`：

#### 核心模块
1. **`src/data/db_loader.py`** (2处)
   - `get_regional_hierarchy()`: 第169行
   - `get_region_village_counts()`: 第221行

#### 核心分析脚本
2. **`scripts/core/train_char_embeddings.py`**
   - `load_villages()`: 第39行

3. **`scripts/core/populate_village_ngrams.py`** (2处)
   - 第41行: 统计总数
   - 第50行: 加载村庄数据

#### 实验性脚本
4. **`scripts/experimental/spatial_tendency_integration.py`**
   - `load_villages_with_chars()`: 第180行

#### 预处理脚本
5. **`scripts/preprocessing/create_audit_log.py`**
   - `populate_audit_log()`: 第102行

#### 报告生成脚本
6. **`scripts/reporting/extract_analysis_results.py`**
   - `main()`: 第34行

7. **`scripts/reporting/generate_comprehensive_report.py`**
   - `get_phase0_stats()`: 第20行
   - 同时修复了列名错误：`县区级` → `区县级`

## 影响分析

### 正面影响
1. **数据完整性提升**: 修复后，所有285,860个村庄都会被正确处理
2. **分析准确性提升**: 不再遗漏1,096个有效村庄的数据
3. **代码简化**: 移除了"有效"列的复杂逻辑，代码更清晰
4. **一致性提升**: 统一使用 `字符数量 > 0` 作为有效性判断标准

### 需要注意
1. **需要重新运行预处理**: 修复后需要重新执行 `create_preprocessed_table.py`
2. **数据库变化**: 重新预处理后，`字符数量 > 0` 的村庄数量应该增加到285,860（或接近这个数字）
3. **下游分析**: 重新预处理后，建议重新运行所有分析脚本以获得完整结果

## 验证步骤

修复后，建议执行以下验证：

```bash
# 1. 重新运行预处理
python scripts/preprocessing/create_preprocessed_table.py

# 2. 验证结果
python -c "
import sqlite3
conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# 检查有效村庄数量
cursor.execute('SELECT COUNT(*) FROM 广东省自然村_预处理 WHERE 字符数量 > 0')
valid_count = cursor.fetchone()[0]
print(f'有效村庄数: {valid_count:,}')

# 检查无效村庄数量
cursor.execute('SELECT COUNT(*) FROM 广东省自然村_预处理 WHERE 字符数量 = 0')
invalid_count = cursor.fetchone()[0]
print(f'无效村庄数: {invalid_count:,}')

# 检查之前的问题村庄
cursor.execute('SELECT 自然村_去前缀, 字符数量 FROM 广东省自然村_预处理 WHERE ROWID BETWEEN 284765 AND 284770')
print('\n之前的问题村庄样本:')
for row in cursor.fetchall():
    print(f'  村名: \"{row[0]}\", 字符数量: {row[1]}')

conn.close()
"

# 3. 测试核心分析脚本
python scripts/core/train_char_embeddings.py --run-id test_fix --db-path data/villages.db
```

## 预期结果

修复后的预期结果：
- **有效村庄数**: ~285,860 (99.9%+)
- **无效村庄数**: <100 (仅真正无效的村庄，如NULL或空字符串)
- **之前的1,096个问题村庄**: 应该都有非空的 `自然村_去前缀` 和 `字符数量 > 0`

## 相关文档

- 问题分析: 见本次对话记录
- 数据库优化: `docs/guides/DATABASE_MIGRATION_FOR_BACKEND.md`
- 预处理文档: `docs/phases/PHASE_0_PREPROCESSING_SUMMARY.md`
