# Pre-Execution Checklist

## Files Modified (9 total)

### Schema Files
- [x] `src/ngram_schema.py` - village_id already present
- [x] `src/semantic_composition_schema.py` - village_id already present

### Preprocessing Scripts
- [x] `scripts/preprocessing/create_preprocessed_table.py`
  - [x] Schema: 行政村 → 村委会
  - [x] Schema: longitude/latitude TEXT → REAL
  - [x] Column names: 行政村 → 村委会
  - [x] Type conversion: Added pd.to_numeric()
  - [x] Index: Updated to use 村委会
  - [x] Input dataframe: Updated column reference

- [x] `scripts/preprocessing/add_village_id_to_main_table.py`
  - [x] Mapping query: p.行政村 → p.村委会

- [x] `src/preprocessing/prefix_cleaner.py`
  - [x] Documentation: 行政村 → 村委会
  - [x] Column access: Supports both 村委会 and 行政村 (backward compat)

### Analysis Scripts
- [x] `scripts/core/populate_village_ngrams.py`
  - [x] Query: 行政村 → 村委会

- [x] `scripts/core/phase14_semantic_composition.py`
  - [x] Query: 行政村 → 村委会

### Pipeline Scripts
- [x] `src/pipelines/feature_materialization_pipeline.py`
  - [x] Query: 行政村 → 村委会
  - [x] Merge columns: Updated
  - [x] Drop columns: Updated

- [x] `src/spatial/coordinate_loader.py`
  - [x] Query: 行政村 → 村委会

## New Files Created (2 total)

- [x] `scripts/preprocessing/execute_plan_b_optimization.py`
  - Automated execution script
  - Progress tracking
  - Error handling

- [x] `docs/guides/PLAN_B_IMPLEMENTATION_SUMMARY.md`
  - Complete implementation documentation
  - Verification queries
  - Rollback plan

## Pre-Execution Checks

### Database Backup
```bash
# Check if backup exists
ls -lh data/villages_backup.db

# If not, create backup
cp data/villages.db data/villages_backup.db
```

### Python Environment
```bash
# Verify Python version
python --version  # Should be 3.x

# Verify required packages
python -c "import pandas, sqlite3, tqdm; print('OK')"
```

### Disk Space
```bash
# Check available disk space (need ~6GB free)
df -h data/
```

### Current Database State
```sql
-- Check current schema
PRAGMA table_info('广东省自然村_预处理');
-- Should show: 行政村 TEXT, longitude TEXT, latitude TEXT

-- Check row count
SELECT COUNT(*) FROM 广东省自然村_预处理;
-- Should be ~285K

-- Check if village_id exists
SELECT COUNT(village_id) FROM 广东省自然村_预处理;
-- May be 0 or NULL if not yet populated
```

## Execution Options

### Option 1: Automated (Recommended)
```bash
python scripts/preprocessing/execute_plan_b_optimization.py
```
- Interactive prompts
- Progress tracking
- Error handling
- Summary report

### Option 2: Manual Step-by-Step
```bash
# Step 1: Regenerate preprocessed table (15-20 min)
python scripts/preprocessing/create_preprocessed_table.py

# Step 2: Add village_id to main table (5 min)
python scripts/preprocessing/add_village_id_to_main_table.py

# Step 3: Regenerate village_ngrams (20-25 min)
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_ngrams;"
python -c "from src.ngram_schema import create_ngram_tables; create_ngram_tables()"
python scripts/core/populate_village_ngrams.py

# Step 4: Regenerate village_semantic_structure (40-50 min)
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_semantic_structure;"
python -c "from src.semantic_composition_schema import create_semantic_composition_tables; create_semantic_composition_tables()"
python scripts/core/phase14_semantic_composition.py

# Step 5: Verify (2 min)
python scripts/verification/verify_village_id.py
```

## Post-Execution Verification

### Quick Checks
```sql
-- 1. Check preprocessed table schema
PRAGMA table_info('广东省自然村_预处理');
-- Expected: 村委会 TEXT, longitude REAL, latitude REAL, village_id TEXT

-- 2. Check coordinate types
SELECT typeof(longitude), typeof(latitude)
FROM 广东省自然村_预处理 LIMIT 1;
-- Expected: real, real

-- 3. Check village_id coverage
SELECT
    COUNT(*) as total,
    COUNT(village_id) as with_id,
    COUNT(village_id) * 100.0 / COUNT(*) as coverage_pct
FROM 广东省自然村_预处理;
-- Expected: ~100% coverage

-- 4. Check village_ngrams
SELECT COUNT(*), COUNT(village_id) FROM village_ngrams;
-- Expected: Both numbers equal

-- 5. Check village_semantic_structure
SELECT COUNT(*), COUNT(village_id) FROM village_semantic_structure;
-- Expected: Both numbers equal
```

### Full Verification
```bash
python scripts/verification/verify_village_id.py
```

## Rollback Plan

If issues occur:

```bash
# Option 1: Restore entire database
cp data/villages_backup.db data/villages.db

# Option 2: Restore specific table
sqlite3 data/villages.db ".dump 广东省自然村_预处理" > backup_prep.sql
sqlite3 data/villages.db < backup_prep.sql
```

## Estimated Timeline

- Step 1: 15-20 min (Preprocessed table)
- Step 2: 5 min (Main table village_id)
- Step 3: 20-25 min (village_ngrams)
- Step 4: 40-50 min (village_semantic_structure)
- Step 5: 2 min (Verification)

**Total: 82-102 minutes (1.5-2 hours)**

## Ready to Execute?

All files have been modified and are ready for execution.

Run:
```bash
python scripts/preprocessing/execute_plan_b_optimization.py
```

Or execute steps manually as shown above.
