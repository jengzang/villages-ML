"""Character frequency computation with regional analysis."""

import json
import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

from src.schema import REGION_LEVELS, VillageTableSchema, DEFAULT_SCHEMA

logger = logging.getLogger(__name__)


def compute_char_frequency_global(
    villages_df: pd.DataFrame,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
) -> pd.DataFrame:
    """
    Compute global character frequencies across all villages.

    For each character c:
    - n_c = number of villages where c appears (binary presence)
    - N = total number of valid villages
    - p_c = n_c / N (frequency)

    Args:
        villages_df: DataFrame with columns [char_set_json] or [{schema.char_set_col}]
        schema: Table schema definition

    Returns:
        DataFrame with columns:
        - char: Character
        - village_count: Number of villages containing this char
        - total_villages: Total valid villages
        - frequency: Proportion (village_count / total_villages)
        - rank: Rank by frequency (1 = most common)
    """
    char_set_col = 'char_set_json' if 'char_set_json' in villages_df.columns else schema.char_set_col

    # Filter to valid villages only (if is_valid column exists, otherwise use all)
    if 'is_valid' in villages_df.columns:
        valid_df = villages_df[villages_df['is_valid']].copy()
    else:
        valid_df = villages_df.copy()

    total_villages = len(valid_df)

    logger.info(f"Computing global frequencies for {total_villages:,} valid villages")

    # Handle empty case
    if total_villages == 0:
        return pd.DataFrame(columns=['char', 'village_count', 'total_villages', 'frequency', 'rank'])

    # Count character occurrences (binary presence per village)
    char_counts = {}

    for char_set_json in valid_df[char_set_col]:
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
    region_level: str,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
) -> pd.DataFrame:
    """
    Compute character frequencies by region with hierarchical grouping.

    Args:
        villages_df: DataFrame with columns [{schema.city_col}, {schema.county_col}, {schema.township_col}, char_set]
        region_level: REGION_LEVELS[0], REGION_LEVELS[1], or REGION_LEVELS[2]
        schema: Table schema definition

    Returns:
        DataFrame with columns:
        - region_level: Level name
        - city: City name
        - county: County name
        - township: Township name
        - region_name: Region name (for display)
        - char: Character
        - village_count: Villages in region containing char
        - total_villages: Total valid villages in region
        - frequency: Proportion
        - rank_within_region: Rank within this region
    """
    if region_level not in schema.level_map:
        raise ValueError(f"Invalid region_level: {region_level}")

    region_col = schema.level_map[region_level]

    char_set_col = 'char_set_json' if 'char_set_json' in villages_df.columns else schema.char_set_col

    # Filter to valid villages (if is_valid column exists, otherwise use all)
    if 'is_valid' in villages_df.columns:
        valid_df = villages_df[villages_df['is_valid']].copy()
    else:
        valid_df = villages_df.copy()

    logger.info(f"Computing {region_level}-level frequencies with hierarchical grouping")

    results = []

    # Group by hierarchical key to separate duplicate place names
    if region_level == REGION_LEVELS[0]:
        group_cols = [schema.city_col]
    elif region_level == REGION_LEVELS[1]:
        group_cols = [schema.city_col, schema.county_col]
    else:  # township
        group_cols = [schema.city_col, schema.county_col, schema.township_col]

    # Group by hierarchical key
    for group_key, group in valid_df.groupby(group_cols):
        # Handle single vs multiple group columns
        # IMPORTANT: groupby always returns tuple, even for single column
        if region_level == REGION_LEVELS[0]:
            city = group_key[0] if isinstance(group_key, tuple) else group_key
            county = None
            township = None
        elif region_level == REGION_LEVELS[1]:
            city, county = group_key
            township = None
        else:  # township
            city, county, township = group_key

        # Skip if any key is NaN
        if pd.isna(city) or (region_level in [REGION_LEVELS[1], REGION_LEVELS[2]] and pd.isna(county)) or (region_level == REGION_LEVELS[2] and pd.isna(township)):
            continue

        # Get region name for display
        region_name = group[region_col].iloc[0]
        total_villages = len(group)

        # Count characters in this region
        char_counts = {}
        for char_set_json in group[char_set_col]:
            char_set = set(json.loads(char_set_json))
            for char in char_set:
                char_counts[char] = char_counts.get(char, 0) + 1

        # Add to results
        for char, count in char_counts.items():
            results.append({
                'region_level': region_level,
                REGION_LEVELS[0]: city,
                REGION_LEVELS[1]: county,
                REGION_LEVELS[2]: township,
                'region_name': region_name,
                'char': char,
                'village_count': count,
                'total_villages': total_villages,
                'frequency': count / total_villages if total_villages > 0 else 0.0
            })

    df = pd.DataFrame(results)

    # Add rank within each hierarchical region (not just by region_name)
    # Group by hierarchical key for ranking
    if region_level == REGION_LEVELS[0]:
        rank_group_cols = [REGION_LEVELS[0]]
    elif region_level == REGION_LEVELS[1]:
        rank_group_cols = [REGION_LEVELS[0], REGION_LEVELS[1]]
    else:  # township
        rank_group_cols = [REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2]]

    df['rank_within_region'] = df.groupby(rank_group_cols)['frequency'].rank(
        ascending=False, method='dense'
    ).astype(int)

    # Sort by hierarchical key and frequency
    sort_cols = rank_group_cols + ['frequency']
    df = df.sort_values(sort_cols, ascending=[True] * len(rank_group_cols) + [False])

    # Count unique regions (by hierarchical key, not just region_name)
    unique_regions = df.groupby(rank_group_cols).ngroups
    logger.info(f"Computed frequencies for {unique_regions} {region_level} regions (hierarchically separated)")

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
    min_regional_support: int = 5,
    schema: VillageTableSchema = DEFAULT_SCHEMA,
) -> dict:
    """
    Compute character frequencies at global and regional levels.

    This is a convenience wrapper that combines global and regional frequency
    computations into a single function call.

    Args:
        villages_df: DataFrame with village data
        region_levels: List of region levels to analyze (logical keys: [REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2]])
        min_global_support: Minimum global village count (for filtering)
        min_regional_support: Minimum regional village count (for filtering)
        schema: Table schema definition

    Returns:
        Dictionary with keys:
        - 'global': Global frequency DataFrame
        - 'regional': Dict mapping region_level to regional frequency DataFrame
    """
    if region_levels is None:
        region_levels = schema.level_order

    logger.info(f"Computing character frequencies for region levels: {region_levels}")

    # Compute global frequencies
    global_freq = compute_char_frequency_global(villages_df, schema=schema)

    # Filter by minimum support
    global_freq_filtered = global_freq[
        global_freq['village_count'] >= min_global_support
    ].copy()

    logger.info(f"Global: {len(global_freq)} chars total, "
                f"{len(global_freq_filtered)} meet min_global_support={min_global_support}")

    regional_freqs = {}
    for level in region_levels:
        if level not in schema.level_map:
            logger.warning(f"Unknown region level: {level}, skipping")
            continue

        logger.info(f"Computing frequencies for {level}...")

        regional_df = compute_char_frequency_by_region(villages_df, level, schema=schema)

        # Add global stats and compute lift
        regional_df = calculate_lift(regional_df, global_freq)

        # Store with original level name as key
        regional_freqs[level] = regional_df

        logger.info(f"  {level}: {len(regional_df)} char-region pairs")

    return {
        'global': global_freq_filtered,
        'regional': regional_freqs
    }
