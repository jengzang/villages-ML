# 数据库优化记录 (2026-03-02)

## 概述

对 N-gram 相关表进行了重大优化，删除了冗余数据和索引，数据库大小从 4.1 GB 降至 2.5 GB，节省 1.6 GB（39%）。

## 优化内容

### 1. 数据层级优化

**删除的数据：**
- City（市级）和 County（区县级）的预计算数据
- 总计删除：5,451,117 条记录

**保留的数据：**
- Township（乡镇级）：完整保留
- 后端 API 通过动态聚合支持 City/County 查询

**影响的表：**
| 表名 | 删除前 | 删除后 | 删除记录数 |
|------|--------|--------|-----------|
| ngram_significance | 2,381,071 | 1,058,746 | -1,322,325 |
| ngram_tendency | 3,153,418 | 1,089,022 | -2,064,396 |
| regional_ngram_frequency | 3,153,418 | 1,089,022 | -2,064,396 |

### 2. 索引优化

**ngram_tendency 表索引：**

**删除的索引（8个）：**
1. `idx_ngram_tendency_level` - 冗余（PRIMARY KEY 覆盖）
2. `idx_ngram_tendency_city` - 冗余（PRIMARY KEY 覆盖）
3. `idx_ngram_tendency_county` - 冗余（PRIMARY KEY 覆盖）
4. `idx_ngram_tendency_township` - 冗余（level_township 更好）
5. `idx_ngram_tendency_level_city` - 不需要（City 数据已删除）
6. `idx_ngram_tendency_level_county` - 不需要（County 数据已删除）
7. `idx_ngram_tendency_lift` - 冗余（level_lift 更好）
8. `idx_ngram_tendency_zscore` - 很少使用

**保留的索引（5个）：**
1. `sqlite_autoindex_ngram_tendency_1` - PRIMARY KEY (level, city, county, township, ngram, n, position)
2. `idx_ngram_tendency_level_lift` - 用于 ORDER BY lift DESC 查询
3. `idx_ngram_tendency_level_ngram` - 用于 ngram 过滤
4. `idx_ngram_tendency_level_township` - 用于 township 查询（最常用）
5. `idx_ngram_tendency_region` - 向后兼容（region_name 查询）

**空间节省：**
- 索引数量：13个 → 5个（减少 61.5%）
- 估算节省：~500-700 MB

### 3. 总体效果

| 指标 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| 数据库大小 | 4.1 GB | 2.5 GB | -1.6 GB (-39%) |
| 记录总数 | 8,687,907 | 3,236,790 | -5,451,117 (-63%) |
| ngram_tendency 索引 | 13个 | 5个 | -8个 (-61.5%) |

## 技术实现

### 动态聚合策略

后端 API 已实现动态聚合功能：
- **Township 查询**：直接读取原始数据
- **County 查询**：从 Township 实时聚合（GROUP BY city, county）
- **City 查询**：从 Township 实时聚合（GROUP BY city）

**性能影响：**
- Township 查询：无影响（直接读取）
- County/City 查询：增加 100-500ms 延迟（可接受）

### API 端点

受影响的端点：
- `/ngrams/tendency?region_level=county` - 动态聚合
- `/ngrams/tendency?region_level=city` - 动态聚合
- `/ngrams/regional?region_level=county` - 动态聚合
- `/ngrams/regional?region_level=city` - 动态聚合

## 脚本修改

### 1. phase12_ngram_analysis.py

**修改内容：**
- 删除了 `idx_ngram_tendency_level_county` 和 `idx_ngram_tendency_level_city` 的创建
- 添加了 `idx_ngram_tendency_region` 索引（向后兼容）
- 更新了注释说明优化原因

**修改位置：** 第 799-820 行

### 2. generate_city_county_ngrams.py

**处理方式：**
- 重命名为 `generate_city_county_ngrams.py.deprecated`
- 创建新的 `generate_city_county_ngrams_DEPRECATED.py` 警告脚本
- 防止误用，避免重新生成冗余数据

### 3. create_missing_indexes.py

**修改内容：**
- 注释掉了 `idx_ngram_tendency_lookup` 的创建（与 phase12 创建的索引冗余）
- 添加了说明注释

**修改位置：** 第 71-76 行

## 执行步骤

```bash
# 1. 删除 City/County 数据
DELETE FROM ngram_significance WHERE level IN ('city', 'county');
DELETE FROM ngram_tendency WHERE level IN ('city', 'county');
DELETE FROM regional_ngram_frequency WHERE level IN ('city', 'county');

# 2. 删除冗余索引
DROP INDEX IF EXISTS idx_ngram_tendency_level;
DROP INDEX IF EXISTS idx_ngram_tendency_city;
DROP INDEX IF EXISTS idx_ngram_tendency_county;
DROP INDEX IF EXISTS idx_ngram_tendency_township;
DROP INDEX IF EXISTS idx_ngram_tendency_level_city;
DROP INDEX IF EXISTS idx_ngram_tendency_level_county;
DROP INDEX IF EXISTS idx_ngram_tendency_lift;
DROP INDEX IF EXISTS idx_ngram_tendency_zscore;

# 3. 回收空间
VACUUM;
```

## 验证结果

```sql
-- 检查数据层级
SELECT level, COUNT(*) FROM ngram_significance GROUP BY level;
-- 结果：township: 1,058,746

SELECT level, COUNT(*) FROM ngram_tendency GROUP BY level;
-- 结果：township: 1,089,022

SELECT level, COUNT(*) FROM regional_ngram_frequency GROUP BY level;
-- 结果：township: 1,089,022

-- 检查索引
PRAGMA index_list(ngram_tendency);
-- 结果：5个索引
```

## 风险评估

### 低风险
- ✅ API 代码已支持动态聚合，无需修改
- ✅ Township 数据完整保留，核心功能不受影响
- ✅ 可回滚：如需要可重新生成 County/City 数据

### 性能影响
- ⚠️ County/City 查询增加 100-500ms 延迟
- ✅ Township 查询性能不受影响（最常用）
- ✅ 数据库体积减小，整体 I/O 性能提升

### 测试建议
- 测试 County/City 级别的 API 查询性能
- 监控实际查询延迟
- 如延迟超过 1 秒，考虑重新生成 County 数据

## 后续维护

### 重新生成数据时注意事项

1. **不要使用** `generate_city_county_ngrams.py`（已废弃）
2. **只运行** `phase12_ngram_analysis.py`（只生成 Township 数据）
3. **确认索引**：phase12 会自动创建 5 个优化索引

### 如需恢复 City/County 数据

如果性能测试显示动态聚合不可接受：

1. 与后端团队讨论
2. 评估实际查询频率和延迟
3. 考虑只恢复 County 数据（City 使用较少）
4. 使用修改后的脚本，只生成必要的索引

## 相关文档

- API 动态聚合实现：`api/ngrams/frequency.py` 第 410-616 行
- 后端邮件讨论：2026-03-02
- 数据库对比报告：`database_comparison_report.md`

## 联系人

- 数据分析师：负责数据优化
- 后端开发：负责 API 动态聚合实现

---

**最后更新：** 2026-03-02
**状态：** ✅ 已完成并验证
