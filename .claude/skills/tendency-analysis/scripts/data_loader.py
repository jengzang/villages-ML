"""
Data Loading Utilities for Tendency Analysis

This module provides utilities for loading, validating, and exporting
village data for tendency analysis.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional


def load_village_data(file_path: str, verbose: bool = False) -> Dict:
    """
    Load village data from text file using the existing parser.

    Args:
        file_path: Path to village registry text file (阳春村庄名录.txt)
        verbose: If True, print debug information during parsing

    Returns:
        Hierarchical village data dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file encoding is incorrect
    """
    # Import the existing parser from the project
    try:
        # Try to import from the project's your_module directory
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "your_module"))
        from data_parser import parse_village_file
    except ImportError:
        # Fallback: implement basic parser inline
        return _parse_village_file_inline(file_path, verbose)

    # Suppress debug output if not verbose
    if not verbose:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            data = parse_village_file(file_path)
    else:
        data = parse_village_file(file_path)

    return data


def _parse_village_file_inline(file_path: str, verbose: bool = False) -> Dict:
    """
    Inline implementation of village file parser (fallback).

    Args:
        file_path: Path to village registry text file
        verbose: If True, print debug information

    Returns:
        Parsed village data
    """
    import re

    data = {}
    current_town = None
    current_committee = None

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            # Town separator
            if line.startswith('*****'):
                current_town = None
                continue

            # New town
            if not current_town:
                current_town = line
                data[current_town] = {
                    '村民委员会': [],
                    '居民委员会': [],
                    '社区': [],
                    '自然村': {}
                }
                if verbose:
                    print(f"Found town: {current_town}")

            # Committee list line
            elif '（' in line and '）' in line and '个' in line:
                parts = line.split('（')
                committees = parts[0].split('、')
                committee_type = parts[1].split('个')[1].split('）')[0]

                if committee_type not in data[current_town]:
                    data[current_town][committee_type] = []
                data[current_town][committee_type].extend(committees)

                if verbose:
                    print(f"Found {committee_type}: {', '.join(committees)}")

            # Natural village line
            elif line.startswith(''):
                committee_info = re.search(r'\\s*(.*村民委员会)：(.*)', line)
                if committee_info:
                    current_committee = committee_info.group(1)
                    villages_raw = committee_info.group(2)
                    villages_part = re.split(r'（\\d+条自然村）', villages_raw)[0]
                    villages = [v.strip() for v in re.split(r'[、及]', villages_part)]

                    if current_town and current_committee:
                        data[current_town]['自然村'][current_committee] = villages

                        if verbose:
                            print(f"Found villages for {current_committee}: {len(villages)} villages")

    return data


def validate_data_structure(data: Dict, verbose: bool = False) -> bool:
    """
    Validate input data structure.

    Args:
        data: Data to validate
        verbose: If True, print validation details

    Returns:
        True if valid

    Raises:
        ValueError: If data structure is invalid
    """
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    if len(data) < 2:
        raise ValueError("At least 2 towns required for tendency analysis")

    for town_name, town_data in data.items():
        if not isinstance(town_name, str) or not town_name:
            raise ValueError(f"Town name must be non-empty string: {town_name}")

        if not isinstance(town_data, dict):
            raise ValueError(f"Town data must be dictionary: {town_name}")

        if "自然村" not in town_data:
            raise ValueError(f"Town must have '自然村' key: {town_name}")

        natural_villages = town_data["自然村"]
        if not isinstance(natural_villages, dict):
            raise ValueError(f"'自然村' must be dictionary: {town_name}")

        village_count = 0
        for committee, villages in natural_villages.items():
            if not isinstance(committee, str) or not committee:
                raise ValueError(f"Committee name must be non-empty string: {committee}")

            if not isinstance(villages, list):
                raise ValueError(f"Villages must be list: {committee}")

            if not villages:
                raise ValueError(f"Committee must have at least one village: {committee}")

            for village in villages:
                if not isinstance(village, str) or not village:
                    raise ValueError(f"Village name must be non-empty string: {village}")

            village_count += len(villages)

        if verbose:
            print(f"Town '{town_name}': {village_count} villages")

    if verbose:
        print(f"Validation passed: {len(data)} towns")

    return True


def load_from_json(file_path: str) -> Dict:
    """
    Load pre-parsed JSON data.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed data dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate structure
    validate_data_structure(data)

    return data


