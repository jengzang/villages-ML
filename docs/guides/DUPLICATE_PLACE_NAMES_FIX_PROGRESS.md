# Duplicate Place Names Fix - Implementation Progress

## Overview

This document tracks the implementation of the fix for duplicate place names handling in the villages-ML database.

**Problem**: Place names like "太平镇" appear in multiple locations (7 different cities/counties), but the system merges them into single records, making it impossible to distinguish between different locations.

**Solution**: Add hierarchical columns (city, county, township) to all regional analysis tables to properly separate duplicate place names.

---

## Implementation Status

### ✅ Phase 1: Schema Updates (COMPLETED)

**Files Modified**:

1. **`src/ngram_schema.py`** ✅
   - Updated `regional_ngram_frequency` table schema
   - Updated `ngram_tendency` table schema
   - Updated `ngram_significance` table schema
   - Added hierarchical columns: `city`, `county`, `township`
   - Updated PRIMARY KEY to use hierarchical columns
   - Added indexes for hierarchical columns

2. **`scripts/maintenance/create_optimized_schema.py`** ✅
   - Updated `char_regional_analysis` table schema
   - Updated `pattern_regional_analysis` table schema
   - Updated `semantic_regional_analysis` table schema
   - Added hierarchical columns: `city`, `county`, `township`
   - Updated PRIMARY KEY to use hierarchical columns

**New Files Created**:

3. **`scripts/maintenance/drop_regional_tables.py`** ✅
   - Script to drop existing regional tables before regeneration
   - Drops 6 tables: char_regional_analysis, semantic_regional_analysis, pattern_regional_analysis, ngram_tendency, ngram_significance, regional_ngram_frequency

4. **`scripts/verification/verify_duplicate_handling.py`** ✅
   - Verification script to test the fix
   - Checks if "太平镇" is properly separated into 7 records
   - Verifies schema structure
   - Compares counts with main table

---

### ⏳ Phase 2: Data Generation Script Refactoring (TODO)

**Files to Modify**:

1. **`src/pipelines/frequency_pipeline.py`** ⏳
   - Update to keep city/county/township columns when loading village data
   - Group by hierarchical key instead of region_name only
   - Write hierarchical columns to database

2. **`src/semantic/vtf_calculator.py`** ⏳
   - Update `calculate_regional_vtf()` method (lines 76-147)
   - Group by hierarchical key (city, county, township)
   - Pass hierarchical columns to database writer

3. **`scripts/core/phase12_ngram_analysis.py`** ⏳
   - Include city/county/township columns when loading village data
   - Group by hierarchical key when calculating regional n-gram frequency
   - Write hierarchical columns to database

4. **`scripts/core/run_morphology_analysis.py`** ⏳
   - Similar updates to frequency pipeline
   - Group by hierarchical key
   - Write hierarchical columns to database

5. **`src/data/db_writer.py`** ⏳
   - Update all `write_*_regional()` functions
   - Add city/county/township parameters
   - Update INSERT statements to include hierarchical columns

**Key Pattern for All Scripts**:
```python
# Before
def calculate_regional_frequency(villages_df, level):
    regional_df = villages_df.groupby([level, 'region_name']).agg(...)

# After
def calculate_regional_frequency(villages_df, level):
    group_cols = ['市级', '区县级', '乡镇级', level]
    regional_df = villages_df.groupby(group_cols).agg(...)

    # Rename columns for database
    regional_df = regional_df.rename(columns={
        '市级': 'city',
        '区县级': 'county',
        '乡镇级': 'township',
        level: 'region_name'
    })
```

---

### ⏳ Phase 3: API Updates (TODO)

**Files to Modify** (15+ endpoint files):

1. **`api/semantic/category.py`** ⏳
2. **`api/character/frequency.py`** ⏳
3. **`api/character/tendency.py`** ⏳
4. **`api/ngrams/frequency.py`** ⏳
5. **`api/ngrams/tendency.py`** ⏳
6. **`api/patterns/frequency.py`** ⏳
7. **`api/patterns/tendency.py`** ⏳
8. ... (8+ more endpoint files)

**Key Pattern for All Endpoints**:
```python
# Before
@router.get("/regional")
def get_regional_data(
    region_level: str,
    region_name: str,
    ...
):
    query = "SELECT * FROM table WHERE region_name = ?"
    params = [region_name]

# After
@router.get("/regional")
def get_regional_data(
    region_level: str,
    region_name: str = None,  # Optional, for backward compatibility
    city: str = None,         # NEW
    county: str = None,       # NEW
    township: str = None,     # NEW
    ...
):
    query = "SELECT * FROM table WHERE 1=1"
    params = []

    # Add hierarchical filters
    if city:
        query += " AND city = ?"
        params.append(city)
    if county:
        query += " AND county = ?"
        params.append(county)
    if township:
        query += " AND township = ?"
        params.append(township)

    # Backward compatibility
    if region_name:
        query += " AND region_name = ?"
        params.append(region_name)
```

