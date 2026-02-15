"""
Region Feature Builder for Clustering.

Constructs feature vectors from semantic and morphological data.
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json

from ..data.db_query import (
    get_semantic_vtf_regional,
    get_pattern_frequency_regional,
    get_regional_frequency
)


class RegionFeatureBuilder:
    """Build region feature vectors from database."""

    # Semantic categories (9 categories)
    SEMANTIC_CATEGORIES = [
        'mountain', 'water', 'direction', 'settlement',
        'clan', 'infrastructure', 'symbolic', 'nature', 'other'
    ]

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize feature builder.

        Args:
            conn: Database connection
        """
        self.conn = conn

    def build_semantic_features(
        self,
        run_id: str,
        region_level: str
    ) -> pd.DataFrame:
        """
        Build semantic features from VTF and tendency data.

        For each of 9 semantic categories, creates 3 features:
        - intensity: VTF frequency (normalized)
        - coverage: Binary presence (>0 = 1)
        - lift: Tendency lift value

        Total: 27 features

        Args:
            run_id: Semantic analysis run ID
            region_level: 'city', 'county', or 'town'

        Returns:
            DataFrame with columns: region_name, sem_*_intensity, sem_*_coverage, sem_*_lift
        """
        # Get VTF data
        vtf_df = get_semantic_vtf_regional(self.conn, run_id, region_level)

        if vtf_df.empty:
            raise ValueError(f"No semantic VTF data found for run_id={run_id}, region_level={region_level}")

        # Pivot to wide format
        features = []

        for category in self.SEMANTIC_CATEGORIES:
            cat_data = vtf_df[vtf_df['category'] == category].copy()

            if cat_data.empty:
                continue

            # Intensity: normalized VTF frequency
            intensity = cat_data.set_index('region_name')['frequency'].to_dict()

            # Coverage: binary presence
            coverage = {rid: 1 if freq > 0 else 0 for rid, freq in intensity.items()}

            # Lift: tendency value (if available)
            if 'lift' in cat_data.columns:
                lift = cat_data.set_index('region_name')['lift'].to_dict()
            else:
                lift = {rid: 0.0 for rid in intensity.keys()}

            features.append({
                'category': category,
                'intensity': intensity,
                'coverage': coverage,
                'lift': lift
            })

        # Build feature matrix
        all_regions = vtf_df[['region_name']].drop_duplicates()
        result = all_regions.copy()

        for feat in features:
            cat = feat['category']
            result[f'sem_{cat}_intensity'] = result['region_name'].map(feat['intensity']).fillna(0)
            result[f'sem_{cat}_coverage'] = result['region_name'].map(feat['coverage']).fillna(0)
            result[f'sem_{cat}_lift'] = result['region_name'].map(feat['lift']).fillna(0)

        return result

    def build_morphology_features(
        self,
        run_id: str,
        region_level: str,
        top_n_suffix2: int = 100,
        top_n_suffix3: int = 100
    ) -> pd.DataFrame:
        """
        Build morphology features from suffix patterns.

        Steps:
        1. Query global top N suffixes (suffix_2, suffix_3)
        2. For each region, calculate occurrence rate of these suffixes
        3. Output: suf2_村_rate, suf2_涌_rate, suf3_坑尾_rate, ...

        Args:
            run_id: Morphology analysis run ID
            region_level: 'city', 'county', or 'town'
            top_n_suffix2: Number of top bigram suffixes to use
            top_n_suffix3: Number of top trigram suffixes to use

        Returns:
            DataFrame with columns: region_name, suf2_*_rate, suf3_*_rate
        """
        # Get pattern frequency data for suffix_2 and suffix_3
        suffix2_df = get_pattern_frequency_regional(self.conn, run_id, 'suffix_2', region_level)
        suffix3_df = get_pattern_frequency_regional(self.conn, run_id, 'suffix_3', region_level)

        if suffix2_df.empty and suffix3_df.empty:
            raise ValueError(f"No pattern frequency data found for run_id={run_id}, region_level={region_level}")

        # Calculate global frequency for each pattern
        suffix2_global = suffix2_df.groupby('pattern')['frequency'].sum().sort_values(ascending=False)
        suffix3_global = suffix3_df.groupby('pattern')['frequency'].sum().sort_values(ascending=False)

        top_suffix2 = suffix2_global.head(top_n_suffix2).index.tolist()
        top_suffix3 = suffix3_global.head(top_n_suffix3).index.tolist()

        # Build feature matrix
        all_regions = pd.concat([suffix2_df[['region_name']], suffix3_df[['region_name']]]).drop_duplicates()
        result = all_regions.copy()

        # Add suffix2 features
        for suffix in top_suffix2:
            suffix_data = suffix2_df[suffix2_df['pattern'] == suffix].set_index('region_name')['frequency']
            result[f'suf2_{suffix}_rate'] = result['region_name'].map(suffix_data).fillna(0)

        # Add suffix3 features
        for suffix in top_suffix3:
            suffix_data = suffix3_df[suffix3_df['pattern'] == suffix].set_index('region_name')['frequency']
            result[f'suf3_{suffix}_rate'] = result['region_name'].map(suffix_data).fillna(0)

        return result

    def build_diversity_features(
        self,
        semantic_df: pd.DataFrame,
        morphology_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate diversity metrics.

        Features:
        - meta_suffix2_entropy: Suffix diversity entropy
        - meta_mw_balance: Mountain-water balance index
        - meta_semantic_diversity: Semantic category diversity

        Args:
            semantic_df: DataFrame with semantic features
            morphology_df: DataFrame with morphology features

        Returns:
            DataFrame with columns: region_name, meta_*_entropy, meta_*_balance
        """
        result = semantic_df[['region_name']].copy()

        # Calculate suffix2 entropy
        suffix2_cols = [col for col in morphology_df.columns if col.startswith('suf2_')]
        if suffix2_cols:
            suffix2_data = morphology_df[['region_name'] + suffix2_cols].set_index('region_name')
            entropy = suffix2_data.apply(lambda row: self._calculate_entropy(row.values), axis=1)
            result['meta_suffix2_entropy'] = result['region_name'].map(entropy).fillna(0)
        else:
            result['meta_suffix2_entropy'] = 0

        # Calculate mountain-water balance
        if 'sem_mountain_intensity' in semantic_df.columns and 'sem_water_intensity' in semantic_df.columns:
            mountain = semantic_df.set_index('region_name')['sem_mountain_intensity']
            water = semantic_df.set_index('region_name')['sem_water_intensity']
            balance = (mountain - water).abs() / (mountain + water + 1e-6)
            result['meta_mw_balance'] = result['region_name'].map(balance).fillna(0)
        else:
            result['meta_mw_balance'] = 0

        # Calculate semantic diversity
        sem_intensity_cols = [col for col in semantic_df.columns if col.endswith('_intensity')]
        if sem_intensity_cols:
            sem_data = semantic_df[['region_name'] + sem_intensity_cols].set_index('region_name')
            diversity = sem_data.apply(lambda row: self._calculate_entropy(row.values), axis=1)
            result['meta_semantic_diversity'] = result['region_name'].map(diversity).fillna(0)
        else:
            result['meta_semantic_diversity'] = 0

        return result

    @staticmethod
    def _calculate_entropy(values: np.ndarray) -> float:
        """Calculate Shannon entropy of a distribution."""
        values = np.array(values)
        values = values[values > 0]  # Remove zeros
        if len(values) == 0:
            return 0.0
        probs = values / values.sum()
        return -np.sum(probs * np.log2(probs + 1e-10))

    def build_region_vectors(
        self,
        semantic_run_id: str,
        morphology_run_id: str,
        region_level: str,
        use_semantic: bool = True,
        use_morphology: bool = True,
        use_diversity: bool = True,
        top_n_suffix2: int = 100,
        top_n_suffix3: int = 100
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Build complete region feature vectors.

        Combines semantic, morphology, and diversity features.

        Args:
            semantic_run_id: Semantic analysis run ID
            morphology_run_id: Morphology analysis run ID
            region_level: 'city', 'county', or 'town'
            use_semantic: Include semantic features
            use_morphology: Include morphology features
            use_diversity: Include diversity features
            top_n_suffix2: Number of top bigram suffixes
            top_n_suffix3: Number of top trigram suffixes

        Returns:
            Tuple of (feature_df, feature_names)
            - feature_df: DataFrame with all features
            - feature_names: List of feature column names
        """
        # Start with base region info
        result = None
        feature_names = []

        # Build semantic features
        if use_semantic:
            semantic_df = self.build_semantic_features(semantic_run_id, region_level)
            result = semantic_df
            feature_names.extend([col for col in semantic_df.columns
                                 if col.startswith('sem_')])

        # Build morphology features
        if use_morphology:
            morphology_df = self.build_morphology_features(
                morphology_run_id, region_level, top_n_suffix2, top_n_suffix3
            )

            if result is None:
                result = morphology_df
            else:
                result = result.merge(morphology_df, on=['region_name'], how='outer')

            feature_names.extend([col for col in morphology_df.columns
                                 if col.startswith('suf')])

        # Build diversity features
        if use_diversity and use_semantic and use_morphology:
            diversity_df = self.build_diversity_features(semantic_df, morphology_df)

            if result is None:
                result = diversity_df
            else:
                result = result.merge(diversity_df, on=['region_name'], how='outer')

            feature_names.extend([col for col in diversity_df.columns
                                 if col.startswith('meta_')])

        if result is None:
            raise ValueError("No features selected. Enable at least one feature type.")

        # Fill NaN values with 0
        result = result.fillna(0)

        # Add N_villages count from semantic VTF data
        vtf_df = get_semantic_vtf_regional(self.conn, semantic_run_id, region_level)
        village_counts = vtf_df.groupby('region_name')['total_villages'].first().to_dict()
        result['N_villages'] = result['region_name'].map(village_counts).fillna(0).astype(int)

        return result, feature_names

    def _count_villages_in_region(self, region_name: str, region_level: str) -> int:
        """Count number of villages in a region."""
        level_col_map = {
            'city': '市级',
            'county': '县区级',
            'town': '乡镇'
        }

        col_name = level_col_map.get(region_level)
        if not col_name:
            return 0

        query = f"SELECT COUNT(*) FROM 广东省自然村 WHERE `{col_name}` = ?"
        cursor = self.conn.execute(query, (region_name,))
        return cursor.fetchone()[0]

