"""Regional tendency analysis with statistical metrics."""

import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


def apply_smoothing(n: int, N: int, alpha: float = 1.0) -> float:
    """
    Apply Laplace smoothing to frequency estimate.

    p_smoothed = (n + alpha) / (N + 2*alpha)

    Args:
        n: Count in region
        N: Total in region
        alpha: Smoothing parameter

    Returns:
        Smoothed probability
    """
    return (n + alpha) / (N + 2 * alpha)


def compute_log_odds(p_region: float, p_global: float, alpha: float = 1.0) -> float:
    """
    Compute log-odds ratio with smoothing.

    log_odds = log((p_region + alpha) / (1 - p_region + alpha)) -
               log((p_global + alpha) / (1 - p_global + alpha))

    Args:
        p_region: Regional frequency
        p_global: Global frequency
        alpha: Smoothing parameter

    Returns:
        Log-odds ratio
    """
    # Apply smoothing to avoid log(0)
    p_r_smooth = min(max(p_region, 1e-10), 1 - 1e-10)
    p_g_smooth = min(max(p_global, 1e-10), 1 - 1e-10)

    odds_region = p_r_smooth / (1 - p_r_smooth)
    odds_global = p_g_smooth / (1 - p_g_smooth)

    return np.log(odds_region) - np.log(odds_global)


def compute_z_score(n_region: int, N_region: int, p_global: float) -> float:
    """
    Compute z-score for regional vs global frequency.

    Under null hypothesis (regional = global):
    E[n] = N_region * p_global
    Var[n] = N_region * p_global * (1 - p_global)
    z = (n_region - E) / sqrt(Var)

    Args:
        n_region: Count in region
        N_region: Total villages in region
        p_global: Global frequency

    Returns:
        Z-score
    """
    expected = N_region * p_global
    variance = N_region * p_global * (1 - p_global)

    if variance < 1e-10:
        return 0.0

    return (n_region - expected) / np.sqrt(variance)


def filter_by_support(
    df: pd.DataFrame,
    min_global: int = 20,
    min_regional: int = 5
) -> pd.DataFrame:
    """
    Filter characters by minimum support thresholds.

    Args:
        df: DataFrame with columns [global_village_count, village_count]
        min_global: Minimum global village count
        min_regional: Minimum regional village count

    Returns:
        Filtered DataFrame with support_flag column
    """
    df = df.copy()

    df['support_flag'] = (
        (df['global_village_count'] >= min_global) &
        (df['village_count'] >= min_regional)
    )

    before = len(df)
    after = df['support_flag'].sum()

    logger.info(f"Support filtering: {after}/{before} chars pass thresholds")

    return df


def compute_regional_tendency(
    char_freq_df: pd.DataFrame,
    smoothing_alpha: float = 1.0,
    min_global_support: int = 20,
    min_regional_support: int = 5,
    compute_z: bool = True
) -> pd.DataFrame:
    """
    Compute regional tendency metrics.

    Adds the following columns:
    - lift: p_region / p_global
    - log_lift: log(lift)
    - log_odds: Log-odds ratio with smoothing
    - z_score: Statistical significance (if compute_z=True)
    - support_flag: Whether char meets support thresholds
    - rank_overrepresented: Rank by lift (descending)
    - rank_underrepresented: Rank by lift (ascending)

    Args:
        char_freq_df: Regional frequency DataFrame with global stats
        smoothing_alpha: Laplace smoothing parameter
        min_global_support: Minimum global village count
        min_regional_support: Minimum regional village count
        compute_z: Whether to compute z-scores

    Returns:
        DataFrame with tendency metrics
    """
    df = char_freq_df.copy()

    logger.info(f"Computing regional tendency for {len(df)} char-region pairs")

    # Compute lift (already in char_freq_df as lift_vs_global)
    df['lift'] = df['lift_vs_global']
    df['log_lift'] = np.log(df['lift'].replace(0, np.nan))

    # Compute log-odds
    df['log_odds'] = df.apply(
        lambda row: compute_log_odds(row['frequency'], row['global_frequency'], smoothing_alpha),
        axis=1
    )

    # Compute z-score
    if compute_z:
        df['z_score'] = df.apply(
            lambda row: compute_z_score(
                row['village_count'],
                row['total_villages'],
                row['global_frequency']
            ),
            axis=1
        )

    # Filter by support
    df = filter_by_support(df, min_global_support, min_regional_support)

    # Add ranks (within each region)
    df['rank_overrepresented'] = df.groupby('region_name')['lift'].rank(
        ascending=False, method='dense'
    ).astype(int)

    df['rank_underrepresented'] = df.groupby('region_name')['lift'].rank(
        ascending=True, method='dense'
    ).astype(int)

    logger.info("Regional tendency computation complete")

    return df