---

### ⏳ Phase 4: Data Regeneration (TODO)

**Scripts to Run** (in order):

1. **Drop existing tables** ⏳
   ```bash
   python scripts/maintenance/drop_regional_tables.py
   ```

2. **Regenerate character frequency & tendency** ⏳
   ```bash
   python scripts/core/run_frequency_analysis.py
   python scripts/core/run_tendency_with_significance.py
   ```

3. **Regenerate semantic VTF** ⏳
   ```bash
   python scripts/core/run_semantic_analysis.py
   ```

4. **Regenerate n-gram analysis** ⏳
   ```bash
   python scripts/core/phase12_ngram_analysis.py
   ```

5. **Regenerate pattern analysis** ⏳
   ```bash
   python scripts/core/run_morphology_analysis.py
   ```

**Estimated Time**: 2-4 hours

---

### ⏳ Phase 5: Verification (TODO)

**Steps**:

1. **Run verification script** ⏳
   ```bash
   python scripts/verification/verify_duplicate_handling.py
   ```

2. **Test SQL queries** ⏳
   ```sql
   SELECT city, county, township, region_name, COUNT(*) as char_count
   FROM char_regional_analysis
   WHERE region_level = 'township' AND region_name = '太平镇'
   GROUP BY city, county, township, region_name;
   ```
   **Expected**: 7 rows (one for each location)

3. **Test API endpoints** ⏳
   ```bash
   # Should return data for specific location
   curl "http://localhost:5000/api/semantic/category/vtf/regional?region_level=township&city=清远市&county=清新区&township=太平镇"

   # Should return data for all 7 locations
   curl "http://localhost:5000/api/semantic/category/vtf/regional?region_level=township&region_name=太平镇"
   ```

---

## Next Steps

1. **Immediate**: Complete Phase 2 (Data Generation Script Refactoring)
   - Start with `src/pipelines/frequency_pipeline.py`
   - Then update `src/semantic/vtf_calculator.py`
   - Update database writers in `src/data/db_writer.py`

2. **After Phase 2**: Complete Phase 3 (API Updates)
   - Update all endpoint files to accept hierarchical parameters
   - Maintain backward compatibility

3. **After Phase 3**: Execute Phase 4 (Data Regeneration)
   - Drop old tables
   - Regenerate all regional analysis data

4. **Final**: Execute Phase 5 (Verification)
   - Run verification script
   - Test API endpoints
   - Confirm fix works correctly

---

## Estimated Timeline

- **Phase 1 (Schema Updates)**: ✅ COMPLETED
- **Phase 2 (Script Refactoring)**: 6-8 hours
- **Phase 3 (API Updates)**: 6-8 hours
- **Phase 4 (Data Regeneration)**: 2-4 hours
- **Phase 5 (Verification)**: 2-3 hours

**Total Estimated Time**: 16-23 hours (2-3 days)

---

## Critical Files Summary

### Modified Files (Phase 1):
- `src/ngram_schema.py` - N-gram table schemas
- `scripts/maintenance/create_optimized_schema.py` - Optimized table schemas

### New Files (Phase 1):
- `scripts/maintenance/drop_regional_tables.py` - Drop tables script
- `scripts/verification/verify_duplicate_handling.py` - Verification script

### Files to Modify (Phase 2):
- `src/pipelines/frequency_pipeline.py` - Character frequency calculation
- `src/semantic/vtf_calculator.py` - Semantic VTF calculation
- `scripts/core/phase12_ngram_analysis.py` - N-gram analysis
- `scripts/core/run_morphology_analysis.py` - Pattern analysis
- `src/data/db_writer.py` - Database write functions

### Files to Modify (Phase 3):
- 15+ API endpoint files in `api/` directory

---

## Testing Checklist

- [ ] Schema verification: All tables have city/county/township columns
- [ ] Data verification: "太平镇" has 7 separate records
- [ ] Count verification: Total villages match main table
- [ ] API verification: Hierarchical parameters work correctly
- [ ] Backward compatibility: region_name parameter still works
- [ ] Performance verification: Queries run efficiently with new indexes

---

## Rollback Plan

If issues occur:

1. **Backup database** before dropping tables
2. **Keep old schema files** for reference
3. **Document all changes** for easy rollback
4. **Test on copy of database** first

---

## Notes

- All schema changes maintain backward compatibility by keeping `region_name` column
- Hierarchical columns (city, county, township) are nullable to support different region levels
- PRIMARY KEY uses all hierarchical columns to ensure uniqueness
- Indexes added for all hierarchical columns to maintain query performance

---

**Last Updated**: 2026-02-24
**Status**: Phase 1 Complete, Phase 2-5 Pending
