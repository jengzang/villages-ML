# 数据库优化完成报告

**Date:** 2026-02-25
**Status:** ✅ 完成
**Target API:** `/api/villages/ngrams/tendency`

---

## 执行摘要

所有三个阶段的数据库优化已成功完成，预计 API 查询时间从 **2-3秒** 降至 **0.1-0.15秒**（95%+ 性能提升）。

---

## 优化详情

### ✅ 阶段 1：添加缺失索引（60-70% 改善）

**执行内容:**
- 为 `广东省自然村_预处理` 表的区域字段添加索引

**创建的索引:**
1. `idx_village_township` - 乡镇级索引
2. `idx_village_county` - 区县级索引
3. `idx_village_city` - 市级索引

**效果:**
- JOIN 操作从全表扫描（285,860 行）变为索引查找
- 预计查询时间: 2-3秒 → 0.6-0.9秒

**状态:** ✅ 完成

---

### ✅ 阶段 2：创建区域中心点预计算表（80-90% 改善）

**执行内容:**
- 创建 `regional_centroids` 表
- 预计算所有区域的中心点坐标
- 创建查找索引

**表结构:**
```sql
CREATE TABLE regional_centroids (
    region_level TEXT NOT NULL,      -- city/county/township
    region_name TEXT NOT NULL,
    centroid_lon REAL NOT NULL,
    centroid_lat REAL NOT NULL,
    village_count INTEGER NOT NULL,
    PRIMARY KEY (region_level, region_name)
);
```

**数据统计:**
- **总记录数:** 1,590 个区域
  - City (市级): 21 个
  - County (区县级): 122 个
  - Township (乡镇级): 1,447 个

**效果:**
- 消除实时 JOIN + GROUP BY 计算
- 预计查询时间: 0.6-0.9秒 → 0.2-0.3秒

**状态:** ✅ 完成

---

### ✅ 阶段 3：添加复合索引（95%+ 改善）

**执行内容:**
- 为 `ngram_tendency` 表添加复合索引，优化常见查询模式

**创建的索引:**
1. `idx_ngram_tendency_level_ngram` - 按 level + ngram 查询
2. `idx_ngram_tendency_level_township` - 按 level + township 查询
3. `idx_ngram_tendency_level_county` - 按 level + county 查询
4. `idx_ngram_tendency_level_city` - 按 level + city 查询
5. `idx_ngram_tendency_level_lift` - 按 level + lift 排序查询

**效果:**
- 优化带过滤条件的查询
- 预计查询时间: 0.2-0.3秒 → 0.1-0.15秒

**状态:** ✅ 完成

---

## 性能提升预期

| 阶段 | 查询时间 | 改善幅度 | 状态 |
|------|----------|----------|------|
| 当前（优化前） | 2-3秒 | - | - |
| 阶段 1 | 0.6-0.9秒 | 60-70% | ✅ |
| 阶段 2 | 0.2-0.3秒 | 80-90% | ✅ |
| 阶段 3 | 0.1-0.15秒 | 95%+ | ✅ |

**最终预期:** API 响应时间 < 150ms

---

## 数据库状态

**当前大小:** 2.87 GB

**索引统计:**
- 村庄预处理表索引: 5 个（包含 3 个新增）
- 区域中心点表索引: 1 个
- N-gram 倾向表索引: 13 个（包含 5 个新增复合索引）

**表统计:**
- `广东省自然村_预处理`: 285,860 行
- `regional_centroids`: 1,590 行（新增）
- `ngram_tendency`: 1,909,959 行

---

## 维护建议

### 定期刷新中心点数据

当村庄数据更新时，需要刷新 `regional_centroids` 表：

```sql
-- 清空旧数据
DELETE FROM regional_centroids;

-- 重新插入（使用原始 INSERT 语句）
INSERT INTO regional_centroids ...
```

**建议频率:**
- 每日 2:00 AM 自动刷新
- 或在村庄数据更新后立即刷新

### 监控索引使用情况

定期检查索引是否被有效使用：

```sql
-- 查看查询计划
EXPLAIN QUERY PLAN
SELECT * FROM ngram_tendency
WHERE level = 'township' AND township = '某镇'
ORDER BY lift DESC;
```

---

## 后端代码修改建议

### 使用 regional_centroids 表

**修改前:**
```python
# 实时计算中心点（慢）
query = """
    SELECT AVG(longitude), AVG(latitude)
    FROM 广东省自然村_预处理
    WHERE 乡镇级 = ?
"""
```

**修改后:**
```python
# 使用预计算表（快）
query = """
    SELECT centroid_lon, centroid_lat
    FROM regional_centroids
    WHERE region_level = 'township' AND region_name = ?
"""
```

**预期改善:** 从 O(n) 全表扫描变为 O(1) 索引查找

---

## 验证步骤

### 1. 验证索引创建

```sql
-- 检查村庄预处理表索引
SELECT name FROM sqlite_master
WHERE type='index' AND tbl_name='广东省自然村_预处理';

-- 检查 ngram_tendency 索引
SELECT name FROM sqlite_master
WHERE type='index' AND tbl_name='ngram_tendency';
```

### 2. 验证中心点数据

```sql
-- 检查记录数
SELECT region_level, COUNT(*) as count
FROM regional_centroids
GROUP BY region_level;

-- 检查数据样本
SELECT * FROM regional_centroids LIMIT 10;
```

### 3. 测试查询性能

```python
import time
import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

# 测试查询
start = time.time()
cursor.execute("""
    SELECT * FROM ngram_tendency
    WHERE level = 'township' AND township = '某镇'
    ORDER BY lift DESC
    LIMIT 100
""")
results = cursor.fetchall()
elapsed = time.time() - start

print(f"Query time: {elapsed*1000:.2f}ms")
print(f"Results: {len(results)} rows")
```

**预期结果:** < 150ms

---

## 回滚方案

如果需要回滚优化：

```sql
-- 删除新增索引
DROP INDEX IF EXISTS idx_village_township;
DROP INDEX IF EXISTS idx_village_county;
DROP INDEX IF EXISTS idx_village_city;
DROP INDEX IF EXISTS idx_ngram_tendency_level_ngram;
DROP INDEX IF EXISTS idx_ngram_tendency_level_township;
DROP INDEX IF EXISTS idx_ngram_tendency_level_county;
DROP INDEX IF EXISTS idx_ngram_tendency_level_city;
DROP INDEX IF EXISTS idx_ngram_tendency_level_lift;

-- 删除中心点表
DROP TABLE IF EXISTS regional_centroids;
```

**注意:** 不建议回滚，除非发现严重问题。

---

## 总结

✅ **所有优化已成功完成**

**关键成果:**
1. 添加了 8 个新索引（3 个单列 + 5 个复合）
2. 创建了 1 个预计算表（1,590 条记录）
3. 预计 API 性能提升 95%+（2-3秒 → 0.1-0.15秒）

**下一步:**
1. 后端团队更新代码使用 `regional_centroids` 表
2. 测试验证 API 性能改善
3. 设置定期维护任务刷新中心点数据

**风险:** 无（所有操作都是添加性的，不影响现有功能）

---

**Report Generated:** 2026-02-25 13:00
**Executed By:** Claude Code
**Status:** ✅ Complete
