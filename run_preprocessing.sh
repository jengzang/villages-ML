#!/bin/bash
# Preprocessing Pipeline Execution Script
# Run this script to execute the complete preprocessing pipeline

set -e  # Exit on error

echo "=========================================="
echo "Villages-ML Preprocessing Pipeline"
echo "=========================================="
echo ""

# Check database exists
if [ ! -f "data/villages.db" ]; then
    echo "ERROR: Database not found at data/villages.db"
    exit 1
fi

echo "Database found: data/villages.db"
echo ""

# Step 1: Backup
echo "Step 1/5: Backing up analysis tables..."
echo "Duration: ~5 minutes"
python scripts/backup_analysis_tables.py
if [ $? -ne 0 ]; then
    echo "ERROR: Backup failed"
    exit 1
fi
echo "✓ Backup complete"
echo ""

# Step 2: Preprocessing
echo "Step 2/5: Running preprocessing pipeline..."
echo "Duration: ~30-60 minutes"
echo "Processing 285K+ villages..."
python scripts/create_preprocessed_table.py
if [ $? -ne 0 ]; then
    echo "ERROR: Preprocessing failed"
    exit 1
fi
echo "✓ Preprocessing complete"
echo ""

# Step 3: Audit Log
echo "Step 3/5: Creating audit log..."
echo "Duration: ~5 minutes"
python scripts/create_audit_log.py
if [ $? -ne 0 ]; then
    echo "ERROR: Audit log creation failed"
    exit 1
fi
echo "✓ Audit log created"
echo ""

# Step 4: Audit Report
echo "Step 4/5: Generating audit report..."
echo "Duration: ~5 minutes"
python scripts/generate_audit_report.py
if [ $? -ne 0 ]; then
    echo "ERROR: Audit report generation failed"
    exit 1
fi
echo "✓ Audit report generated"
echo ""

# Step 5: Summary
echo "Step 5/5: Preprocessing Summary"
echo "=========================================="
echo ""
echo "✓ All preprocessing steps completed successfully!"
echo ""
echo "Next steps:"
echo "1. Review audit report: docs/PREFIX_CLEANING_AUDIT_REPORT.md"
echo "2. Verify preprocessing results"
echo "3. Rerun Phase 1-3 analyses (optional):"
echo "   - python scripts/phase1_frequency_analysis.py"
echo "   - python scripts/phase2_regional_tendency.py"
echo "   - python scripts/phase8_zscore_normalization.py"
echo "   - python scripts/phase9_significance_testing.py"
echo ""
echo "=========================================="
