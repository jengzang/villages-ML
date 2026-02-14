"""
Result Formatting Utilities for Tendency Analysis

This module provides utilities for formatting analysis results in various formats
including ASCII tables, markdown, HTML, and comprehensive reports.
"""

from typing import Dict, List, Tuple
from datetime import datetime


def format_results_table(results: Dict, analyzer) -> str:
    """
    Format results as ASCII table.

    Args:
        results: Analysis results from analyze_tendencies()
        analyzer: TendencyAnalyzer instance for accessing frequency data

    Returns:
        Formatted ASCII table string
    """
    output = []

    for town, town_results in results.items():
        output.append("=" * 80)
        output.append(f"Town: {town}".center(80))
        output.append("=" * 80)
        output.append("")

        # High tendency table
        if town_results["high_tendency"]:
            output.append("HIGH TENDENCY CHARACTERS (Preferentially Used)")
            output.append("-" * 80)
            output.append(f"{'Char':<6} {'Tendency':<12} {'Towns':<40} {'Count':<10}")
            output.append("-" * 80)

            for char, value, towns in town_results["high_tendency"][:10]:
                town_list = ", ".join(towns[:3])
                if len(towns) > 3:
                    town_list += f" (+{len(towns)-3} more)"

                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                output.append(f"{char:<6} {f'+{value:.1f}%':<12} {town_list:<40} {char_count:<10}")

            output.append("")

        # Low tendency table
        if town_results["low_tendency"]:
            output.append("LOW TENDENCY CHARACTERS (Avoided)")
            output.append("-" * 80)
            output.append(f"{'Char':<6} {'Tendency':<12} {'Towns':<40} {'Count':<10}")
            output.append("-" * 80)

            for char, value, towns in town_results["low_tendency"][:10]:
                town_list = ", ".join(towns[:3])
                if len(towns) > 3:
                    town_list += f" (+{len(towns)-3} more)"

                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                output.append(f"{char:<6} {f'{value:.1f}%':<12} {town_list:<40} {char_count:<10}")

            output.append("")

        output.append("")

    return "\n".join(output)


def format_results_markdown(results: Dict, analyzer, include_metadata: bool = True) -> str:
    """
    Format results as markdown.

    Args:
        results: Analysis results
        analyzer: TendencyAnalyzer instance
        include_metadata: If True, include metadata header

    Returns:
        Markdown-formatted string
    """
    output = []

    if include_metadata:
        output.append("# Village Name Tendency Analysis Results")
        output.append("")
        output.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"**Total Towns Analyzed:** {len(results)}")
        output.append("")
        output.append("---")
        output.append("")

    for town, town_results in results.items():
        output.append(f"## {town}")
        output.append("")

        # High tendency section
        if town_results["high_tendency"]:
            output.append("### High Tendency Characters")
            output.append("Characters preferentially used in this town:")
            output.append("")
            output.append("| Character | Tendency Value | High-Usage Towns | Count in Town | Total Count |")
            output.append("|-----------|----------------|------------------|---------------|-------------|")

            for char, value, towns in town_results["high_tendency"][:10]:
                town_list = ", ".join(towns)
                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                total_count = analyzer.char_total_counts.get(char, 0)
                output.append(f"| {char} | +{value:.1f}% | {town_list} | {char_count} | {total_count} |")

            output.append("")
        else:
            output.append("### High Tendency Characters")
            output.append("*No characters meet the high tendency threshold.*")
            output.append("")

        # Low tendency section
        if town_results["low_tendency"]:
            output.append("### Low Tendency Characters")
            output.append("Characters avoided in this town:")
            output.append("")
            output.append("| Character | Tendency Value | Low-Usage Towns | Count in Town | Total Count |")
            output.append("|-----------|----------------|-----------------|---------------|-------------|")

            for char, value, towns in town_results["low_tendency"][:10]:
                town_list = ", ".join(towns)
                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                total_count = analyzer.char_total_counts.get(char, 0)
                output.append(f"| {char} | {value:.1f}% | {town_list} | {char_count} | {total_count} |")

            output.append("")
        else:
            output.append("### Low Tendency Characters")
            output.append("*No characters meet the low tendency threshold.*")
            output.append("")

        output.append("---")
        output.append("")

    return "\n".join(output)


