#!/usr/bin/env python3
"""
Export analysis results to various formats.

Usage:
    python scripts/export_results.py --run-id run_002 --type global --format csv --output results.csv
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.export.exporters import CSVExporter, JSONExporter, ExcelExporter, LaTeXExporter
from src.data.db_query import (
    get_global_frequency,
    get_regional_frequency,
    get_top_polarized_chars,
    get_pattern_frequency_global,
    get_semantic_vtf_global,
    get_cluster_profile
)


def main():
    parser = argparse.ArgumentParser(description='Export analysis results')
    parser.add_argument('--run-id', required=True, help='Run identifier')
    parser.add_argument('--type', required=True,
                       choices=['global', 'regional', 'tendency', 'pattern', 'semantic', 'cluster', 'all'],
                       help='Result type to export')
    parser.add_argument('--format', required=True,
                       choices=['csv', 'json', 'excel', 'latex'],
                       help='Export format')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--top', type=int, help='Limit to top N results')
    parser.add_argument('--level', choices=['city', 'county', 'town'],
                       help='Region level (for regional queries)')
    parser.add_argument('--compress', action='store_true', help='Enable gzip compression')
    parser.add_argument('--db-path', default='data/villages.db', help='Database path')

    args = parser.parse_args()

    # Connect to database
    conn = sqlite3.connect(args.db_path)
    conn.row_factory = sqlite3.Row

    # Get data based on type
    data = []
    metadata = {'run_id': args.run_id}

    if args.type == 'global':
        data = get_global_frequency(conn, args.run_id, top_n=args.top)
        metadata['type'] = 'global_frequency'
    elif args.type == 'regional':
        if not args.level:
            print("Error: --level required for regional export")
            sys.exit(1)
        data = get_regional_frequency(conn, args.run_id, args.level, top_n=args.top)
        metadata['type'] = 'regional_frequency'
        metadata['level'] = args.level
    elif args.type == 'tendency':
        if not args.level:
            print("Error: --level required for tendency export")
            sys.exit(1)
        data = get_top_polarized_chars(conn, args.run_id, region_level=args.level, top_n=args.top)
        metadata['type'] = 'regional_tendency'
        metadata['level'] = args.level
    elif args.type == 'pattern':
        data = get_pattern_frequency_global(conn, args.run_id, 'suffix', top_n=args.top)
        metadata['type'] = 'morphology_patterns'
    elif args.type == 'semantic':
        data = get_semantic_vtf_global(conn, args.run_id, top_n=args.top)
        metadata['type'] = 'semantic_categories'
    elif args.type == 'cluster':
        data = get_cluster_profile(conn, args.run_id)
        metadata['type'] = 'cluster_summary'

    if not data or (hasattr(data, 'empty') and data.empty):
        print(f"No data found for run_id={args.run_id}, type={args.type}")
        sys.exit(1)

    # Convert DataFrame to list of dicts if needed
    if hasattr(data, 'to_dict'):
        data = data.to_dict('records')
    elif hasattr(data, '__iter__') and not isinstance(data, (list, dict)):
        # Convert Row objects to dicts
        data = [dict(row) for row in data]

    # Export based on format
    if args.format == 'csv':
        exporter = CSVExporter()
        exporter.export(data, args.output, metadata=metadata, compress=args.compress)
    elif args.format == 'json':
        exporter = JSONExporter()
        exporter.export(data, args.output, metadata=metadata, compress=args.compress)
    elif args.format == 'excel':
        exporter = ExcelExporter()
        exporter.export(data, args.output, metadata=metadata)
    elif args.format == 'latex':
        exporter = LaTeXExporter()
        caption = f"{metadata['type']} for {args.run_id}"
        label = f"tab:{args.type}_{args.run_id}"
        exporter.export(data, args.output, metadata=metadata,
                       caption=caption, label=label, max_rows=args.top)

    print(f"Exported {len(data)} rows to {args.output}")
    conn.close()


if __name__ == '__main__':
    main()
