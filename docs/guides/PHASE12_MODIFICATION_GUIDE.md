# Phase 12 N-gram Analysis 修改指南

## 目标
添加 `regional_total_raw` 和 `total_before_filter` 字段，用于记录清理前的原始 n-gram 总数。

## 修改步骤

### 1. 在 Step 3 之后添加新步骤：计算原始总数

在 `step3_extract_regional_ngrams()` 函数之后，添加以下代码：

```python
def step3_5_calculate_regional_totals_raw(db_path: str):
    """Step 3.5: Calculate and store regional total raw counts (before filtering)."""
    print("\n" + "="*60)
    print("Step 3.5: Calculating Regional Total Raw Counts")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create temporary table to store raw totals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_regional_totals_raw (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            total_raw INTEGER NOT NULL,
            PRIMARY KEY (level, city, county, township, n, position)
        )
    """)

    # Clear old data
    cursor.execute("DELETE FROM temp_regional_totals_raw")

    # Calculate raw totals for each region-position combination
    cursor.execute("""
        INSERT INTO temp_regional_totals_raw
        SELECT level, city, county, township, n, position, COUNT(*) as total_raw
        FROM regional_ngram_frequency
        GROUP BY level, city, county, township, n, position
    """)

    rows_inserted = cursor.rowcount
    print(f"  Calculated raw totals for {rows_inserted:,} region-position combinations")

    conn.commit()
    conn.close()

    print("[OK] Regional total raw counts calculated")
```

### 2. 修改 Step 4：在计算倾向值时添加 regional_total_raw

在 `step4_calculate_tendency()` 函数中，修改以下部分：

**原代码（第 259-290 行）：**
```python
regional_count, regional_total = regional_result

# ... (获取 global counts)

# Store results with hierarchical columns
cursor.execute("""
    INSERT OR REPLACE INTO ngram_tendency
    (level, city, county, township, region, ngram, n, position, lift, log_odds, z_score,
     regional_count, regional_total, global_count, global_total)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    level_en, city, county, township, region, ngram, n, position,
    tendency['lift'], tendency['log_odds'], tendency['z_score'],
    regional_count, regional_total, global_count, global_total
))
```

**修改为：**
```python
regional_count, regional_total = regional_result

# Get regional_total_raw from temp table
cursor.execute("""
    SELECT total_raw
    FROM temp_regional_totals_raw
    WHERE level = ? AND city IS ? AND county IS ? AND township IS ?
      AND n = ? AND position = ?
""", (level_en, city, county, township, n, position))

raw_result = cursor.fetchone()
regional_total_raw = raw_result[0] if raw_result else regional_total

# ... (获取 global counts)

# Store results with hierarchical columns (including regional_total_raw)
cursor.execute("""
    INSERT OR REPLACE INTO ngram_tendency
    (level, city, county, township, region, ngram, n, position, lift, log_odds, z_score,
     regional_count, regional_total, regional_total_raw, global_count, global_total)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    level_en, city, county, township, region, ngram, n, position,
    tendency['lift'], tendency['log_odds'], tendency['z_score'],
    regional_count, regional_total, regional_total_raw, global_count, global_total
))
```

### 3. 修改 Step 5：在显著性测试时添加 total_before_filter

在 `step5_calculate_significance()` 函数中，修改以下部分：

**找到第 362-370 行的代码：**
```python
# ONLY store significant results (p < 0.05)
if is_significant:
    cursor.execute("""
        INSERT OR REPLACE INTO ngram_significance
        (level, city, county, township, region, ngram, n, position, chi2, p_value, cramers_v, is_significant)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (level_db, city, county, township, region, ngram, n, position,
          sig['chi2'], sig['p_value'], sig['cramers_v'], 1))
    significant_count += 1
```

**修改为：**
```python
# ONLY store significant results (p < 0.05)
if is_significant:
    # Get total_before_filter from temp table
    cursor.execute("""
        SELECT total_raw
        FROM temp_regional_totals_raw
        WHERE level = ? AND city IS ? AND county IS ? AND township IS ?
          AND n = ? AND position = ?
    """, (level_db, city, county, township, n, position))

    raw_result = cursor.fetchone()
    total_before_filter = raw_result[0] if raw_result else regional_total

    cursor.execute("""
        INSERT OR REPLACE INTO ngram_significance
        (level, city, county, township, region, ngram, n, position, chi2, p_value, cramers_v, is_significant, total_before_filter)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (level_db, city, county, township, region, ngram, n, position,
          sig['chi2'], sig['p_value'], sig['cramers_v'], 1, total_before_filter))
    significant_count += 1
```

### 4. 在主函数中调用新步骤

在 `main()` 函数中，找到调用 Step 3 的地方，在其后添加 Step 3.5：

```python
# Step 3: Extract regional n-grams
step3_extract_regional_ngrams(db_path)

# Step 3.5: Calculate regional total raw counts (NEW)
step3_5_calculate_regional_totals_raw(db_path)

# Step 4: Calculate tendency
step4_calculate_tendency(db_path)
```

### 5. 清理临时表（可选）

在所有步骤完成后，可以选择删除临时表：

```python
def cleanup_temp_tables(db_path: str):
    """Clean up temporary tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS temp_regional_totals_raw")
    conn.commit()
    conn.close()
    print("[OK] Temporary tables cleaned up")
```

## 验证

数据生成完成后，验证新字段：

```sql
-- 检查 ngram_tendency 表
SELECT level, region, ngram, regional_total, regional_total_raw
FROM ngram_tendency
LIMIT 10;

-- 检查 ngram_significance 表
SELECT level, region, ngram, total_before_filter
FROM ngram_significance
LIMIT 10;

-- 验证过滤率
SELECT
    level,
    COUNT(*) as total_records,
    AVG(CAST(regional_total as FLOAT) / regional_total_raw) as avg_retention_rate
FROM ngram_tendency
WHERE regional_total_raw IS NOT NULL
GROUP BY level;
```

## 注意事项

1. `regional_total_raw` 字段可能为 NULL（如果临时表中没有对应记录）
2. `total_before_filter` 字段可能为 NULL（同上）
3. 临时表 `temp_regional_totals_raw` 在数据生成过程中使用，完成后可以删除
4. 确保在 Step 6 清理数据之前，所有需要原始总数的字段都已填充
