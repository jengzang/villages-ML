# Phase 0: Data Preprocessing Implementation Summary

## Overview

This document describes the comprehensive data preprocessing implementation for the villages-ML project. The preprocessing pipeline addresses two critical data quality issues:

1. **Administrative Prefix Removal**: Removes redundant administrative village prefixes from natural village names
2. **Numbered Village Normalization**: Normalizes villages with trailing Chinese numeral suffixes for statistical aggregation

## Implementation Status

✅ **COMPLETED** - All modules, scripts, and tests implemented

## Architecture

### Two-Phase Design

The preprocessing follows the project's two-phase architecture:

**Phase 1: Offline Preprocessing (Current)**
- Heavy computation allowed
- Full dataset processing (285K+ villages)
- Results stored in database
- Execution time: ~30-60 minutes

**Phase 2: Online API (Future)**
- Loads precomputed results only
- No runtime preprocessing
- Fast queries (<1 second)

### Data Flow

```
Raw Data (广东省自然村)
  ↓
Basic Text Cleaning (brackets, noise)
  ↓
Administrative Prefix Removal
  ↓
Numbered Village Normalization
  ↓
Character Set Extraction
  ↓
Preprocessed Table (广东省自然村_预处理)
  ↓
Analysis Pipelines (Phase 1-14)
```

## Module Descriptions

### 1. prefix_cleaner.py

**Location**: `src/preprocessing/prefix_cleaner.py`

**Purpose**: Detect and remove redundant administrative village prefixes

**Key Functions**:
- `generate_prefix_candidates()` - Split-first parsing to generate prefix candidates
- `flexible_match()` - Flexible matching with/without "村" suffix
- `remove_prefix_conservative()` - Conservative prefix removal (only at beginning)
- `remove_administrative_prefix()` - Main prefix removal logic
- `batch_clean_prefixes()` - Batch processing for all villages

**Algorithm**:
1. **Step 0**: Length guard (skip if ≤3 characters)
2. **Step 1**: Generate prefix candidates (2-3 char fixed length + delimiter-based)
3. **Step 2**: Match and validate
   - Priority 1: Same-row admin village (confidence 0.9-1.0)
   - Priority 2: Same township search (confidence 0.7)
   - Priority 3: Same county search (confidence 0.5)
4. **Step 3**: Conservative removal (only if confidence ≥0.7)

**Design Principles**:
- Split-first parsing (parse before matching)
- Conservative behavior (prefer false negatives over false positives)
- Explainable edits (all operations auditable)

**Examples**:
- "石岭村上村" + admin="石岭村" → "上村" (exact match, conf=1.0)
- "龙岗村新村" + admin="龙岗" → "村新村" (normalized match, conf=0.95)
- "葵山土头村" + admin="葵山村" → "土头村" (partial match, conf=0.95)
- "魁头三角村" + admin="魁头村" → "三角村" (no delimiter, conf=0.95)

### 2. numbered_village_normalizer.py

**Location**: `src/preprocessing/numbered_village_normalizer.py`

**Purpose**: Normalize villages with trailing Chinese numeral suffixes

**Key Functions**:
- `detect_trailing_numeral()` - Detect trailing Chinese numerals
- `normalize_numbered_village()` - Remove numeral suffix for aggregation

**Patterns Detected**:
- Pattern 1: 村名 + 数字 + 村 (e.g., "东村一村" → "东村")
- Pattern 2: 村名 + 数字 (e.g., "南岭二" → "南岭")

**Design Principles**:
- Non-destructive (database never modified)
- Statistical-layer normalization only
- Prevents artificial village count inflation

**Examples**:
- "东村一村" → "东村"
- "东村二村" → "东村"
- "南岭一" → "南岭"
- "南岭二" → "南岭"

### 3. text_cleaner.py (Existing)

**Location**: `src/preprocessing/text_cleaner.py`

**Purpose**: Basic text cleaning (brackets, noise, non-Chinese characters)

**Already Implemented** - No changes needed

## Database Schema

### Preprocessed Table: 广东省自然村_预处理

