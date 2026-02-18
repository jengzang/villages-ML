# Preprocessing Implementation - Execution Guide

## Quick Start

The preprocessing system is **fully implemented and ready to execute**. All code, tests, and documentation are complete.

## Execute Preprocessing (Choose One)

### Option A: Automated (Recommended)

**Windows**:
```cmd
run_preprocessing.bat
```

**Linux/Mac/Cygwin**:
```bash
bash run_preprocessing.sh
```

### Option B: Manual Steps

```bash
# 1. Backup (5 min)
python scripts/backup_analysis_tables.py

# 2. Preprocess (30-60 min)
python scripts/create_preprocessed_table.py

# 3. Audit Log (5 min)
python scripts/create_audit_log.py

# 4. Audit Report (5 min)
python scripts/generate_audit_report.py
```

**Total Time**: 45-75 minutes

## What Gets Created

1. **广东省自然村_预处理** table (~285K rows)
   - Cleaned and normalized village names
   - Character sets extracted
   - Full metadata

2. **prefix_cleaning_audit_log** table (~285K rows)
   - Complete audit trail
   - All cleaning operations logged

3. **Backup tables** (5 tables)
   - Original analysis tables preserved

4. **docs/PREFIX_CLEANING_AUDIT_REPORT.md**
   - Statistics and verification

## Expected Results

- Prefix removal rate: 20-40%
- Numbered village rate: 5-15%
- Average confidence: >0.85
- Processing time: 30-60 minutes

## After Preprocessing

1. **Review**: Open `docs/PREFIX_CLEANING_AUDIT_REPORT.md`
2. **Verify**: Check statistics and samples
3. **Rerun** (optional): Phase 1-3 analyses
4. **Compare** (optional): Before/after impact

## Files Implemented

### Core Modules
- ✅ src/preprocessing/prefix_cleaner.py (414 lines)
- ✅ src/preprocessing/numbered_village_normalizer.py (76 lines)
- ✅ src/preprocessing/text_cleaner.py (existing)

### Scripts
- ✅ scripts/backup_analysis_tables.py
- ✅ scripts/create_preprocessed_table.py
- ✅ scripts/create_audit_log.py
- ✅ scripts/generate_audit_report.py
- ✅ scripts/validate_preprocessing.py
- ✅ run_preprocessing.bat / .sh

### Tests
- ✅ tests/unit/test_prefix_cleaner.py
- ✅ tests/unit/test_numbered_village_normalizer.py

### Documentation
- ✅ docs/PHASE_0_PREPROCESSING_SUMMARY.md (technical)
- ✅ docs/PREPROCESSING_QUICK_START.md (user guide)
- ✅ docs/PREPROCESSING_STATUS.md (status)
- ✅ docs/IMPLEMENTATION_COMPLETE.md (summary)
- ✅ scripts/README_PREPROCESSING.md (scripts)

## Troubleshooting

**Database not found**: Check `data/villages.db` exists

**Python not found**: Ensure Python 3.x is in PATH

**Takes too long**: 30-60 min is normal for 285K villages

**Low removal rate**: Review audit report, may need parameter tuning

**High removal rate**: Check samples for false positives

## Support

- Technical details: `docs/PHASE_0_PREPROCESSING_SUMMARY.md`
- Quick start: `docs/PREPROCESSING_QUICK_START.md`
- Status: `docs/PREPROCESSING_STATUS.md`
- Skills: `.claude/skills/02_preprocessing/`

---

**Status**: Ready to execute
**Action**: Run `run_preprocessing.bat` or `run_preprocessing.sh`
**Duration**: 45-75 minutes
**Risk**: Low (tested, conservative, auditable)
