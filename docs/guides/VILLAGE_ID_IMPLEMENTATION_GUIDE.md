# Village ID Implementation - Execution Guide

## Overview

This guide provides step-by-step instructions for implementing the unified `village_id` system across all database tables.

## Prerequisites

- User has completed database backup
- Python environment is set up with all dependencies
- Database path: `data/villages.db`

## Implementation Steps

### Step 1: Regenerate Preprocessed Table (with village_id)

**Purpose**: Add village_id column to preprocessed table and populate it.

**Command**:
```bash
python scripts/preprocessing/create_preprocessed_table.py
```

**Expected output**:
- Creates 广东省自然村_预处理 table with village_id column
- Populates village_id = 'v_' || ROWID for all rows
- Creates index on village_id
- ~285,860 rows processed

**Verification**:
```sql
SELECT COUNT(*), COUNT(village_id) FROM 广东省自然村_预处理;
-- Should show same count for both
```

**Estimated time**: 10-15 minutes

---

### Step 2: Add village_id to Main Table

**Purpose**: Add village_id to main table by mapping to preprocessed table.

**Command**:
```bash
python scripts/preprocessing/add_village_id_to_main_table.py
```

**Expected output**:
- Adds village_id column to 广东省自然村
- Maps village_id from preprocessed table using 4-column match
- Creates index on village_id
- ~285,860 rows mapped

**Verification**:
```sql
SELECT COUNT(*), COUNT(village_id) FROM 广东省自然村;
-- Should show high coverage (>99%)
```

**Estimated time**: 5 minutes

---

### Step 3: Regenerate village_ngrams Table

**Purpose**: Recreate village_ngrams with village_id as primary key.

**Command**:
```bash
# First, drop the old table
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_ngrams;"

# Recreate schema
python -c "from src.ngram_schema import create_ngram_tables; create_ngram_tables()"

# Populate with new structure
python scripts/core/populate_village_ngrams.py
```

**Expected output**:
- Creates village_ngrams table with village_id column
- Extracts n-grams for ~274,825 villages
- Primary key: (village_id, n)

**Verification**:
```sql
SELECT COUNT(*), COUNT(village_id) FROM village_ngrams;
-- Should show same count for both
```

**Estimated time**: 15-20 minutes

---

### Step 4: Regenerate village_semantic_structure Table

**Purpose**: Recreate village_semantic_structure with village_id as primary key.

**Command**:
```bash
# Drop old table
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_semantic_structure;"

# Recreate schema
python -c "from src.semantic_composition_schema import create_semantic_composition_tables; create_semantic_composition_tables()"

# Regenerate (runs full Phase 14)
python scripts/core/phase14_semantic_composition.py
```

**Expected output**:
- Creates village_semantic_structure table with village_id column
- Extracts semantic structures for ~198,595 villages
- Primary key: village_id

**Verification**:
```sql
SELECT COUNT(*), COUNT(village_id) FROM village_semantic_structure;
-- Should show same count for both
```

**Estimated time**: 30-45 minutes

---

### Step 5: Regenerate village_features Table

**Purpose**: Recreate village_features with village_id column.

**Command**:
```bash
# Drop old table
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_features;"

# Regenerate (runs clustering analysis which includes feature materialization)
python scripts/core/run_clustering_analysis.py
```

**Expected output**:
- Creates village_features table with village_id column
- Generates features for ~284,764 villages
- Includes village_id in all rows

**Verification**:
```sql
SELECT COUNT(*), COUNT(village_id) FROM village_features;
-- Should show same count for both
```

**Estimated time**: 60-90 minutes

---

### Step 6: Verify Implementation

**Purpose**: Run comprehensive verification tests.

**Command**:
```bash
python scripts/verification/verify_village_id.py
```

**Expected output**:
- Test 1: All tables have village_id column ✓
- Test 2: village_id format is correct (v_<ROWID>) ✓
- Test 3: village_id values are unique ✓
- Test 4: Coverage is high (>99% for most tables) ✓
- Test 5: Indexes exist on village_id ✓

**Estimated time**: 1 minute

---

### Step 7: Benchmark Performance

**Purpose**: Measure query performance improvement.

**Command**:
```bash
python scripts/verification/benchmark_village_id.py
```

