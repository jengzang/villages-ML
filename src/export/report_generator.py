"""
Report generation module for analysis results.
"""

import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..data.db_query import (
    get_global_frequency,
    get_regional_frequency,
    get_top_polarized_chars,
    get_pattern_frequency_global,
    get_semantic_vtf_global,
    get_cluster_profile
)
from .formatters import format_number, format_percentage, format_timestamp


class ReportGenerator:
    """Generate analysis reports in various formats."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize report generator.

        Args:
            conn: Database connection
        """
        self.conn = conn

    def generate_summary_report(self, run_id: str, output_path: Optional[str] = None) -> str:
        """
        Generate summary report for a run.

        Args:
            run_id: Run identifier
            output_path: Optional output file path

        Returns:
            Report content as string
        """
        # Get run metadata
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT created_at, config_json, total_villages
            FROM analysis_runs
            WHERE run_id = ?
        """, (run_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Run {run_id} not found")

        created_at, config_json, total_villages = row

        # Build report
        lines = []
        lines.append(f"# Analysis Summary Report")
        lines.append(f"")
        lines.append(f"**Run ID:** {run_id}")
        lines.append(f"**Created:** {format_timestamp(created_at)}")
        lines.append(f"**Total Villages:** {format_number(total_villages)}")
        lines.append(f"**Config:** {config_json}")
        lines.append(f"")

        # Global frequency top 20
        lines.append(f"## Top 20 Characters by Frequency")
        lines.append(f"")
        try:
            global_freq = get_global_frequency(self.conn, run_id, top_n=20)
            if global_freq is not None and not (hasattr(global_freq, 'empty') and global_freq.empty):
                if hasattr(global_freq, 'to_dict'):
                    global_freq = global_freq.to_dict('records')
                lines.append("| Rank | Character | Village Count | Frequency |")
                lines.append("|------|-----------|---------------|-----------|")
                for idx, row in enumerate(global_freq, 1):
                    rank = row.get('rank', idx)
                    char = row.get('char', row.get('character', ''))
                    count = row.get('village_count', row.get('count', 0))
                    freq = row.get('frequency', row.get('freq', 0))
                    lines.append(f"| {rank} | {char} | {format_number(count)} | {format_percentage(freq)} |")
        except Exception as e:
            lines.append(f"_(Error loading data: {e})_")
        lines.append(f"")

        # Regional tendency top 10
        lines.append(f"## Top 10 Polarized Characters (Regional Tendency)")
        lines.append(f"")
        try:
            tendency = get_top_polarized_chars(self.conn, run_id, region_level='city', top_n=10)
            if tendency is not None and not (hasattr(tendency, 'empty') and tendency.empty):
                if hasattr(tendency, 'to_dict'):
                    tendency = tendency.to_dict('records')
                lines.append("| Rank | Character | Region | Tendency Value |")
                lines.append("|------|-----------|--------|----------------|")
                for idx, row in enumerate(tendency, 1):
                    rank = row.get('rank', idx)
                    char = row.get('char', row.get('character', ''))
                    region = row.get('region', '')
                    tendency_val = row.get('tendency_value', row.get('log_odds', 0))
                    lines.append(f"| {rank} | {char} | {region} | {tendency_val:.4f} |")
        except Exception as e:
            lines.append(f"_(Error loading data: {e})_")
        lines.append(f"")

        # Morphology patterns top 10
        lines.append(f"## Top 10 Morphology Patterns")
        lines.append(f"")
        try:
            patterns = get_pattern_frequency_global(self.conn, run_id, pattern_type='suffix', top_n=10)
            if patterns is not None and not (hasattr(patterns, 'empty') and patterns.empty):
                if hasattr(patterns, 'to_dict'):
                    patterns = patterns.to_dict('records')
                lines.append("| Rank | Pattern | Village Count | Frequency |")
                lines.append("|------|---------|---------------|-----------|")
                for idx, row in enumerate(patterns, 1):
                    rank = row.get('rank', idx)
                    pattern = row.get('pattern', '')
                    count = row.get('village_count', row.get('count', 0))
                    freq = row.get('frequency', row.get('freq', 0))
                    lines.append(f"| {rank} | {pattern} | {format_number(count)} | {format_percentage(freq)} |")
        except Exception as e:
            lines.append(f"_(Error loading data: {e})_")
        lines.append(f"")

        report = '\n'.join(lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)

        return report

    def generate_comparison_report(self, run_ids: List[str], output_path: Optional[str] = None) -> str:
        """
        Generate comparison report for multiple runs.

        Args:
            run_ids: List of run identifiers
            output_path: Optional output file path

        Returns:
            Report content as string
        """
        lines = []
        lines.append(f"# Run Comparison Report")
        lines.append(f"")
        lines.append(f"**Comparing Runs:** {', '.join(run_ids)}")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"")

        # Get metadata for each run
        lines.append(f"## Run Metadata")
        lines.append(f"")
        lines.append("| Run ID | Created | Total Villages | Parameters |")
        lines.append("|--------|---------|----------------|------------|")

        for run_id in run_ids:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT created_at, config_json, total_villages
                FROM analysis_runs
                WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()
            if row:
                created_at, config_json, total_villages = row
                lines.append(f"| {run_id} | {format_timestamp(created_at)} | {format_number(total_villages)} | {config_json} |")

        lines.append(f"")

        # Compare top 10 characters across runs
        lines.append(f"## Top 10 Characters Comparison")
        lines.append(f"")

        for run_id in run_ids:
            lines.append(f"### {run_id}")
            lines.append(f"")
            global_freq = get_global_frequency(self.conn, run_id, top_n=10)
            if global_freq is not None and not (hasattr(global_freq, 'empty') and global_freq.empty):
                if hasattr(global_freq, 'to_dict'):
                    global_freq = global_freq.to_dict('records')
                lines.append("| Rank | Character | Village Count | Frequency |")
                lines.append("|------|-----------|---------------|-----------|")
                for row in global_freq:
                    lines.append(f"| {row['rank']} | {row['char']} | {format_number(row['village_count'])} | {format_percentage(row['frequency'])} |")
            lines.append(f"")

        report = '\n'.join(lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)

        return report
