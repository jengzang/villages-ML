# Auto-Update active_run_ids Enhancement

**Date:** 2026-02-25
**Status:** ✅ Completed

---

## Summary

Added automatic `active_run_ids` table updates to data generation scripts. Scripts now automatically register their run_id after successful completion, eliminating manual intervention.

---

## Background

### Problem

Previously, after running analysis scripts, developers had to manually update the `active_run_ids` table to register the new run_id. This was:
- Error-prone (easy to forget)
- Time-consuming
- Inconsistent across scripts

### Solution

Integrated `update_active_run_id()` function into data generation scripts. Scripts now automatically:
1. Generate a timestamped run_id
2. Complete their analysis
3. Update `active_run_ids` table
4. Log the update

---

## Implementation

### Modified Scripts

#### 1. Phase 12 N-gram Analysis

**File:** `scripts/core/phase12_ngram_analysis.py`

**Changes:**
```python
# Import run_id manager
from utils.update_run_id import update_active_run_id

def main():
    # Generate run_id
    run_id = f"ngram_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ... perform analysis ...

    # Auto-update active_run_ids (NEW)
    cursor.execute("SELECT COUNT(*) FROM ngram_significance")
    sig_count = cursor.fetchone()[0]

    update_active_run_id(
        analysis_type="ngrams",
        run_id=run_id,
        script_name="phase12_ngram_analysis",
        notes=f"N-gram analysis complete. {sig_count:,} significant n-grams stored.",
        db_path=db_path
    )
```

**Run ID Format:** `ngram_YYYYMMDD_HHMMSS`

**Example:** `ngram_20260225_153045`

#### 2. Semantic Indices Population

**File:** `scripts/core/populate_semantic_indices.py`

**Changes:**
```python
# Import run_id manager
from utils.update_run_id import update_active_run_id

def main():
    # Use user-provided run_id
    run_id = args.output_run_id

    # ... perform analysis ...

    # Auto-update active_run_ids (NEW)
    unique_regions = combined_indices[['region_level', 'region_name']].drop_duplicates()
    region_count = len(unique_regions)

    update_active_run_id(
        analysis_type="semantic_indices",
        run_id=run_id,
        script_name="populate_semantic_indices",
        notes=f"Semantic indices calculated for {region_count} regions.",
        db_path=args.db_path
    )
```

**Run ID Format:** User-specified (e.g., `semantic_indices_002`)

---

## How It Works

### RunIDManager System

The system uses a centralized `RunIDManager` class:

**Location:** `api/run_id_manager.py`

**Key Features:**
1. **Validation:** Verifies run_id exists in target table
2. **Auto-fallback:** Uses latest run_id if configured one doesn't exist
3. **Caching:** In-memory cache for fast lookups
4. **Tracking:** Records who updated and when

### Update Function

**Location:** `scripts/utils/update_run_id.py`

**Function:** `update_active_run_id()`

**Parameters:**
- `analysis_type` - Type identifier (e.g., "ngrams", "semantic_indices")
- `run_id` - New run_id to register
- `script_name` - Script name (auto-detected if not provided)
- `notes` - Optional description
- `db_path` - Database path (default: "data/villages.db")

**Example:**
```python
update_active_run_id(
    analysis_type="ngrams",
    run_id="ngram_20260225_153045",
    notes="Analysis complete with 2.3M significant n-grams"
)
```

---

## active_run_ids Table

### Schema

```sql
CREATE TABLE active_run_ids (
    analysis_type TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    updated_at REAL,
    updated_by TEXT,
    notes TEXT
);
```

### Current Entries

| analysis_type | table_name | Description |
|---------------|------------|-------------|
| ngrams | village_ngrams | N-gram patterns |
| semantic_indices | semantic_indices | Regional semantic indices |
| char_frequency | char_frequency_global | Character frequency |
| char_embeddings | char_embeddings | Character embeddings |
| char_significance | tendency_significance | Character significance |
| clustering_county | cluster_assignments | County clustering |
| patterns | pattern_tendency | Pattern tendency |
| semantic | semantic_labels | Semantic labels |
| spatial_hotspots | spatial_hotspots | Spatial hotspots |
| spatial_integration | spatial_tendency_integration | Spatial integration |
| village_features | village_features | Village features |

---

## Benefits

### For Developers

**Before:**
```bash
# Run analysis
python scripts/core/phase12_ngram_analysis.py

# Manually update active_run_ids
python scripts/utils/update_run_id.py --analysis-type ngrams --run-id ngram_xxx

# Easy to forget!
```

**After:**
```bash
# Run analysis (auto-updates active_run_ids)
python scripts/core/phase12_ngram_analysis.py

# Done! ✓
```

### For System

- **Consistency:** All scripts follow same pattern
- **Traceability:** Automatic logging of updates
- **Reliability:** No manual steps to forget
- **Auditability:** Track who/when/why updates happened

---

## Usage Examples

### Example 1: Phase 12 N-gram Analysis

```bash
python scripts/core/phase12_ngram_analysis.py
```