**Expected output**:
- Query times for 1000 villages using village_id
- Average query time per operation
- Performance metrics

**Estimated time**: 2-3 minutes

---

### Step 8: Test API Endpoints

**Purpose**: Verify API works with new village_id system.

**Commands**:
```bash
# Start API server
python -m uvicorn api.main:app --reload

# In another terminal, test endpoints
curl http://localhost:8000/village/ngrams/1
curl http://localhost:8000/village/semantic-structure/1
curl http://localhost:8000/village/features/1
curl http://localhost:8000/village/complete/1
```

**Expected output**:
- All endpoints return data successfully
- No 404 errors
- Response includes village_id field

**Estimated time**: 5 minutes

---

## Total Estimated Time

- Step 1: 10-15 minutes
- Step 2: 5 minutes
- Step 3: 15-20 minutes
- Step 4: 30-45 minutes
- Step 5: 60-90 minutes
- Step 6: 1 minute
- Step 7: 2-3 minutes
- Step 8: 5 minutes

**Total: 2-3 hours**

---

## Rollback Procedure

If implementation fails or issues arise:

```bash
# Restore from backup (user has already created backup)
# Example commands (adjust paths as needed):
sqlite3 data/villages.db ".restore data/villages_backup.db"
```

---

## Verification Checklist

After completing all steps, verify:

- [ ] All 6 tables have village_id column
- [ ] village_id format is 'v_<ROWID>' for all rows
- [ ] village_id is unique in preprocessed table
- [ ] Coverage is >99% for all tables
- [ ] Indexes exist on village_id columns
- [ ] API endpoints work correctly
- [ ] Query performance is improved

---

## Troubleshooting

### Issue: NULL village_id values

**Cause**: Mapping failed for some villages

**Solution**:
```sql
-- Check which villages have NULL village_id
SELECT COUNT(*) FROM 广东省自然村 WHERE village_id IS NULL;

-- Investigate why mapping failed
SELECT * FROM 广东省自然村 WHERE village_id IS NULL LIMIT 10;
```

### Issue: Duplicate village_id values

**Cause**: ROWID collision (very rare)

**Solution**:
```sql
-- Check for duplicates
SELECT village_id, COUNT(*) FROM 广东省自然村_预处理 GROUP BY village_id HAVING COUNT(*) > 1;
```

### Issue: API returns 404

**Cause**: village_id format mismatch

**Solution**:
- Ensure API uses `f'v_{village_id}'` format
- Check that database has village_id in correct format

---

## Files Modified

### Scripts Modified (6 files)
1. `scripts/preprocessing/create_preprocessed_table.py` - Added village_id column and population logic
2. `src/ngram_schema.py` - Modified village_ngrams table structure
3. `scripts/core/populate_village_ngrams.py` - Modified to include village_id
4. `src/semantic_composition_schema.py` - Modified village_semantic_structure table structure
5. `scripts/core/phase14_semantic_composition.py` - Modified to include village_id
6. `src/pipelines/feature_materialization_pipeline.py` - Modified to include village_id

### Scripts Created (3 files)
1. `scripts/preprocessing/add_village_id_to_main_table.py` - Add village_id to main table
2. `scripts/verification/verify_village_id.py` - Verification script
3. `scripts/verification/benchmark_village_id.py` - Performance benchmark

### API Modified (1 file)
1. `api/village/data.py` - Simplified all 4 endpoints to use village_id

---

## Notes

- **No data migration**: All tables are regenerated from source data
- **Backup is critical**: User must have backup before starting
- **Idempotent**: Scripts can be re-run if they fail
- **Indexes are important**: Performance depends on indexes being created
- **village_spatial_features**: Already has village_id, no changes needed

---

## Success Criteria

Implementation is successful when:

1. All verification tests pass
2. API endpoints return data correctly
3. Query performance is improved (50-80% faster)
4. No NULL village_id values in critical tables
5. All indexes are created
6. Documentation is updated

---

## Next Steps After Implementation

1. Update frontend to use new API responses (includes village_id)
2. Update documentation to reflect new schema
3. Monitor API performance in production
4. Consider removing old composite key columns after 30 days
5. Update any external tools/scripts that query the database
