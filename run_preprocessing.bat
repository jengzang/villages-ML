@echo off
REM Preprocessing Pipeline Execution Script (Windows)
REM Run this script to execute the complete preprocessing pipeline

echo ==========================================
echo Villages-ML Preprocessing Pipeline
echo ==========================================
echo.

REM Check database exists
if not exist "data\villages.db" (
    echo ERROR: Database not found at data\villages.db
    exit /b 1
)

echo Database found: data\villages.db
echo.

REM Step 1: Backup
echo Step 1/5: Backing up analysis tables...
echo Duration: ~5 minutes
python scripts\backup_analysis_tables.py
if errorlevel 1 (
    echo ERROR: Backup failed
    exit /b 1
)
echo [OK] Backup complete
echo.

REM Step 2: Preprocessing
echo Step 2/5: Running preprocessing pipeline...
echo Duration: ~30-60 minutes
echo Processing 285K+ villages...
python scripts\create_preprocessed_table.py
if errorlevel 1 (
    echo ERROR: Preprocessing failed
    exit /b 1
)
echo [OK] Preprocessing complete
echo.

REM Step 3: Audit Log
echo Step 3/5: Creating audit log...
echo Duration: ~5 minutes
python scripts\create_audit_log.py
if errorlevel 1 (
    echo ERROR: Audit log creation failed
    exit /b 1
)
echo [OK] Audit log created
echo.

REM Step 4: Audit Report
echo Step 4/5: Generating audit report...
echo Duration: ~5 minutes
python scripts\generate_audit_report.py
if errorlevel 1 (
    echo ERROR: Audit report generation failed
    exit /b 1
)
echo [OK] Audit report generated
echo.

REM Step 5: Summary
echo Step 5/5: Preprocessing Summary
echo ==========================================
echo.
echo [OK] All preprocessing steps completed successfully!
echo.
echo Next steps:
echo 1. Review audit report: docs\PREFIX_CLEANING_AUDIT_REPORT.md
echo 2. Verify preprocessing results
echo 3. Rerun Phase 1-3 analyses (optional):
echo    - python scripts\phase1_frequency_analysis.py
echo    - python scripts\phase2_regional_tendency.py
echo    - python scripts\phase8_zscore_normalization.py
echo    - python scripts\phase9_significance_testing.py
echo.
echo ==========================================
pause
