# Preprocessing Scripts

This directory contains scripts for data preprocessing and analysis.

## Preprocessing Pipeline Scripts

### 1. backup_analysis_tables.py
**Purpose**: Backup existing analysis tables before reprocessing

**Usage**:
```bash
python scripts/backup_analysis_tables.py
```

**Duration**: ~5 minutes

**Output**: Backup tables with `_before_prefix_cleaning` suffix

---

### 2. create_preprocessed_table.py
**Purpose**: Main preprocessing pipeline - creates preprocessed table

**Usage**:
```bash
python scripts/create_preprocessed_table.py
```

**Duration**: ~30-60 minutes

**What it does**:
1. Loads raw village data (285K+ villages)
2. Applies basic text cleaning
3. Removes administrative prefixes
4. Normalizes numbered villages
5. Extracts character sets
6. Creates `广东省自然村_预处理` table

**Expected Output**:
- Preprocessed table with ~285K rows
- Prefix removal rate: 20-40%
- Numbered village rate: 5-15%

---

### 3. create_audit_log.py
**Purpose**: Create detailed audit log for prefix cleaning

**Usage**:
```bash
python scripts/create_audit_log.py
```

**Duration**: ~5 minutes

**Output**: `prefix_cleaning_audit_log` table

**Note**: Run after `create_preprocessed_table.py`

---

### 4. generate_audit_report.py
**Purpose**: Generate comprehensive audit report

**Usage**:
```bash
python scripts/generate_audit_report.py
```

**Duration**: ~5 minutes

**Output**: `docs/PREFIX_CLEANING_AUDIT_REPORT.md`

**Report Sections**:
- Executive Summary
- Removal Rate by City
- Most Common Removed Prefixes
- Match Source Distribution
- Confidence Distribution
- Sample Cases for Review
- Random Sample Verification
- Cross-City Disambiguation Check

---

### 5. validate_preprocessing.py
**Purpose**: Validate preprocessing modules

**Usage**:
```bash
python scripts/validate_preprocessing.py
```

**Duration**: <1 minute

**What it tests**:
- Prefix candidate generation
- Flexible matching
- Conservative removal
- Numbered village normalization
- Integration

---

## Execution Order

For first-time preprocessing:

```bash
# Step 1: Backup (5 min)
python scripts/backup_analysis_tables.py

# Step 2: Preprocess (30-60 min)
python scripts/create_preprocessed_table.py

# Step 3: Audit Log (5 min)
python scripts/create_audit_log.py

# Step 4: Audit Report (5 min)
python scripts/generate_audit_report.py

# Step 5: Review
# Open docs/PREFIX_CLEANING_AUDIT_REPORT.md
```

Total time: ~45-75 minutes

---

## Analysis Pipeline Scripts

### Phase 1: Character Frequency
```bash
python scripts/phase1_frequency_analysis.py
```

### Phase 2: Regional Tendency
```bash
python scripts/phase2_regional_tendency.py
```

### Phase 8: Z-score Normalization
```bash
python scripts/phase8_zscore_normalization.py
```

### Phase 9: Significance Testing
```bash
python scripts/phase9_significance_testing.py
```

---

## Troubleshooting

### Database not found
Check that `data/villages.db` exists:
```bash
ls -lh data/villages.db
```

### Preprocessing takes too long
Expected: 30-60 minutes for 285K villages
If >2 hours: Check system resources

### Low prefix removal rate (<10%)
Review audit report and check:
- Confidence threshold (default: 0.7)
- Match logic parameters
- Data quality

### High prefix removal rate (>60%)
Review random samples in audit report for false positives

---

## Quick Reference

| Script | Duration | Input | Output |
|--------|----------|-------|--------|
| backup_analysis_tables.py | 5 min | Analysis tables | Backup tables |
| create_preprocessed_table.py | 30-60 min | Raw data | Preprocessed table |
| create_audit_log.py | 5 min | Preprocessed table | Audit log |
| generate_audit_report.py | 5 min | Audit log | Audit report |
| validate_preprocessing.py | <1 min | - | Test results |

---

## Documentation

- **Quick Start**: `docs/PREPROCESSING_QUICK_START.md`
- **Technical Details**: `docs/PHASE_0_PREPROCESSING_SUMMARY.md`
- **Implementation Status**: `docs/IMPLEMENTATION_COMPLETE.md`

---

## Support

For detailed documentation, see:
- `docs/` directory
- `.claude/skills/02_preprocessing/` (skill specifications)
- `CLAUDE.md` (project instructions)