**Original Fields** (copied from main table):
- 市级, 区县级, 乡镇级, 行政村, 自然村
- 拼音, 语言分布, longitude, latitude
- 备注, 更新时间, 数据来源

**Preprocessing Fields**:
- `自然村_基础清洗` TEXT - After basic cleaning
- `自然村_去前缀` TEXT - After prefix removal
- `自然村_规范化` TEXT - After numbered village normalization
- `字符集` TEXT - JSON array of unique characters
- `字符数量` INTEGER - Number of unique characters

**Metadata Fields**:
- `有括号` INTEGER (0/1) - Had brackets
- `有噪音` INTEGER (0/1) - Had noise
- `有前缀` INTEGER (0/1) - Had prefix removed
- `去除的前缀` TEXT - Removed prefix
- `前缀匹配来源` TEXT - Match source
- `前缀置信度` REAL - Confidence score
- `有编号后缀` INTEGER (0/1) - Had numeral suffix
- `编号后缀` TEXT - Numeral suffix

**Validity Fields**:
- `有效` INTEGER (0/1) - Is valid
- `无效原因` TEXT - Invalid reason

**Indexes**:
- idx_prep_city, idx_prep_county, idx_prep_township
- idx_prep_admin, idx_prep_prefix, idx_prep_valid

### Audit Log Table: prefix_cleaning_audit_log

**Purpose**: Detailed audit trail for all prefix cleaning operations

**Fields**:
- Geographic hierarchy (市级, 区县级, 乡镇级, 行政村)
- Cleaning information (原始, 基础清洗, 去前缀)
- Prefix information (检测到前缀, 前缀候选, 去除的前缀, 剩余部分)
- Match information (匹配来源, 匹配的行政村, 规则置信度, 最终置信度)
- Decision information (是否去除, 需要人工审核)
- Timestamp (处理时间)

**Indexes**:
- idx_audit_city, idx_audit_removed
- idx_audit_review, idx_audit_confidence

## Scripts

### 1. backup_analysis_tables.py

**Purpose**: Backup existing analysis tables before reprocessing

**Tables Backed Up**:
- character_frequency
- regional_character_frequency
- character_tendency
- character_tendency_zscore
- character_significance

**Backup Suffix**: `_before_prefix_cleaning`

**Usage**:
```bash
python scripts/backup_analysis_tables.py
```

### 2. create_preprocessed_table.py

**Purpose**: Main preprocessing pipeline - creates preprocessed table

**Steps**:
1. Load raw village data
2. Apply basic text cleaning
3. Apply administrative prefix removal
4. Apply numbered village normalization
5. Extract character sets
6. Write to preprocessed table

**Usage**:
```bash
python scripts/create_preprocessed_table.py
```

**Expected Output**:
- Preprocessed table with ~285K rows
- Prefix removal rate: 20-40%
- Numbered village rate: 5-15%
- Execution time: 30-60 minutes

### 3. create_audit_log.py

**Purpose**: Create and populate audit log table

**Usage**:
```bash
python scripts/create_audit_log.py
```

### 4. generate_audit_report.py

**Purpose**: Generate comprehensive audit report

**Report Sections**:
1. Executive Summary
2. Removal Rate by City
3. Most Common Removed Prefixes (Top 50)
4. Match Source Distribution
5. Confidence Distribution
6. Sample Cases for Review (Top 20)
7. Random Sample Verification (100 cases)
8. Cross-City Disambiguation Check

**Output**: `docs/PREFIX_CLEANING_AUDIT_REPORT.md`

**Usage**:
```bash
python scripts/generate_audit_report.py
```

## Testing

### Unit Tests

**test_prefix_cleaner.py**:
- TestGeneratePrefixCandidates
- TestFlexibleMatch
- TestRemovePrefixConservative
- TestRemoveAdministrativePrefix
- TestEdgeCases

**test_numbered_village_normalizer.py**:
- TestDetectTrailingNumeral
- TestNormalizeNumberedVillage
- TestEdgeCases

**Run Tests**:
```bash
pytest tests/unit/test_prefix_cleaner.py -v
pytest tests/unit/test_numbered_village_normalizer.py -v
```