**Output:**
```
======================================================================
Phase 12: N-gram Structure Analysis
======================================================================
Database: data/villages.db
Start time: 2026-02-25 15:30:45
Run ID: ngram_20260225_153045

... (analysis steps) ...

======================================================================
Updating active_run_ids...
======================================================================
✓ 已自动更新 ngrams 的活跃 run_id 为: ngram_20260225_153045
✓ 成功更新 ngrams 的活跃 run_id
```

### Example 2: Semantic Indices

```bash
python scripts/core/populate_semantic_indices.py --output-run-id semantic_indices_002
```

**Output:**
```
=== Step 5: Writing to database ===
Saved 14,292 semantic indices records for run_id=semantic_indices_002

=== Step 6: Updating active_run_ids ===
✓ 已自动更新 semantic_indices 的活跃 run_id 为: semantic_indices_002
✓ 成功更新 semantic_indices 的活跃 run_id

=== Completed in 245.32s ===
```

---

## Verification

### Check Current active_run_ids

```python
import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT analysis_type, run_id, updated_by, notes
    FROM active_run_ids
    WHERE analysis_type IN ('ngrams', 'semantic_indices')
""")

for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")
    print(f"  Updated by: {row[2]}")
    print(f"  Notes: {row[3]}")
```

### Check Update History

```python
# View recent updates
cursor.execute("""
    SELECT analysis_type, run_id,
           datetime(updated_at, 'unixepoch', 'localtime') as updated_time,
           updated_by
    FROM active_run_ids
    ORDER BY updated_at DESC
    LIMIT 10
""")
```

---

## Future Scripts to Update

### Recommended

These scripts should also be updated to auto-register run_ids:

1. **Phase 1:** `scripts/core/phase01_embeddings.py`
   - Analysis type: `char_embeddings`

2. **Phase 4:** `scripts/core/phase04_spatial_analysis.py`
   - Analysis type: `spatial_hotspots`

3. **Phase 6:** `scripts/core/phase06_clustering.py`
   - Analysis type: `clustering_county`

4. **Phase 8-10:** Character analysis scripts
   - Analysis types: `char_frequency`, `char_significance`

### Implementation Pattern

```python
# At the top of the script
from utils.update_run_id import update_active_run_id

# In main() function, after analysis completes
def main():
    # Generate or use provided run_id
    run_id = f"{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ... perform analysis ...

    # Auto-update active_run_ids
    update_active_run_id(
        analysis_type="your_analysis_type",
        run_id=run_id,
        notes="Brief description of what was done"
    )
```

---

## Error Handling

### If Update Fails

The script will print a warning but **not fail**:

```
✗ 更新活跃 run_id 失败: 分析类型 'unknown_type' 不存在于 active_run_ids 表中
```

**Reason:** Analysis data is already saved. The update is a convenience feature.

### Manual Update (If Needed)

```python
from scripts.utils.update_run_id import update_active_run_id

update_active_run_id(
    analysis_type="ngrams",
    run_id="ngram_20260225_153045",
    notes="Manual update after script completion"
)
```

---

## Testing

### Test Script

```python
# Test auto-update functionality
from scripts.utils.update_run_id import update_active_run_id

# Test update
success = update_active_run_id(
    analysis_type="ngrams",
    run_id="test_run_20260225",
    script_name="test_script",
    notes="Testing auto-update feature"
)

if success:
    print("✓ Test passed")
else:
    print("✗ Test failed")
```

### Verify Update

```python
import sqlite3

conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT run_id, updated_by, notes
    FROM active_run_ids
    WHERE analysis_type = 'ngrams'
""")

print(cursor.fetchone())
```

---

## Files Modified

1. `scripts/core/phase12_ngram_analysis.py`
   - Added auto-update for ngrams

2. `scripts/core/populate_semantic_indices.py`
   - Added auto-update for semantic_indices

3. `docs/reports/AUTO_UPDATE_RUN_IDS.md`
   - This documentation (NEW)

---

## Migration Notes

### For Existing Scripts

**No breaking changes!**

- Scripts without auto-update continue to work
- Manual updates still supported
- Gradual migration recommended

### For New Scripts

**Always include auto-update:**

```python
# Template for new analysis scripts
from utils.update_run_id import update_active_run_id

def main():
    run_id = generate_run_id()

    # ... analysis code ...

    # Auto-update (REQUIRED for new scripts)
    update_active_run_id(
        analysis_type="your_type",
        run_id=run_id,
        notes="Description"
    )
```

---

## Summary

✅ **Phase 12 (ngrams):** Auto-updates after n-gram analysis
✅ **Semantic Indices:** Auto-updates after index calculation
✅ **No manual intervention:** Fully automated
✅ **Backward compatible:** Existing workflows unaffected
✅ **Extensible:** Easy to add to other scripts

**Next Steps:**
1. Monitor auto-updates in production
2. Gradually add to remaining analysis scripts
3. Consider adding to API compute endpoints

---

**Report Generated:** 2026-02-25
**Status:** ✅ Production Ready
**Impact:** Eliminates manual run_id management
