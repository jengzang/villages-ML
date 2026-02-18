# Data Preprocessing Quick Start Guide

## Overview

This guide provides quick instructions for running the data preprocessing pipeline.

## Prerequisites

- Python 3.x installed
- Required packages: pandas, sqlite3 (built-in)
- Database: `data/villages.db` (285K+ villages)

## Quick Start (5 Steps)

### Step 1: Backup Existing Analysis Tables

```bash
python scripts/backup_analysis_tables.py
```

**What it does**: Creates backup copies of existing analysis tables with `_before_prefix_cleaning` suffix

**Duration**: ~5 minutes

**Output**: Backup tables in database

### Step 2: Run Preprocessing Pipeline

```bash
python scripts/create_preprocessed_table.py
```

**What it does**:
1. Loads raw village data
2. Applies basic text cleaning (brackets, noise)
3. Removes administrative prefixes
4. Normalizes numbered villages
5. Extracts character sets
6. Creates `广东省自然村_预处理` table

**Duration**: ~30-60 minutes

**Expected Results**:
- 285K rows processed
- 20-40% prefix removal rate
- 5-15% numbered village rate

### Step 3: Create Audit Log

```bash
python scripts/create_audit_log.py
```

**What it does**: Creates detailed audit log table for all prefix cleaning operations

**Duration**: ~5 minutes

**Output**: `prefix_cleaning_audit_log` table

### Step 4: Generate Audit Report

```bash
python scripts/generate_audit_report.py
```

**What it does**: Generates comprehensive audit report with statistics and samples

**Duration**: ~5 minutes

**Output**: `docs/PREFIX_CLEANING_AUDIT_REPORT.md`

### Step 5: Review Results

Open and review: `docs/PREFIX_CLEANING_AUDIT_REPORT.md`

**Check**:
- Prefix removal rate (should be 20-40%)
- Confidence distribution (most should be >0.7)
- Random sample verification (spot check 10-20 cases)
- Cases needing review (if any)

## Rerun Analysis (Optional)

If preprocessing results look good, rerun analysis pipelines:

```bash
# Phase 1: Character frequency
python scripts/phase1_frequency_analysis.py

# Phase 2: Regional tendency
python scripts/phase2_regional_tendency.py

# Phase 8: Z-score normalization
python scripts/phase8_zscore_normalization.py

# Phase 9: Significance testing
python scripts/phase9_significance_testing.py
```

**Duration**: ~30 minutes total

## Troubleshooting

### Issue: Database not found

**Solution**: Check that `data/villages.db` exists

```bash
ls -lh data/villages.db
```

### Issue: Preprocessing takes too long

**Expected**: 30-60 minutes is normal for 285K villages

**If >2 hours**: Check system resources (CPU, memory)

### Issue: Low prefix removal rate (<10%)

**Possible causes**:
- Confidence threshold too high
- Match logic too conservative
- Data quality issues

**Solution**: Review audit report and adjust parameters if needed

### Issue: High prefix removal rate (>60%)

**Possible causes**:
- Confidence threshold too low
- Match logic too aggressive

**Solution**: Review random samples in audit report for false positives

## Testing

Run unit tests to verify implementation:

```bash
# Test prefix cleaner
pytest tests/unit/test_prefix_cleaner.py -v

# Test numbered village normalizer
pytest tests/unit/test_numbered_village_normalizer.py -v

# Run all tests
pytest tests/unit/ -v
```

## Using Preprocessed Data

### In Python Scripts

```python
import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect('data/villages.db')

# Load preprocessed data
query = """
SELECT
    市级, 区县级, 乡镇级, 行政村,
    自然村_规范化 AS village_name,
    字符集 AS char_set,
    字符数量 AS char_count
FROM 广东省自然村_预处理
WHERE 有效 = 1
"""
df = pd.read_sql(query, conn)

# Use normalized names for analysis
# ...
```

### Key Fields

- `自然村_基础清洗`: After basic cleaning (brackets, noise removed)
- `自然村_去前缀`: After prefix removal
- `自然村_规范化`: After numbered village normalization (use this for analysis)
- `字符集`: JSON array of unique characters
- `字符数量`: Number of unique characters

### Filtering

```python
# Only valid villages
WHERE 有效 = 1

# Villages with prefixes removed
WHERE 有前缀 = 1

# Villages with numbered suffixes
WHERE 有编号后缀 = 1

# High confidence prefix removal
WHERE 前缀置信度 >= 0.9

# Specific city
WHERE 市级 = '广州市'
```

## Audit Queries

### Check prefix removal statistics

```sql
SELECT
    市级,
    COUNT(*) AS total,
    SUM(有前缀) AS removed,
    ROUND(100.0 * SUM(有前缀) / COUNT(*), 2) AS removal_rate
FROM 广东省自然村_预处理
WHERE 有效 = 1
GROUP BY 市级
ORDER BY removal_rate DESC;
```

### Find most common removed prefixes

```sql
SELECT
    去除的前缀,
    COUNT(*) AS count
FROM 广东省自然村_预处理
WHERE 有前缀 = 1
GROUP BY 去除的前缀
ORDER BY count DESC
LIMIT 20;
```

### Check cases needing review

```sql
SELECT
    市级, 区县级, 乡镇级, 行政村,
    自然村, 自然村_去前缀, 去除的前缀,
    前缀匹配来源, 前缀置信度
FROM 广东省自然村_预处理
WHERE 需要审核 = 1
ORDER BY 前缀置信度 ASC
LIMIT 50;
```

## Next Steps

After preprocessing is complete:

1. **Review audit report** - Verify quality
2. **Rerun analysis** - Update Phase 1-3 results
3. **Compare results** - Generate impact report
4. **Update documentation** - Record findings
5. **Consider Phase 4-14** - Decide if rerun needed

## Support

For issues or questions:
- Check `docs/PHASE_0_PREPROCESSING_SUMMARY.md` for detailed documentation
- Review skill specifications in `.claude/skills/02_preprocessing/`
- Check project instructions in `CLAUDE.md`

## Summary

**Total Time**: ~1-2 hours
- Backup: 5 min
- Preprocessing: 30-60 min
- Audit: 10 min
- Review: 15-30 min
- Rerun analysis (optional): 30 min

**Key Outputs**:
- Preprocessed table: `广东省自然村_预处理`
- Audit log: `prefix_cleaning_audit_log`
- Audit report: `docs/PREFIX_CLEANING_AUDIT_REPORT.md`
- Updated analysis tables (if rerun)
