#!/usr/bin/env python3
"""
Compare analysis runs and verify reproducibility.

Usage:
    python scripts/compare_runs.py --run-ids run_002 run_003 --output comparison.md
    python scripts/compare_runs.py --run-id run_002 --verify-reproducibility
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.export.reproducibility import RunSnapshot, ResultVersioning, DeterminismValidator


def main():
    parser = argparse.ArgumentParser(description='Compare runs and verify reproducibility')
    parser.add_argument('--run-ids', nargs='+', help='Run IDs to compare')
    parser.add_argument('--run-id', help='Single run ID for verification')
    parser.add_argument('--verify-reproducibility', action='store_true',
                       help='Verify reproducibility of a run')
    parser.add_argument('--output', help='Output file path for comparison report')
    parser.add_argument('--db-path', default='data/villages.db', help='Database path')

    args = parser.parse_args()

    # Connect to database
    conn = sqlite3.connect(args.db_path)

    if args.verify_reproducibility:
        if not args.run_id:
            print("Error: --run-id required for reproducibility verification")
            sys.exit(1)

        validator = DeterminismValidator(conn)
        is_reproducible = validator.validate_run(args.run_id)
        checksum = validator.calculate_result_checksum(args.run_id)

        print(f"Run: {args.run_id}")
        print(f"Reproducible: {is_reproducible}")
        print(f"Result checksum: {checksum}")

        snapshot_mgr = RunSnapshot(conn)
        snapshot = snapshot_mgr.get_snapshot(args.run_id)
        if snapshot:
            print(f"\nSnapshot details:")
            print(f"  Git commit: {snapshot['git_commit_hash']}")
            print(f"  Random state: {snapshot['random_state']}")
            print(f"  Data hash: {snapshot['data_hash']}")

    elif args.run_ids and len(args.run_ids) >= 2:
        versioning = ResultVersioning(conn)
        comparison = versioning.compare_runs(args.run_ids[0], args.run_ids[1])

        print(f"Comparing {args.run_ids[0]} vs {args.run_ids[1]}")
        print(f"Parameter differences: {comparison['parameter_differences']}")
        print(f"Data changed: {comparison['data_changed']}")
        print(f"Top 100 overlap: {comparison['top100_overlap']:.2%}")
        print(f"Git commit same: {comparison['git_commit_same']}")

        if args.output:
            lines = []
            lines.append(f"# Run Comparison: {args.run_ids[0]} vs {args.run_ids[1]}")
            lines.append(f"")
            lines.append(f"## Summary")
            lines.append(f"- Parameter differences: {len(comparison['parameter_differences'])}")
            lines.append(f"- Data changed: {comparison['data_changed']}")
            lines.append(f"- Top 100 overlap: {comparison['top100_overlap']:.2%}")
            lines.append(f"- Git commit same: {comparison['git_commit_same']}")
            lines.append(f"")
            if comparison['parameter_differences']:
                lines.append(f"## Parameter Differences")
                for key, values in comparison['parameter_differences'].items():
                    lines.append(f"- **{key}**: {values['run1']} → {values['run2']}")

            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"\nComparison report saved to: {args.output}")

    else:
        print("Error: Either --verify-reproducibility with --run-id, or --run-ids with 2+ IDs required")
        sys.exit(1)

    conn.close()


if __name__ == '__main__':
    main()
