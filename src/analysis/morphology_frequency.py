"""Morphology pattern frequency computation (suffix/prefix)."""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_pattern_frequency_global(
    villages_df: pd.DataFrame,
    pattern_col: str
) -> pd.DataFrame:
    """
    Compute global pattern frequencies across all villages.

    For each pattern p:
    - n_p = number of villages where p appears
    - N = total number of valid villages
    - freq_p = n_p / N

    Args:
        villages_df: DataFrame with pattern column and is_valid
        pattern_col: Column name (e.g., 'suffix_1', 'prefix_2')

    Returns:
        DataFrame with columns:
        - pattern: Pattern string
        - village_count: Number of villages with this pattern
        - total_villages: Total valid villages
        - frequency: Proportion
        - rank: Rank by frequency (1 = most common)
    """
    # Filter to valid villages with non-null patterns
    valid_df = villages_df[
        villages_df['is_valid'] & villages_df[pattern_col].notna()
    ].copy()

    total_villages = len(valid_df)

    logger.info(f"Computing global frequencies for {pattern_col}: {total_villages:,} valid villages")

    if total_villages == 0:
        return pd.DataFrame(columns=['pattern', 'village_count', 'total_villages', 'frequency', 'rank'])

    # Count pattern occurrences
    pattern_counts = valid_df[pattern_col].value_counts().to_dict()

    # Build result DataFrame
    results = []
    for pattern, count in pattern_counts.items():
        results.append({
            'pattern': pattern,
            'village_count': count,
            'total_villages': total_villages,
            'frequency': count / total_villages if total_villages > 0 else 0.0
        })

    df = pd.DataFrame(results)

    # Sort by frequency and add rank
    df = df.sort_values('frequency', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1

    logger.info(f"Computed frequencies for {len(df)} unique patterns")
    if len(df) > 0:
        logger.info(f"Top 5 patterns: {df.head(5)['pattern'].tolist()}")

    return df


def compute_pattern_frequency_by_region(
    villages_df: pd.DataFrame,
    region_level: str,
    pattern_col: str
) -> pd.DataFrame:
    """
    Compute pattern frequencies by region.

    Args:
        villages_df: DataFrame with region columns, pattern column, and is_valid
        region_level: 'city', 'county', or 'township'
        pattern_col: Column name (e.g., 'suffix_1', 'prefix_2')

    Returns:
        DataFrame with columns:
        - region_level: Level name
        - region_name: Region name
        - pattern: Pattern string
        - village_count: Villages in region with this pattern
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

    # Filter to valid villages with non-null patterns
    valid_df = villages_df[
        villages_df['is_valid'] & villages_df[pattern_col].notna()
    ].copy()

    logger.info(f"Computing {region_level}-level frequencies for {pattern_col}")

    results = []

    # Group by region
    for region_name, group in valid_df.groupby(region_col):
        if pd.isna(region_name):
            continue

        total_villages = len(group)

        # Count patterns in this region
        pattern_counts = group[pattern_col].value_counts().to_dict()

        # Add to results
        for pattern, count in pattern_counts.items():
            results.append({
                'region_level': region_level,
                'region_name': region_name,
                'pattern': pattern,
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


def calculate_pattern_lift(
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
    global_lookup = global_freq.set_index('pattern')[['village_count', 'frequency']].to_dict('index')

    # Add global stats and compute lift
    regional_freq = regional_freq.copy()

    regional_freq['global_village_count'] = regional_freq['pattern'].map(
        lambda p: global_lookup.get(p, {}).get('village_count', 0)
    )
    regional_freq['global_frequency'] = regional_freq['pattern'].map(
        lambda p: global_lookup.get(p, {}).get('frequency', 0.0)
    )

    # Compute lift (avoid division by zero)
    regional_freq['lift_vs_global'] = np.where(
        regional_freq['global_frequency'] > 0,
        regional_freq['frequency'] / regional_freq['global_frequency'],
        np.nan
    )

    logger.info("Calculated lift values for regional pattern frequencies")

    return regional_freq
