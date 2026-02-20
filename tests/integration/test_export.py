#!/usr/bin/env python3
"""
Test the export and reproducibility modules.
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.export.exporters import CSVExporter, JSONExporter
from src.export.report_generator import ReportGenerator
from src.export.reproducibility import RunSnapshot, DeterminismValidator
from src.data.db_query import get_global_frequency


def test_csv_export():
    """Test CSV export."""
    print("Testing CSV export...")
    conn = sqlite3.connect('data/villages.db')

    # Get some data
    data = get_global_frequency(conn, 'run_002', top_n=20)
    if data is None or (hasattr(data, 'empty') and data.empty):
        print("  No data found for run_002")
        conn.close()
        return False

    # Convert DataFrame to list of dicts
    if hasattr(data, 'to_dict'):
        data = data.to_dict('records')

    # Export to CSV
    exporter = CSVExporter()
    output_path = 'test-output/test_export.csv'
    exporter.export(data, output_path, metadata={'run_id': 'run_002', 'test': True})

    # Check file exists
    if Path(output_path).exists():
        print(f"  PASS CSV export successful: {output_path}")
        conn.close()
        return True
    else:
        print(f"  FAIL CSV export failed")
        conn.close()
        return False


def test_json_export():
    """Test JSON export."""
    print("Testing JSON export...")
    conn = sqlite3.connect('data/villages.db')

    data = get_global_frequency(conn, 'run_002', top_n=20)
    if data is None or (hasattr(data, 'empty') and data.empty):
        print("  No data found")
        conn.close()
        return False

    # Convert DataFrame to list of dicts
    if hasattr(data, 'to_dict'):
        data = data.to_dict('records')

    exporter = JSONExporter()
    output_path = 'test-output/test_export.json'
    exporter.export(data, output_path, metadata={'run_id': 'run_002'})

    if Path(output_path).exists():
        print(f"  PASS JSON export successful: {output_path}")
        conn.close()
        return True
    else:
        print(f"  FAIL JSON export failed")
        conn.close()
        return False


def test_report_generation():
    """Test report generation."""
    print("Testing report generation...")
    conn = sqlite3.connect('data/villages.db')

    generator = ReportGenerator(conn)
    try:
        output_path = 'test-output/test_report.md'
        report = generator.generate_summary_report('run_002', output_path)

        if Path(output_path).exists():
            print(f"  PASS Report generation successful: {output_path}")
            conn.close()
            return True
        else:
            print(f"  FAIL Report generation failed")
            conn.close()
            return False
    except Exception as e:
        print(f"  FAIL Report generation error: {e}")
        conn.close()
        return False


def test_reproducibility():
    """Test reproducibility framework."""
    print("Testing reproducibility framework...")
    conn = sqlite3.connect('data/villages.db')

    # Create snapshot
    snapshot_mgr = RunSnapshot(conn)
    snapshot_mgr.capture_snapshot(
        run_id='test_run',
        parameters={'min_support': 10, 'test': True},
        random_state=42
    )

    # Retrieve snapshot
    snapshot = snapshot_mgr.get_snapshot('test_run')
    if snapshot and snapshot['random_state'] == 42:
        print(f"  PASS Snapshot capture/retrieve successful")
        
        # Validate
        validator = DeterminismValidator(conn)
        is_valid = validator.validate_run('test_run')
        print(f"  PASS Validation result: {is_valid}")
        
        conn.close()
        return True
    else:
        print(f"  FAIL Snapshot test failed")
        conn.close()
        return False


def main():
    print("=" * 60)
    print("Testing Export & Reproducibility Module")
    print("=" * 60)
    print()

    results = []
    results.append(("CSV Export", test_csv_export()))
    results.append(("JSON Export", test_json_export()))
    results.append(("Report Generation", test_report_generation()))
    results.append(("Reproducibility", test_reproducibility()))

    print()
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for name, passed in results:
        status = "PASS PASS" if passed else "FAIL FAIL"
        print(f"{status:8} {name}")

    all_passed = all(result[1] for result in results)
    print()
    if all_passed:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1)


if __name__ == '__main__':
    main()
