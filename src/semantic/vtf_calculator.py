"""
Virtual Term Frequency (VTF) calculator for semantic categories.

Calculates semantic category frequencies by aggregating character frequencies.
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from .lexicon_loader import SemanticLexicon


class VTFCalculator:
    """Calculate Virtual Term Frequency for semantic categories."""

    def __init__(self, lexicon: SemanticLexicon):
        """
        Initialize with semantic lexicon.

        Args:
            lexicon: SemanticLexicon instance
        """
        self.lexicon = lexicon

    def calculate_global_vtf(self, char_freq_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate global VTF for each semantic category.

        Args:
            char_freq_df: DataFrame from char_frequency_global table
                         Must have columns: character, village_count, total_villages

        Returns:
            DataFrame with columns:
              - category
              - vtf_count (sum of village_count for chars in category)
              - total_villages
              - frequency (vtf_count / total_villages)
              - rank
        """
        # Get total villages (should be same for all rows)
        total_villages = char_freq_df['total_villages'].iloc[0]

        # Calculate VTF for each category
        results = []

        for category in self.lexicon.list_categories():
            # Get characters in this category
            category_chars = set(self.lexicon.get_lexicon(category))

            # Filter char_freq_df for characters in this category
            category_df = char_freq_df[char_freq_df['character'].isin(category_chars)]

            # Sum village_count
            vtf_count = category_df['village_count'].sum()

            # Calculate frequency
            frequency = vtf_count / total_villages if total_villages > 0 else 0.0

            results.append({
                'category': category,
                'vtf_count': int(vtf_count),
                'total_villages': int(total_villages),
                'frequency': float(frequency)
            })

        # Create DataFrame
        result_df = pd.DataFrame(results)

        # Sort by vtf_count descending and add rank
        result_df = result_df.sort_values('vtf_count', ascending=False).reset_index(drop=True)
        result_df['rank'] = range(1, len(result_df) + 1)

        return result_df

    def calculate_regional_vtf(self, char_freq_df: pd.DataFrame,
                               level: str) -> pd.DataFrame:
        """
        Calculate regional VTF for each semantic category with hierarchical grouping.

        Args:
            char_freq_df: DataFrame from char_frequency_regional table
                         Must have columns: region_level, region_name, character,
                                          village_count, total_villages
                         Optional: city, county, township (for hierarchical grouping)
            level: Region level to filter ('city', 'county', 'township')

        Returns:
            DataFrame with columns:
              - region_level
              - city, county, township (if available in input)
              - region_name
              - category
              - vtf_count
              - total_villages
              - frequency
              - rank_within_region
        """
        # Filter by region level
        level_df = char_freq_df[char_freq_df['region_level'] == level].copy()

        if level_df.empty:
            return pd.DataFrame()

        # Check if hierarchical columns exist
        has_hierarchical = all(col in level_df.columns for col in ['city', 'county', 'township'])

        if has_hierarchical:
            # Use hierarchical grouping to separate duplicate place names
            if level == 'city':
                group_cols = ['city']
            elif level == 'county':
                group_cols = ['city', 'county']
            else:  # township
                group_cols = ['city', 'county', 'township']

            # Get unique regions by hierarchical key
            region_groups = level_df.groupby(group_cols)
        else:
            # Fall back to region_name for backward compatibility
            group_cols = ['region_name']
            region_groups = level_df.groupby('region_name')

        results = []

        for group_key, region_df in region_groups:
            # Extract hierarchical values
            if has_hierarchical:
                if isinstance(group_key, tuple):
                    # Explicit unpacking based on level
                    if level == 'city':
                        city = group_key
                        county = None
                        township = None
                    elif level == 'county':
                        city, county = group_key
                        township = None
                    else:  # township
                        city, county, township = group_key
                else:
                    city = group_key
                    county = None
                    township = None
            else:
                city = None
                county = None
                township = None

            # Get region name for display
            region_name = region_df['region_name'].iloc[0]
            total_villages = region_df['total_villages'].iloc[0]

            # Calculate VTF for each category
            for category in self.lexicon.list_categories():
                # Get characters in this category
                category_chars = set(self.lexicon.get_lexicon(category))

                # Filter for characters in this category
                category_region_df = region_df[region_df['character'].isin(category_chars)]

                # Sum village_count
                vtf_count = category_region_df['village_count'].sum()

                # Calculate frequency
                frequency = vtf_count / total_villages if total_villages > 0 else 0.0

                result = {
                    'region_level': level,
                    'region_name': region_name,
                    'category': category,
                    'vtf_count': int(vtf_count),
                    'total_villages': int(total_villages),
                    'frequency': float(frequency)
                }

                # Add hierarchical columns if available
                if has_hierarchical:
                    result['city'] = city
                    result['county'] = county
                    result['township'] = township

                results.append(result)

        # Create DataFrame
        result_df = pd.DataFrame(results)

        # Add rank within each region using hierarchical grouping
        if has_hierarchical:
            result_df['rank_within_region'] = result_df.groupby(group_cols)['vtf_count'].rank(
                ascending=False, method='dense'
            ).astype(int)
        else:
            result_df['rank_within_region'] = result_df.groupby('region_name')['vtf_count'].rank(
                ascending=False, method='dense'
            ).astype(int)

        # Sort by hierarchical key (or region_name) and rank
        if has_hierarchical:
            sort_cols = group_cols + ['rank_within_region']
        else:
            sort_cols = ['region_name', 'rank_within_region']

        result_df = result_df.sort_values(sort_cols).reset_index(drop=True)

        return result_df

    def calculate_vtf_tendency(self, regional_vtf: pd.DataFrame,
                               global_vtf: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate tendency metrics for semantic categories with hierarchical support.

        Args:
            regional_vtf: DataFrame from calculate_regional_vtf
            global_vtf: DataFrame from calculate_global_vtf

        Returns:
            DataFrame with columns:
              - region_level
              - city, county, township (if available in input)
              - region_name
              - category
              - frequency (regional)
              - global_frequency
              - lift
              - log_lift
              - log_odds
              - z_score
              - vtf_count
              - total_villages
              - support_flag
        """
        # Create global frequency lookup
        global_freq_map = dict(zip(global_vtf['category'], global_vtf['frequency']))

        # Check if hierarchical columns exist
        has_hierarchical = all(col in regional_vtf.columns for col in ['city', 'county', 'township'])

        results = []

        for _, row in regional_vtf.iterrows():
            region_level = row['region_level']
            region_name = row['region_name']
            category = row['category']
            vtf_count = row['vtf_count']
            total_villages = row['total_villages']
            frequency = row['frequency']

            # Get global frequency
            global_frequency = global_freq_map.get(category, 0.0)

            # Calculate lift
            lift = frequency / global_frequency if global_frequency > 0 else 0.0

            # Calculate log_lift
            log_lift = np.log(lift) if lift > 0 else 0.0

            # Calculate log_odds
            log_odds = self._compute_log_odds(frequency, global_frequency)

            # Calculate z_score
            z_score = self._compute_z_score(vtf_count, total_villages, global_frequency)

            # Support flag (categories with reasonable counts)
            support_flag = 1 if vtf_count >= 10 else 0

            result = {
                'region_level': region_level,
                'region_name': region_name,
                'category': category,
                'frequency': float(frequency),
                'global_frequency': float(global_frequency),
                'lift': float(lift),
                'log_lift': float(log_lift),
                'log_odds': float(log_odds),
                'z_score': float(z_score),
                'vtf_count': int(vtf_count),
                'total_villages': int(total_villages),
                'support_flag': int(support_flag)
            }

            # Add hierarchical columns if available
            if has_hierarchical:
                result['city'] = row['city']
                result['county'] = row['county']
                result['township'] = row['township']

            results.append(result)

        result_df = pd.DataFrame(results)

        # Sort by hierarchical key (or region_name) and log_odds descending
        if has_hierarchical:
            # Determine sort columns based on region_level
            if 'region_level' in result_df.columns and len(result_df) > 0:
                region_level = result_df['region_level'].iloc[0]
                if region_level == 'city':
                    sort_cols = ['city', 'log_odds']
                elif region_level == 'county':
                    sort_cols = ['city', 'county', 'log_odds']
                else:  # township
                    sort_cols = ['city', 'county', 'township', 'log_odds']
            else:
                sort_cols = ['city', 'county', 'township', 'log_odds']

            result_df = result_df.sort_values(sort_cols,
                                              ascending=[True] * (len(sort_cols) - 1) + [False]).reset_index(drop=True)
        else:
            result_df = result_df.sort_values(['region_name', 'log_odds'],
                                              ascending=[True, False]).reset_index(drop=True)

        return result_df

    def _compute_log_odds(self, p_region: float, p_global: float) -> float:
        """Compute log-odds ratio with smoothing."""
        # Apply smoothing to avoid log(0)
        p_r_smooth = min(max(p_region, 1e-10), 1 - 1e-10)
        p_g_smooth = min(max(p_global, 1e-10), 1 - 1e-10)

        odds_region = p_r_smooth / (1 - p_r_smooth)
        odds_global = p_g_smooth / (1 - p_g_smooth)

        return np.log(odds_region) - np.log(odds_global)

    def _compute_z_score(self, n_region: int, N_region: int, p_global: float) -> float:
        """Compute z-score for regional vs global frequency."""
        expected = N_region * p_global
        variance = N_region * p_global * (1 - p_global)

        if variance < 1e-10:
            return 0.0

        return (n_region - expected) / np.sqrt(variance)
