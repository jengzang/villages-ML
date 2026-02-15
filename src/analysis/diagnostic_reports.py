"""Enhanced diagnostic reporting for regional tendency analysis."""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def find_most_polarized_characters(
    tendency_df: pd.DataFrame,
    top_n: int = 20
) -> pd.DataFrame:
    """
    Find characters with strongest regional polarization.

    Polarization measured by variance of log_odds across regions.

    Args:
        tendency_df: Regional tendency DataFrame
        top_n: Number of top polarized characters to return

    Returns:
        DataFrame with columns: char, polarization_score, n_regions,
        max_log_odds, min_log_odds, range_log_odds
    """
    # Group by character and compute polarization metrics
    char_stats = tendency_df.groupby('char').agg({
        'log_odds': ['std', 'min', 'max', 'count']
    }).reset_index()

    char_stats.columns = ['char', 'polarization_score', 'min_log_odds',
                          'max_log_odds', 'n_regions']
    char_stats['range_log_odds'] = char_stats['max_log_odds'] - char_stats['min_log_odds']

    # Sort by polarization score (std of log_odds)
    char_stats = char_stats.sort_values('polarization_score', ascending=False)

    return char_stats.head(top_n)


def find_extreme_regions(
    tendency_df: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """
    Find regions with strongest positive/negative deviations overall.

    Args:
        tendency_df: Regional tendency DataFrame

    Returns:
        Dictionary with keys 'most_positive' and 'most_negative',
        each containing DataFrame with region stats
    """
    # Compute average log_odds per region
    region_stats = tendency_df.groupby('region_name').agg({
        'log_odds': ['mean', 'std', 'count']
    }).reset_index()

    region_stats.columns = ['region_name', 'avg_log_odds', 'std_log_odds', 'n_chars']

    # Sort by average log_odds
    most_positive = region_stats.nlargest(10, 'avg_log_odds')
    most_negative = region_stats.nsmallest(10, 'avg_log_odds')

    return {
        'most_positive': most_positive,
        'most_negative': most_negative
    }


def generate_distribution_histogram(
    tendency_df: pd.DataFrame,
    bins: int = 50
) -> Dict[str, np.ndarray]:
    """
    Generate histogram data for log_odds distribution.

    Args:
        tendency_df: Regional tendency DataFrame
        bins: Number of histogram bins

    Returns:
        Dictionary with 'counts', 'bin_edges', and 'stats'
    """
    log_odds_values = tendency_df['log_odds'].dropna()

    counts, bin_edges = np.histogram(log_odds_values, bins=bins)

    stats = {
        'mean': log_odds_values.mean(),
        'median': log_odds_values.median(),
        'std': log_odds_values.std(),
        'min': log_odds_values.min(),
        'max': log_odds_values.max(),
        'q25': log_odds_values.quantile(0.25),
        'q75': log_odds_values.quantile(0.75)
    }

    return {
        'counts': counts,
        'bin_edges': bin_edges,
        'stats': stats
    }


def create_comprehensive_report(
    tendency_df: pd.DataFrame,
    output_path: Path,
    region_level: str
) -> None:
    """
    Generate comprehensive diagnostic report.

    Args:
        tendency_df: Regional tendency DataFrame
        output_path: Path to save report
        region_level: 'city', 'county', or 'township'
    """
    logger.info(f"Generating diagnostic report for {region_level} level")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"Regional Tendency Diagnostic Report - {region_level.upper()} Level\n")
        f.write("=" * 80 + "\n\n")

        # Overall statistics
        f.write("OVERALL STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total char-region pairs: {len(tendency_df):,}\n")
        f.write(f"Unique characters: {tendency_df['char'].nunique():,}\n")
        f.write(f"Unique regions: {tendency_df['region_name'].nunique():,}\n\n")

        # Distribution statistics
        hist_data = generate_distribution_histogram(tendency_df)
        stats = hist_data['stats']

        f.write("LOG-ODDS DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Mean: {stats['mean']:.4f}\n")
        f.write(f"Median: {stats['median']:.4f}\n")
        f.write(f"Std Dev: {stats['std']:.4f}\n")
        f.write(f"Min: {stats['min']:.4f}\n")
        f.write(f"Max: {stats['max']:.4f}\n")
        f.write(f"Q25: {stats['q25']:.4f}\n")
        f.write(f"Q75: {stats['q75']:.4f}\n\n")

        # Most polarized characters
        f.write("TOP 20 MOST REGIONALLY POLARIZED CHARACTERS\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Rank':<6} {'Char':<6} {'Polarization':<14} {'Range':<12} {'N_Regions':<12}\n")
        f.write("-" * 80 + "\n")

        polarized = find_most_polarized_characters(tendency_df, top_n=20)
        for idx, row in polarized.iterrows():
            f.write(f"{idx+1:<6} {row['char']:<6} {row['polarization_score']:<14.4f} "
                   f"{row['range_log_odds']:<12.4f} {int(row['n_regions']):<12}\n")

        f.write("\n")

        # Extreme regions
        f.write("REGIONS WITH STRONGEST DEVIATIONS\n")
        f.write("-" * 80 + "\n\n")

        extreme_regions = find_extreme_regions(tendency_df)

        f.write("Top 10 Regions with Highest Average Log-Odds (Overrepresentation):\n")
        f.write(f"{'Rank':<6} {'Region':<40} {'Avg Log-Odds':<15} {'N_Chars':<10}\n")
        f.write("-" * 80 + "\n")
        for idx, row in extreme_regions['most_positive'].iterrows():
            f.write(f"{idx+1:<6} {row['region_name']:<40} {row['avg_log_odds']:<15.4f} "
                   f"{int(row['n_chars']):<10}\n")

        f.write("\n")

        f.write("Top 10 Regions with Lowest Average Log-Odds (Underrepresentation):\n")
        f.write(f"{'Rank':<6} {'Region':<40} {'Avg Log-Odds':<15} {'N_Chars':<10}\n")
        f.write("-" * 80 + "\n")
        for idx, row in extreme_regions['most_negative'].iterrows():
            f.write(f"{idx+1:<6} {row['region_name']:<40} {row['avg_log_odds']:<15.4f} "
                   f"{int(row['n_chars']):<10}\n")

        f.write("\n")

        # Interpretation guidelines
        f.write("INTERPRETATION GUIDELINES\n")
        f.write("-" * 80 + "\n")
        f.write("Polarization Score: Standard deviation of log-odds across regions.\n")
        f.write("  - Higher values = character usage varies more across regions\n")
        f.write("  - Lower values = character usage is more uniform\n\n")
        f.write("Log-Odds: Log of (regional_freq / global_freq)\n")
        f.write("  - Positive = overrepresented in region\n")
        f.write("  - Negative = underrepresented in region\n")
        f.write("  - Near zero = similar to global average\n\n")
        f.write("Lift: Regional frequency / Global frequency\n")
        f.write("  - > 1 = overrepresented\n")
        f.write("  - < 1 = underrepresented\n")
        f.write("  - = 1 = matches global average\n\n")

    logger.info(f"Diagnostic report saved to {output_path}")
