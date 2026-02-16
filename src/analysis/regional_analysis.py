"""Regional tendency analysis with statistical metrics."""

import logging
import numpy as np
import pandas as pd
from typing import Optional
from scipy import stats

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


def compute_chi_square_significance(
    n_region: int,
    N_region: int,
    n_global: int,
    N_global: int
) -> dict:
    """
    Compute chi-square test for character-region association.

    Tests whether the character frequency in the region differs
    significantly from the global frequency.

    Contingency table:
                    Has char    No char     Total
    Region          n_region    N_region-n  N_region
    Other regions   n_other     N_other-n   N_other
    Total           n_global    N_global-n  N_global

    Args:
        n_region: Villages with char in region
        N_region: Total villages in region
        n_global: Villages with char globally
        N_global: Total villages globally

    Returns:
        Dictionary with:
        - chi_square_statistic: Chi-square test statistic
        - p_value: P-value
        - is_significant: Whether p < 0.05
        - significance_level: '***' (p<0.001), '**' (p<0.01), '*' (p<0.05), 'ns'
        - effect_size: Cramér's V
        - effect_size_interpretation: 'small', 'medium', 'large'
    """
    # Calculate other regions
    n_other = n_global - n_region
    N_other = N_global - N_region

    # Contingency table
    observed = np.array([
        [n_region, N_region - n_region],
        [n_other, N_other - n_other]
    ])

    # Perform chi-square test
    try:
        chi2, p_value, dof, expected = stats.chi2_contingency(observed)
    except (ValueError, ZeroDivisionError):
        # Handle edge cases
        return {
            'chi_square_statistic': 0.0,
            'p_value': 1.0,
            'is_significant': False,
            'significance_level': 'ns',
            'effect_size': 0.0,
            'effect_size_interpretation': 'none'
        }

    # Determine significance level
    if p_value < 0.001:
        sig_level = '***'
    elif p_value < 0.01:
        sig_level = '**'
    elif p_value < 0.05:
        sig_level = '*'
    else:
        sig_level = 'ns'

    # Calculate Cramér's V (effect size)
    # V = sqrt(chi2 / (n * min(r-1, c-1)))
    n_total = N_global
    min_dim = min(observed.shape[0] - 1, observed.shape[1] - 1)
    cramers_v = np.sqrt(chi2 / (n_total * min_dim)) if n_total > 0 and min_dim > 0 else 0.0

    # Interpret effect size (Cohen's guidelines)
    if cramers_v < 0.1:
        effect_interpretation = 'small'
    elif cramers_v < 0.3:
        effect_interpretation = 'medium'
    else:
        effect_interpretation = 'large'

    return {
        'chi_square_statistic': float(chi2),
        'p_value': float(p_value),
        'is_significant': p_value < 0.05,
        'significance_level': sig_level,
        'effect_size': float(cramers_v),
        'effect_size_interpretation': effect_interpretation
    }


def compute_confidence_interval(
    n_region: int,
    N_region: int,
    confidence_level: float = 0.95
) -> tuple:
    """
    Compute confidence interval for regional frequency using Wilson score interval.

    Args:
        n_region: Villages with char in region
        N_region: Total villages in region
        confidence_level: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if N_region == 0:
        return (0.0, 0.0)

    p = n_region / N_region
    z = stats.norm.ppf((1 + confidence_level) / 2)

    # Wilson score interval
    denominator = 1 + z**2 / N_region
    center = (p + z**2 / (2 * N_region)) / denominator
    margin = z * np.sqrt(p * (1 - p) / N_region + z**2 / (4 * N_region**2)) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return (float(lower), float(upper))


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


def compute_tendency_significance(
    tendency_df: pd.DataFrame,
    compute_ci: bool = True,
    confidence_level: float = 0.95
) -> pd.DataFrame:
    """
    Compute statistical significance for tendency analysis results.

    Adds the following columns:
    - chi_square_statistic: Chi-square test statistic
    - p_value: P-value from chi-square test
    - is_significant: Boolean flag (p < 0.05)
    - significance_level: '***', '**', '*', or 'ns'
    - effect_size: Cramér's V
    - effect_size_interpretation: 'small', 'medium', 'large'
    - ci_lower: Lower bound of 95% confidence interval (optional)
    - ci_upper: Upper bound of 95% confidence interval (optional)

    Args:
        tendency_df: DataFrame with tendency analysis results
        compute_ci: Whether to compute confidence intervals
        confidence_level: Confidence level for CI (default 0.95)

    Returns:
        DataFrame with significance testing columns added
    """
    df = tendency_df.copy()

    logger.info(f"Computing statistical significance for {len(df)} char-region pairs")

    # Compute chi-square significance for each row
    significance_results = df.apply(
        lambda row: compute_chi_square_significance(
            n_region=row['village_count'],
            N_region=row['total_villages'],
            n_global=row['global_village_count'],
            N_global=row.get('global_total_villages', row['total_villages'])  # Fallback if not present
        ),
        axis=1
    )

    # Extract significance columns
    df['chi_square_statistic'] = significance_results.apply(lambda x: x['chi_square_statistic'])
    df['p_value'] = significance_results.apply(lambda x: x['p_value'])
    df['is_significant'] = significance_results.apply(lambda x: x['is_significant'])
    df['significance_level'] = significance_results.apply(lambda x: x['significance_level'])
    df['effect_size'] = significance_results.apply(lambda x: x['effect_size'])
    df['effect_size_interpretation'] = significance_results.apply(lambda x: x['effect_size_interpretation'])

    # Compute confidence intervals if requested
    if compute_ci:
        ci_results = df.apply(
            lambda row: compute_confidence_interval(
                n_region=row['village_count'],
                N_region=row['total_villages'],
                confidence_level=confidence_level
            ),
            axis=1
        )
        df['ci_lower'] = ci_results.apply(lambda x: x[0])
        df['ci_upper'] = ci_results.apply(lambda x: x[1])

    # Log summary statistics
    n_significant = df['is_significant'].sum()
    pct_significant = (n_significant / len(df) * 100) if len(df) > 0 else 0
    logger.info(f"Significance testing complete: {n_significant}/{len(df)} ({pct_significant:.1f}%) are significant (p < 0.05)")

    # Log effect size distribution
    effect_counts = df['effect_size_interpretation'].value_counts()
    logger.info(f"Effect size distribution: {effect_counts.to_dict()}")

    return df
