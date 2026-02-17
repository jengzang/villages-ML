"""Character frequency computation with regional analysis."""

import json
import logging
from typing import Dict
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_char_frequency_global(villages_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute global character frequencies across all villages.

    For each character c:
    - n_c = number of villages where c appears (binary presence)
    - N = total number of valid villages
    - p_c = n_c / N (frequency)

    Args:
        villages_df: DataFrame with columns [char_set_json, is_valid]

    Returns:
        DataFrame with columns:
        - char: Character
        - village_count: Number of villages containing this char
        - total_villages: Total valid villages
        - frequency: Proportion (village_count / total_villages)
        - rank: Rank by frequency (1 = most common)
    """
    # Filter to valid villages only
    valid_df = villages_df[villages_df['is_valid']].copy()
    total_villages = len(valid_df)

    logger.info(f"Computing global frequencies for {total_villages:,} valid villages")

    # Handle empty case
    if total_villages == 0:
        return pd.DataFrame(columns=['char', 'village_count', 'total_villages', 'frequency', 'rank'])

    # Count character occurrences (binary presence per village)
    char_counts = {}

    for char_set_json in valid_df['char_set_json']:
        char_set = set(json.loads(char_set_json))
        for char in char_set:
            char_counts[char] = char_counts.get(char, 0) + 1

    # Build result DataFrame
    results = []
    for char, count in char_counts.items():
        results.append({
            'char': char,
            'village_count': count,
            'total_villages': total_villages,
            'frequency': count / total_villages if total_villages > 0 else 0.0
        })

    df = pd.DataFrame(results)

    # Sort by frequency and add rank
    df = df.sort_values('frequency', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1

    logger.info(f"Computed frequencies for {len(df)} unique characters")
    logger.info(f"Top 5 chars: {df.head(5)['char'].tolist()}")

    return df


def compute_char_frequency_by_region(
    villages_df: pd.DataFrame,
    region_level: str
) -> pd.DataFrame:
    """
    Compute character frequencies by region.

    Args:
        villages_df: DataFrame with columns [市级, 区县级, 乡镇级, char_set_json, is_valid]
        region_level: 'city', 'county', or 'township'

    Returns:
        DataFrame with columns:
        - region_level: Level name
        - region_name: Region name
        - char: Character
        - village_count: Villages in region containing char
        - total_villages: Total valid villages in region
        - frequency: Proportion
        - rank_within_region: Rank within this region
    """
    level_map = {
        'city': '市级',
        'county': '区县级',
        'township': '乡镇级'
    }

    if region_level not in level_map:
        raise ValueError(f"Invalid region_level: {region_level}")

    region_col = level_map[region_level]

    # Filter to valid villages
    valid_df = villages_df[villages_df['is_valid']].copy()

    logger.info(f"Computing {region_level}-level frequencies")

    results = []

    # Group by region
    for region_name, group in valid_df.groupby(region_col):
        if pd.isna(region_name):
            continue

        total_villages = len(group)

        # Count characters in this region
        char_counts = {}
        for char_set_json in group['char_set_json']:
            char_set = set(json.loads(char_set_json))
            for char in char_set:
                char_counts[char] = char_counts.get(char, 0) + 1

        # Add to results
        for char, count in char_counts.items():
            results.append({
                'region_level': region_level,
                'region_name': region_name,
                'char': char,
                'village_count': count,
                'total_villages': total_villages,
                'frequency': count / total_villages if total_villages > 0 else 0.0
            })

    df = pd.DataFrame(results)

    # Add rank within each region
    df['rank_within_region'] = df.groupby('region_name')['frequency'].rank(
        ascending=False, method='dense'
    ).astype(int)

    # Sort by region and frequency
    df = df.sort_values(['region_name', 'frequency'], ascending=[True, False])

    logger.info(f"Computed frequencies for {df['region_name'].nunique()} {region_level} regions")

    return df


def calculate_lift(
    regional_freq: pd.DataFrame,
    global_freq: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate lift (regional tendency) by comparing regional to global frequencies.

    lift = p_regional / p_global

    Args:
        regional_freq: Regional frequency DataFrame
        global_freq: Global frequency DataFrame

    Returns:
        Regional DataFrame with added columns:
        - global_village_count
        - global_frequency
        - lift_vs_global
    """
    # Create lookup dict for global frequencies
    global_lookup = global_freq.set_index('char')[['village_count', 'frequency']].to_dict('index')

    # Add global stats and compute lift
    regional_freq = regional_freq.copy()

    regional_freq['global_village_count'] = regional_freq['char'].map(
        lambda c: global_lookup.get(c, {}).get('village_count', 0)
    )
    regional_freq['global_frequency'] = regional_freq['char'].map(
        lambda c: global_lookup.get(c, {}).get('frequency', 0.0)
    )

    # Compute lift (avoid division by zero)
    regional_freq['lift_vs_global'] = np.where(
        regional_freq['global_frequency'] > 0,
        regional_freq['frequency'] / regional_freq['global_frequency'],
        np.nan
    )

    logger.info("Calculated lift values for regional frequencies")

    return regional_freq


def compute_char_frequency(
    villages_df: pd.DataFrame,
    region_levels: list = None,
    min_global_support: int = 20,
    min_regional_support: int = 5
) -> dict:
    """
    Compute character frequencies at global and regional levels.

    This is a convenience wrapper that combines global and regional frequency
    computations into a single function call.

    Args:
        villages_df: DataFrame with village data
        region_levels: List of region levels to analyze (e.g., ['市级', '县区级', '乡镇'])
        min_global_support: Minimum global village count (for filtering)
        min_regional_support: Minimum regional village count (for filtering)

    Returns:
        Dictionary with keys:
        - 'global': Global frequency DataFrame
        - 'regional': Dict mapping region_level to regional frequency DataFrame
    """
    if region_levels is None:
        region_levels = ['市级', '县区级', '乡镇']

    logger.info(f"Computing character frequencies for region levels: {region_levels}")

    # Compute global frequencies
    global_freq = compute_char_frequency_global(villages_df)

    # Filter by minimum support
    global_freq_filtered = global_freq[
        global_freq['village_count'] >= min_global_support
    ].copy()

    logger.info(f"Global: {len(global_freq)} chars total, "
                f"{len(global_freq_filtered)} meet min_global_support={min_global_support}")

    # Compute regional frequencies
    level_map = {
        '市级': 'city',
        '县区级': 'county',
        '乡镇': 'township'
    }

    regional_freqs = {}
    for level in region_levels:
        if level not in level_map:
            logger.warning(f"Unknown region level: {level}, skipping")
            continue

        level_key = level_map[level]
        logger.info(f"Computing frequencies for {level}...")

        regional_df = compute_char_frequency_by_region(villages_df, level_key)

        # Add global stats and compute lift
        regional_df = calculate_lift(regional_df, global_freq)

        # Store with original level name as key
        regional_freqs[level] = regional_df

        logger.info(f"  {level}: {len(regional_df)} char-region pairs")

    return {
        'global': global_freq_filtered,
        'regional': regional_freqs
    }
