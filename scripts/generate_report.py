#!/usr/bin/env python3
"""
Generate analysis reports.

Usage:
    python scripts/generate_report.py --run-id run_002 --type summary --output report.md
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.export.report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description='Generate analysis reports')
    parser.add_argument('--run-id', required=True, help='Run identifier')
    parser.add_argument('--type', required=True,
                       choices=['summary', 'comparison'],
                       help='Report type')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--compare-with', nargs='+',
                       help='Additional run IDs for comparison')
    parser.add_argument('--db-path', default='data/villages.db', help='Database path')

    args = parser.parse_args()

    # Connect to database
    conn = sqlite3.connect(args.db_path)
    conn.row_factory = sqlite3.Row

    # Generate report
    generator = ReportGenerator(conn)

    if args.type == 'summary':
        report = generator.generate_summary_report(args.run_id, args.output)
        print(f"Summary report generated: {args.output}")
    elif args.type == 'comparison':
        if not args.compare_with:
            print("Error: --compare-with required for comparison report")
            sys.exit(1)
        run_ids = [args.run_id] + args.compare_with
        report = generator.generate_comparison_report(run_ids, args.output)
        print(f"Comparison report generated: {args.output}")

    conn.close()


if __name__ == '__main__':
    main()
