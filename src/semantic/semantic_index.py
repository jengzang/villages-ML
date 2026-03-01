"""
Semantic intensity index calculator.

Calculates semantic intensity indices for regions based on village name composition.
"""

import pandas as pd
import numpy as np
from typing import Set
from .lexicon_loader import SemanticLexicon


class SemanticIndexCalculator:
    """Calculate semantic intensity indices for regions."""

    def __init__(self, lexicon: SemanticLexicon):
        """
        Initialize with semantic lexicon.

        Args:
            lexicon: SemanticLexicon instance
        """
        self.lexicon = lexicon

    def calculate_semantic_scores(self, villages_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate semantic scores for each village.

        For village i:
        semantic_score_i(C) = |S_i ∩ Lexicon_C|

        Where S_i = set of unique characters in village name

        Args:
            villages_df: DataFrame with columns: 自然村, 市级 (or 县区级, 乡镇)
                         Optionally: 市级, 区县级, 乡镇级 for full hierarchy
                         Or: city, county, township (English names)

        Returns:
            DataFrame with columns:
              - village_name
              - region_name
              - city (if available)
              - county (if available)
              - township (if available)
              - mountain_score
              - water_score
              - settlement_score
              - direction_score
              - clan_score
              - symbolic_score
              - agriculture_score
              - vegetation_score
              - infrastructure_score
        """
        results = []

        for _, row in villages_df.iterrows():
            village_name = row['自然村']

            # Get unique characters in village name
            unique_chars = set(village_name)

            # Calculate score for each category
            scores = {'village_name': village_name}

            # Preserve full hierarchy if available (support both Chinese and English column names)
            if 'city' in row:
                scores['city'] = row['city']
            elif '市级' in row:
                scores['city'] = row['市级']

            if 'county' in row:
                scores['county'] = row['county']
            elif '区县级' in row:
                scores['county'] = row['区县级']

            if 'township' in row:
                scores['township'] = row['township']
            elif '乡镇级' in row:
                scores['township'] = row['乡镇级']

            # Determine region_name (for backward compatibility)
            if 'city' in scores:
                scores['region_name'] = scores['city']
            elif 'county' in scores:
                scores['region_name'] = scores['county']
            elif 'township' in scores:
                scores['region_name'] = scores['township']
            elif '市级' in row:
                scores['region_name'] = row['市级']
            elif '区县级' in row:
                scores['region_name'] = row['区县级']
            elif '乡镇' in row:
                scores['region_name'] = row['乡镇']
            else:
                scores['region_name'] = 'unknown'

            # Calculate scores for each category
            for category in self.lexicon.list_categories():
                category_chars = set(self.lexicon.get_lexicon(category))
                # Count intersection
                score = len(unique_chars & category_chars)
                scores[f'{category}_score'] = score

            results.append(scores)

        return pd.DataFrame(results)

    def calculate_regional_indices(self, village_scores: pd.DataFrame,
                                   level_column: str = 'region_name') -> pd.DataFrame:
        """
        Calculate semantic intensity indices for each region.

        SemanticIntensity(C, g) = (Σ semantic_score_i(C)) / N_g

        NormalizedIndex(C, g) = SemanticIntensity(C, g) / GlobalSemanticIntensity(C)

        Args:
            village_scores: DataFrame from calculate_semantic_scores
            level_column: Column name for region grouping

        Returns:
            DataFrame with columns:
              - region_name
              - city (if available)
              - county (if available)
              - township (if available)
              - category
              - raw_intensity
              - normalized_index
              - z_score
              - rank_within_province
        """
        # Get category columns
        category_columns = [col for col in village_scores.columns if col.endswith('_score')]
        categories = [col.replace('_score', '') for col in category_columns]

        # Calculate global intensities
        global_intensities = {}
        total_villages = len(village_scores)

        for category in categories:
            score_col = f'{category}_score'
            global_sum = village_scores[score_col].sum()
            global_intensities[category] = global_sum / total_villages if total_villages > 0 else 0.0

        # Determine grouping columns (use full hierarchy if available)
        group_cols = [level_column]
        hierarchy_cols = []

        if 'city' in village_scores.columns:
            hierarchy_cols.append('city')
        if 'county' in village_scores.columns:
            hierarchy_cols.append('county')
        if 'township' in village_scores.columns:
            hierarchy_cols.append('township')

        # If we have hierarchy columns, group by them instead of just region_name
        if hierarchy_cols:
            group_cols = hierarchy_cols

        # Calculate regional intensities
        results = []

        for group_key, region_df in village_scores.groupby(group_cols):
            n_villages = len(region_df)

            # Extract hierarchy values
            if isinstance(group_key, tuple):
                hierarchy_values = dict(zip(group_cols, group_key))
            else:
                hierarchy_values = {group_cols[0]: group_key}

            # Get region_name from the first row
            region_name = region_df[level_column].iloc[0]

            for category in categories:
                score_col = f'{category}_score'
                regional_sum = region_df[score_col].sum()
                raw_intensity = regional_sum / n_villages if n_villages > 0 else 0.0

                # Normalized index
                global_intensity = global_intensities[category]
                normalized_index = raw_intensity / global_intensity if global_intensity > 0 else 0.0

                # Z-score (comparing regional to global)
                z_score = self._compute_z_score(
                    regional_sum, n_villages, global_intensity, total_villages
                )

                result = {
                    'region_name': region_name,
                    'category': category,
                    'raw_intensity': float(raw_intensity),
                    'normalized_index': float(normalized_index),
                    'z_score': float(z_score)
                }

                # Add hierarchy columns if available
                for col in hierarchy_cols:
                    if col in hierarchy_values:
                        result[col] = hierarchy_values[col]

                results.append(result)

        result_df = pd.DataFrame(results)

        # Add rank within province
        result_df['rank_within_province'] = result_df.groupby('category')['raw_intensity'].rank(
            ascending=False, method='dense'
        ).astype(int)

        # Sort by region and rank
        sort_cols = hierarchy_cols if hierarchy_cols else ['region_name']
        sort_cols.append('rank_within_province')
        result_df = result_df.sort_values(sort_cols).reset_index(drop=True)

        return result_df

    def _compute_z_score(self, regional_sum: float, n_regional: int,
                        global_intensity: float, n_global: int) -> float:
        """
        Compute z-score for regional semantic intensity.

        Args:
            regional_sum: Sum of scores in region
            n_regional: Number of villages in region
            global_intensity: Global average intensity
            n_global: Total number of villages

        Returns:
            Z-score
        """
        if n_regional == 0:
            return 0.0

        # Expected sum under null hypothesis
        expected_sum = n_regional * global_intensity

        # Variance (approximation)
        # Assuming scores are roughly independent
        variance = n_regional * global_intensity

        if variance < 1e-10:
            return 0.0

        return (regional_sum - expected_sum) / np.sqrt(variance)