def save_to_json(data: Dict, file_path: str, indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Village data dictionary
        file_path: Output file path
        indent: JSON indentation level
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def export_results(
    results: Dict,
    output_path: str,
    format: str = 'json',
    metadata: Optional[Dict] = None
) -> None:
    """
    Export analysis results to file.

    Args:
        results: Results from analyze_tendencies()
        output_path: Output file path
        format: Output format ('json', 'markdown', 'txt')
        metadata: Optional metadata to include (parameters, date, etc.)

    Raises:
        ValueError: If format is not supported
    """
    if format == 'json':
        output_data = {
            "metadata": metadata or {},
            "results": results
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    elif format == 'markdown':
        with open(output_path, 'w', encoding='utf-8') as f:
            if metadata:
                f.write("# Village Name Tendency Analysis Results\n\n")
                f.write(f"**Analysis Date:** {metadata.get('date', 'N/A')}\\n")
                f.write(f"**Parameters:** {metadata.get('parameters', 'N/A')}\\n\n")
                f.write("---\n\n")

            for town, town_results in results.items():
                f.write(f"## {town}\n\n")

                if town_results["high_tendency"]:
                    f.write("### High Tendency Characters\n\n")
                    f.write("| Character | Tendency Value | High-Usage Towns |\n")
                    f.write("|-----------|----------------|------------------|\n")
                    for char, value, towns in town_results["high_tendency"]:
                        town_list = ", ".join(towns)
                        f.write(f"| {char} | +{value:.1f}% | {town_list} |\n")
                    f.write("\n")

                if town_results["low_tendency"]:
                    f.write("### Low Tendency Characters\n\n")
                    f.write("| Character | Tendency Value | Low-Usage Towns |\n")
                    f.write("|-----------|----------------|------------------|\n")
                    for char, value, towns in town_results["low_tendency"]:
                        town_list = ", ".join(towns)
                        f.write(f"| {char} | {value:.1f}% | {town_list} |\n")
                    f.write("\n")

                f.write("---\n\n")

    elif format == 'txt':
        with open(output_path, 'w', encoding='utf-8') as f:
            if metadata:
                f.write("=" * 60 + "\n")
                f.write("Village Name Tendency Analysis Results\n")
                f.write("=" * 60 + "\n\n")
                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")

            for town, town_results in results.items():
                f.write("=" * 60 + "\n")
                f.write(f"=== {town} ===\n")
                f.write("=" * 60 + "\n\n")

                if town_results["high_tendency"]:
                    f.write("高倾向字 (在以下镇使用频率最高):\n")
                    for char, value, towns in town_results["high_tendency"]:
                        town_list = ", ".join(towns)
                        f.write(f"  {char} (倾向值: +{value:.1f}%) - 在 [{town_list}] 中使用频率最高\n")
                    f.write("\n")

                if town_results["low_tendency"]:
                    f.write("低倾向字 (在以下镇使用频率最低):\n")
                    for char, value, towns in town_results["low_tendency"]:
                        town_list = ", ".join(towns)
                        f.write(f"  {char} (倾向值: {value:.1f}%) - 在 [{town_list}] 中使用频率最低\n")
                    f.write("\n")

    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json', 'markdown', or 'txt'")


def get_data_summary(data: Dict) -> Dict:
    """
    Get summary statistics for village data.

    Args:
        data: Village data dictionary

    Returns:
        Dictionary with summary statistics
    """
    total_towns = len(data)
    total_villages = 0
    total_committees = 0

    for town_data in data.values():
        for villages in town_data.get('自然村', {}).values():
            total_villages += len(villages)
            total_committees += 1

    return {
        "total_towns": total_towns,
        "total_villages": total_villages,
        "total_committees": total_committees,
        "avg_villages_per_town": total_villages / total_towns if total_towns > 0 else 0
    }


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Loading data from: {file_path}")

        data = load_village_data(file_path, verbose=True)
        print("\nValidating data structure...")
        validate_data_structure(data, verbose=True)

        print("\nData summary:")
        summary = get_data_summary(data)
        for key, value in summary.items():
            print(f"  {key}: {value}")

        # Save to JSON
        output_path = "village_data.json"
        save_to_json(data, output_path)
        print(f"\nData saved to: {output_path}")
    else:
        print("Usage: python data_loader.py <path_to_village_file>")
