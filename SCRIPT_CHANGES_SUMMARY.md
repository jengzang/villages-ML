# 脚本修改总结

## 修改的文件

### 1. scripts/core/phase12_ngram_analysis.py ✅

**修改内容：**
- 删除了 2 个冗余索引的创建：
  - `idx_ngram_tendency_level_county`（County 数据已删除）
  - `idx_ngram_tendency_level_city`（City 数据已删除）
- 添加了 1 个新索引：
  - `idx_ngram_tendency_region`（向后兼容）
- 更新了注释和输出信息

**结果：** 现在只创建 4 个优化索引（加上 PRIMARY KEY 共 5 个）

### 2. scripts/core/generate_city_county_ngrams.py ⚠️ DEPRECATED

**处理方式：**
- 原文件重命名为：`generate_city_county_ngrams.py.deprecated`
- 创建新文件：`generate_city_county_ngrams_DEPRECATED.py`
  - 包含详细的废弃说明
  - 运行时会显示错误并退出
  - 防止误用

**原因：** 此脚本生成 City/County 数据，现已不需要（使用动态聚合）

### 3. scripts/maintenance/create_missing_indexes.py ✅

**修改内容：**
- 注释掉了 `idx_ngram_tendency_lookup` 的创建
- 添加了说明注释（与 phase12 创建的索引冗余）

**结果：** 避免创建重复索引

## 下次运行时的行为

### ✅ 正确的做法

```bash
# 重新生成 N-gram 数据（只生成 Township 级别）
python scripts/core/phase12_ngram_analysis.py
```

**会发生什么：**
- 只生成 Township 级别的数据
- 创建 5 个优化索引（不包含冗余索引）
- 数据库保持在 ~2.5 GB

### ❌ 错误的做法

```bash
# 不要运行这个！
python scripts/core/generate_city_county_ngrams.py
```

**会发生什么：**
- 脚本会报错并退出
- 显示废弃警告信息
- 不会生成任何数据

## 索引创建对比

### 优化前（13 个索引）
```
1. sqlite_autoindex_ngram_tendency_1 (PRIMARY KEY)
2. idx_ngram_tendency_level ❌ 删除
3. idx_ngram_tendency_city ❌ 删除
4. idx_ngram_tendency_county ❌ 删除
5. idx_ngram_tendency_township ❌ 删除
6. idx_ngram_tendency_level_city ❌ 删除
7. idx_ngram_tendency_level_county ❌ 删除
8. idx_ngram_tendency_level_ngram ✅ 保留
9. idx_ngram_tendency_level_township ✅ 保留
10. idx_ngram_tendency_level_lift ✅ 保留
11. idx_ngram_tendency_lift ❌ 删除
12. idx_ngram_tendency_zscore ❌ 删除
13. idx_ngram_tendency_region ✅ 新增
```

### 优化后（5 个索引）
```
1. sqlite_autoindex_ngram_tendency_1 (PRIMARY KEY)
2. idx_ngram_tendency_level_ngram
3. idx_ngram_tendency_level_township
4. idx_ngram_tendency_level_lift
5. idx_ngram_tendency_region
```

## 数据生成对比

### 优化前
- Township: 1,089,022 条
- County: 1,272,136 条 ❌
- City: 792,260 条 ❌
- **总计: 3,153,418 条**

### 优化后
- Township: 1,089,022 条 ✅
- County: 动态聚合 ✅
- City: 动态聚合 ✅
- **总计: 1,089,022 条**

## 验证方法

### 检查脚本是否正确修改

```bash
# 1. 检查 phase12 创建的索引
grep -A 10 "ngram_indexes = \[" scripts/core/phase12_ngram_analysis.py

# 应该看到 4 个索引（不包含 level_city 和 level_county）

# 2. 检查废弃脚本
python scripts/core/generate_city_county_ngrams_DEPRECATED.py

# 应该看到错误信息和废弃警告
```

### 运行 phase12 后验证

```bash
# 运行 phase12
python scripts/core/phase12_ngram_analysis.py

# 验证索引数量
python -c "
import sqlite3
conn = sqlite3.connect('data/villages.db')
indexes = conn.execute('PRAGMA index_list(ngram_tendency)').fetchall()
print(f'Total indexes: {len(indexes)}')
for idx in indexes:
    print(f'  - {idx[1]}')
conn.close()
"

# 应该看到 5 个索引
```

## 文档

详细文档：`docs/DATABASE_OPTIMIZATION_2026-03-02.md`

---

**修改日期：** 2026-03-02
**状态：** ✅ 完成
