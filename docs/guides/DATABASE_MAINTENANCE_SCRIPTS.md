# Database Maintenance Scripts - Quick Reference

## Overview

Three maintenance scripts for database health monitoring and optimization.

## Scripts

### 1. Create Missing Indexes

**File**: `scripts/maintenance/create_missing_indexes.py`

**Purpose**: Create database indexes based on API query analysis

**Usage**:
```bash
# Create all indexes (recommended)
python scripts/maintenance/create_missing_indexes.py

# Create only critical indexes (fastest)
python scripts/maintenance/create_missing_indexes.py --priority critical

# Create medium priority indexes
python scripts/maintenance/create_missing_indexes.py --priority medium

# Create low priority indexes
python scripts/maintenance/create_missing_indexes.py --priority low
```

**Index Priorities**:
- **CRITICAL (23)**: Heavy query load, large tables (>100K rows)
- **MEDIUM (15)**: Improves query performance (10K-100K rows)
- **LOW (7)**: Nice to have (<10K rows)

**Execution Time**:
- Critical only: 3-5 seconds
- All indexes: 15-20 seconds

**Output**:
```
Creating 47 indexes (priority: all)...
================================================================================
  [OK] [ 0.01s] char_frequency_global
  [OK] [ 0.36s] char_regional_analysis
  ...
================================================================================

[SUCCESS] Index creation complete!
   Created: 47
   Skipped: 0
   Errors: 0
   Total time: 17.81s
```

---

### 2. Drop Deprecated Tables

**File**: `scripts/maintenance/drop_deprecated_tables.py`

**Purpose**: Remove deprecated tables from database optimization (2026-02-24)

**Usage**:
```bash
python scripts/maintenance/drop_deprecated_tables.py
```

**Tables Dropped**:
- `char_frequency_regional` → replaced by `char_regional_analysis`
- `regional_tendency` → merged into `char_regional_analysis`
- `semantic_tendency` → merged into `semantic_regional_analysis`
- `semantic_vtf_regional` → merged into `semantic_regional_analysis`

**Execution Time**: <1 second

**Output**:
```
Dropping deprecated tables...
================================================================================
  [OK] Dropped: char_frequency_regional
  [OK] Dropped: regional_tendency
  [OK] Dropped: semantic_tendency
  [OK] Dropped: semantic_vtf_regional
================================================================================

[SUCCESS] Successfully dropped 4/4 deprecated tables
Database cleanup complete!
```

---

### 3. Audit Database Indexes

**File**: `scripts/maintenance/audit_database_indexes.py`

**Purpose**: Generate comprehensive index audit report

**Usage**:
```bash
# Print to console
python scripts/maintenance/audit_database_indexes.py

# Save to file
python scripts/maintenance/audit_database_indexes.py --output report.txt
```

**Execution Time**: 2-3 seconds

**Output**:
```
================================================================================
DATABASE INDEX AUDIT REPORT
================================================================================

[CRITICAL] Large tables (>10K rows) with NO indexes:
  None found [OK]

[WARNING] Large tables (>10K rows) with FEW indexes (1-2):
  - ngram_significance: 3,117,764 rows, 2 index(es)
  - pattern_frequency_global: 318,771 rows, 1 index(es)

[INFO] All tables with no indexes:
  - active_run_ids: 11 rows
  - city_aggregates: 21 rows
  ...

[SUMMARY]:
  Total tables: 47
  Tables with no indexes: 11
  Large tables needing indexes: 0

[DETAILED TABLE BREAKDOWN]:
================================================================================

ngram_significance:
  Rows: 3,117,764
  Total indexes: 3
  Non-PK indexes: 2
  Indexes:
    - idx_ngram_significance_lookup: level, ngram, is_significant
    - idx_ngram_sig_pvalue: p_value
...
```

---

## When to Use

### Create Missing Indexes

**Use when**:
- Setting up a new database
- After running analysis phases that create new tables
- Query performance is slow
- API endpoints are timing out

**Frequency**: One-time (or after major schema changes)

### Drop Deprecated Tables

**Use when**:
- After database optimization/migration
- Cleaning up old schema versions
- Reducing database size

**Frequency**: One-time (after specific migrations)

### Audit Database Indexes

**Use when**:
- Monitoring database health
- Investigating performance issues
- Planning index optimization
- Documenting database state

**Frequency**:
- Monthly for monitoring
- Before/after major changes
- When investigating performance issues

---

## Common Workflows

### Initial Setup (New Database)

```bash
# 1. Create all indexes
python scripts/maintenance/create_missing_indexes.py

# 2. Verify with audit
python scripts/maintenance/audit_database_indexes.py
```

### After Database Migration

```bash
# 1. Drop deprecated tables
python scripts/maintenance/drop_deprecated_tables.py

# 2. Create new indexes
python scripts/maintenance/create_missing_indexes.py

# 3. Verify with audit
python scripts/maintenance/audit_database_indexes.py --output migration_audit.txt
```

### Performance Investigation

```bash
# 1. Run audit to identify issues
python scripts/maintenance/audit_database_indexes.py

# 2. Create missing indexes
python scripts/maintenance/create_missing_indexes.py --priority critical

# 3. Verify improvement
python scripts/maintenance/audit_database_indexes.py
```

### Monthly Health Check

```bash
# Generate monthly report
python scripts/maintenance/audit_database_indexes.py --output reports/index_audit_$(date +%Y%m%d).txt
```

---

## Troubleshooting

### "No such table" errors

**Cause**: Table doesn't exist in current database schema

**Solution**: This is expected for some tables that were removed during optimization. The script will skip these tables automatically.

### "No such column" errors

**Cause**: Column name mismatch (e.g., run_id was removed during optimization)

**Solution**: The script has been updated to match the current schema. If you see this error, the schema may have changed again.

### Slow index creation

**Cause**: Large tables (>1M rows) take longer to index

**Solution**: This is normal. The script shows progress with timing for each index. Large tables like ngram_significance (3M+ rows) can take 5-10 seconds per index.

### Unicode encoding errors

**Cause**: Windows console encoding issues with special characters

**Solution**: The script has been updated to use ASCII characters only. If you still see errors, redirect output to a file:

```bash
python scripts/maintenance/create_missing_indexes.py > output.txt 2>&1
```

---

## Technical Details

### Index Naming Convention

- `idx_<table>_<purpose>`: General pattern
- `idx_<table>_lookup`: Composite index for common lookups
- `idx_<table>_<column>`: Single column index

### Index Types

- **Single-column**: Fast lookups on one column
- **Composite**: Optimizes queries with multiple WHERE conditions
- **Covering**: Includes all columns needed by query (rare, used for hot paths)

### Index Selection Criteria

Indexes were selected based on:
1. API endpoint query analysis (30+ endpoints)
2. Table size (prioritize large tables)
3. Query frequency (prioritize hot paths)
4. Query patterns (WHERE, ORDER BY, JOIN, GROUP BY)

---

## See Also

- `docs/guides/DATABASE_INDEX_OPTIMIZATION_SUMMARY.md` - Full implementation report
- `docs/guides/DATABASE_MIGRATION_FOR_BACKEND.md` - Database optimization guide
- `docs/reports/DATABASE_STATUS_REPORT.md` - Database status overview