def format_results_html(results: Dict, analyzer, title: str = "Tendency Analysis Results") -> str:
    """
    Format results as HTML.

    Args:
        results: Analysis results
        analyzer: TendencyAnalyzer instance
        title: HTML page title

    Returns:
        HTML-formatted string
    """
    html = []

    # HTML header
    html.append("<!DOCTYPE html>")
    html.append("<html lang='zh-CN'>")
    html.append("<head>")
    html.append("    <meta charset='UTF-8'>")
    html.append(f"    <title>{title}</title>")
    html.append("    <style>")
    html.append("        body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; }")
    html.append("        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }")
    html.append("        h2 { color: #555; margin-top: 30px; }")
    html.append("        h3 { color: #777; }")
    html.append("        table { border-collapse: collapse; width: 100%; margin: 20px 0; }")
    html.append("        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }")
    html.append("        th { background-color: #4CAF50; color: white; }")
    html.append("        tr:nth-child(even) { background-color: #f2f2f2; }")
    html.append("        .positive { color: #4CAF50; font-weight: bold; }")
    html.append("        .negative { color: #f44336; font-weight: bold; }")
    html.append("        .metadata { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }")
    html.append("    </style>")
    html.append("</head>")
    html.append("<body>")

    # Title and metadata
    html.append(f"    <h1>{title}</h1>")
    html.append("    <div class='metadata'>")
    html.append(f"        <p><strong>Analysis Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
    html.append(f"        <p><strong>Total Towns Analyzed:</strong> {len(results)}</p>")
    html.append("    </div>")

    # Results for each town
    for town, town_results in results.items():
        html.append(f"    <h2>{town}</h2>")

        # High tendency table
        if town_results["high_tendency"]:
            html.append("    <h3>High Tendency Characters (Preferentially Used)</h3>")
            html.append("    <table>")
            html.append("        <tr>")
            html.append("            <th>Character</th>")
            html.append("            <th>Tendency Value</th>")
            html.append("            <th>High-Usage Towns</th>")
            html.append("            <th>Count in Town</th>")
            html.append("            <th>Total Count</th>")
            html.append("        </tr>")

            for char, value, towns in town_results["high_tendency"][:10]:
                town_list = ", ".join(towns)
                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                total_count = analyzer.char_total_counts.get(char, 0)

                html.append("        <tr>")
                html.append(f"            <td><strong>{char}</strong></td>")
                html.append(f"            <td class='positive'>+{value:.1f}%</td>")
                html.append(f"            <td>{town_list}</td>")
                html.append(f"            <td>{char_count}</td>")
                html.append(f"            <td>{total_count}</td>")
                html.append("        </tr>")

            html.append("    </table>")
        else:
            html.append("    <h3>High Tendency Characters</h3>")
            html.append("    <p><em>No characters meet the high tendency threshold.</em></p>")

        # Low tendency table
        if town_results["low_tendency"]:
            html.append("    <h3>Low Tendency Characters (Avoided)</h3>")
            html.append("    <table>")
            html.append("        <tr>")
            html.append("            <th>Character</th>")
            html.append("            <th>Tendency Value</th>")
            html.append("            <th>Low-Usage Towns</th>")
            html.append("            <th>Count in Town</th>")
            html.append("            <th>Total Count</th>")
            html.append("        </tr>")

            for char, value, towns in town_results["low_tendency"][:10]:
                town_list = ", ".join(towns)
                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                total_count = analyzer.char_total_counts.get(char, 0)

                html.append("        <tr>")
                html.append(f"            <td><strong>{char}</strong></td>")
                html.append(f"            <td class='negative'>{value:.1f}%</td>")
                html.append(f"            <td>{town_list}</td>")
                html.append(f"            <td>{char_count}</td>")
                html.append(f"            <td>{total_count}</td>")
                html.append("        </tr>")

            html.append("    </table>")
        else:
            html.append("    <h3>Low Tendency Characters</h3>")
            html.append("    <p><em>No characters meet the low tendency threshold.</em></p>")

        html.append("    <hr>")

    # HTML footer
    html.append("</body>")
    html.append("</html>")

    return "\n".join(html)


def generate_summary_report(results: Dict, analyzer) -> str:
    """
    Generate comprehensive analysis report with statistics and interpretations.

    Args:
        results: Analysis results
        analyzer: TendencyAnalyzer instance

    Returns:
        Comprehensive report string
    """
    report = []

    report.append("=" * 80)
    report.append("VILLAGE NAME TENDENCY ANALYSIS - COMPREHENSIVE REPORT".center(80))
    report.append("=" * 80)
    report.append("")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Overall statistics
    report.append("OVERALL STATISTICS")
    report.append("-" * 80)
    report.append(f"Total Towns: {len(analyzer.town_total_counts)}")
    report.append(f"Total Villages: {sum(analyzer.town_total_counts.values())}")
    report.append(f"Total Unique Characters: {len(analyzer.char_total_counts)}")
    report.append(f"Total Character Occurrences: {analyzer.total_chars}")
    report.append("")

    # Per-town analysis
    for town, town_results in results.items():
        report.append("=" * 80)
        report.append(f"TOWN: {town}")
        report.append("=" * 80)
        report.append("")

        town_village_count = analyzer.town_total_counts.get(town, 0)
        report.append(f"Villages in this town: {town_village_count}")
        report.append("")

        # High tendency analysis
        if town_results["high_tendency"]:
            report.append("HIGH TENDENCY CHARACTERS")
            report.append("-" * 80)
            report.append(f"Found {len(town_results['high_tendency'])} characters with high tendency")
            report.append("")

            for i, (char, value, towns) in enumerate(town_results["high_tendency"][:5], 1):
                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                total_count = analyzer.char_total_counts.get(char, 0)
                frequency = char_count / town_village_count * 100 if town_village_count > 0 else 0

                report.append(f"{i}. Character: '{char}'")
                report.append(f"   Tendency Value: +{value:.1f}%")
                report.append(f"   Frequency in {town}: {frequency:.1f}% ({char_count}/{town_village_count} villages)")
                report.append(f"   Overall Frequency: {total_count / sum(analyzer.town_total_counts.values()) * 100:.1f}%")
                report.append(f"   High-usage towns: {', '.join(towns)}")
                report.append("")

        # Low tendency analysis
        if town_results["low_tendency"]:
            report.append("LOW TENDENCY CHARACTERS")
            report.append("-" * 80)
            report.append(f"Found {len(town_results['low_tendency'])} characters with low tendency")
            report.append("")

            for i, (char, value, towns) in enumerate(town_results["low_tendency"][:5], 1):
                char_count = analyzer.char_town_counts.get(char, {}).get(town, 0)
                total_count = analyzer.char_total_counts.get(char, 0)
                frequency = char_count / town_village_count * 100 if town_village_count > 0 else 0

                report.append(f"{i}. Character: '{char}'")
                report.append(f"   Tendency Value: {value:.1f}%")
                report.append(f"   Frequency in {town}: {frequency:.1f}% ({char_count}/{town_village_count} villages)")
                report.append(f"   Overall Frequency: {total_count / sum(analyzer.town_total_counts.values()) * 100:.1f}%")
                report.append(f"   Low-usage towns: {', '.join(towns)}")
                report.append("")

        report.append("")

    report.append("=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    print("Formatter module - use with TendencyAnalyzer results")
    print("Example:")
    print("  from formatter import format_results_markdown")
    print("  markdown = format_results_markdown(results, analyzer)")
    print("  print(markdown)")