## Execution Plan

### Step 1: Backup (5 minutes)
```bash
python scripts/backup_analysis_tables.py
```

### Step 2: Create Preprocessed Table (30-60 minutes)
```bash
python scripts/create_preprocessed_table.py
```

### Step 3: Create Audit Log (5 minutes)
```bash
python scripts/create_audit_log.py
```

### Step 4: Generate Audit Report (5 minutes)
```bash
python scripts/generate_audit_report.py
```

### Step 5: Review Results
- Review `docs/PREFIX_CLEANING_AUDIT_REPORT.md`
- Verify random samples
- Check confidence distribution
- Identify cases needing manual review

### Step 6: Rerun Analysis (30 minutes)
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

### Step 7: Generate Impact Report
```bash
python scripts/compare_before_after_prefix_cleaning.py
```

## Verification Checklist

### Implementation Verification
- [x] prefix_cleaner.py module implemented
- [x] numbered_village_normalizer.py module implemented
- [x] Unit tests created (coverage target: >80%)
- [x] Backup script created
- [x] Preprocessing pipeline script created
- [x] Audit log script created
- [x] Audit report script created

### Execution Verification
- [ ] Backup tables created successfully
- [ ] Preprocessed table created (285K rows)
- [ ] Prefix removal rate in expected range (20-40%)
- [ ] Audit log populated
- [ ] Audit report generated
- [ ] Random sample verification (>99% accuracy)

### Analysis Verification
- [ ] Phase 1-3 rerun completed
- [ ] Character frequency tables updated
- [ ] Regional tendency tables updated
- [ ] Statistical significance tables updated
- [ ] Impact report generated

### Documentation Verification
- [x] Phase 0 summary created
- [ ] PROJECT_STATUS.md updated
- [ ] MEMORY.md updated (if needed)

## Expected Impact

### Character Frequency Analysis
- **Expected**: Reduction in frequency of common administrative characters
- **Example**: "村", "岭", "石" frequencies should decrease
- **Magnitude**: 10-30% reduction for high-frequency admin characters

### Regional Tendency Analysis
- **Expected**: More accurate regional tendency values
- **Reason**: Removal of artificial frequency inflation from prefixes
- **Impact**: Better identification of truly region-specific characters

### Clustering Analysis
- **Expected**: Improved cluster quality
- **Reason**: Morphological features no longer contaminated by prefixes
- **Impact**: More semantically meaningful clusters

### Statistical Significance
- **Expected**: More accurate p-values
- **Reason**: Removal of systematic bias from prefix characters
- **Impact**: Better identification of statistically significant patterns

## Known Limitations

1. **Confidence Threshold**: Set at 0.7 - may need adjustment based on results
2. **Delimiter Detection**: Limited to common delimiters (村, 寨, 坊, etc.)
3. **Prefix Length**: Limited to 2-3 characters - may miss longer prefixes
4. **Cross-City Disambiguation**: Relies on geographic hierarchy - may have edge cases
5. **Numbered Village Patterns**: Only detects trailing numerals - may miss other patterns

## Future Enhancements

1. **LLM-Assisted Validation**: Use LLM for low-confidence cases
2. **Adaptive Confidence Threshold**: Adjust threshold based on match source
3. **Extended Delimiter Set**: Add more regional delimiter variations
4. **Longer Prefix Detection**: Support 4+ character prefixes
5. **Interactive Review Tool**: Web interface for manual review of flagged cases

## References

- Skill Specification: `.claude/skills/02_preprocessing/administrative_prefix_cleaning.md`
- Skill Specification: `.claude/skills/02_preprocessing/numbered_village_normalization.md`
- Project Instructions: `CLAUDE.md`
- Project Status: `docs/PROJECT_STATUS.md`

## Changelog

- 2026-02-19: Initial implementation completed
  - Created prefix_cleaner.py module
  - Created numbered_village_normalizer.py module
  - Created preprocessing pipeline scripts
  - Created audit log and reporting scripts
  - Created comprehensive unit tests
  - Created documentation
