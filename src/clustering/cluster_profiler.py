"""
Cluster Profiler for Interpretable Cluster Descriptions.

Generates human-readable cluster profiles with distinguishing features.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import json


class ClusterProfiler:
    """Generate interpretable cluster profiles."""

    @staticmethod
    def compute_distinguishing_features(
        X: np.ndarray,
        labels: np.ndarray,
        feature_names: List[str],
        top_n: int = 10
    ) -> Dict[int, List[Tuple[str, float]]]:
        """
        Compute distinguishing features for each cluster.

        Method:
        1. Calculate cluster mean for each feature
        2. Calculate z-score difference from global mean
        3. Return top N positive and negative features

        Args:
            X: Feature matrix (n_samples, n_features)
            labels: Cluster assignments (n_samples,)
            feature_names: List of feature names
            top_n: Number of top features to return

        Returns:
            Dict mapping cluster_id to list of (feature_name, z_score) tuples
        """
        global_mean = X.mean(axis=0)
        global_std = X.std(axis=0) + 1e-10  # Avoid division by zero

        profiles = {}

        for cluster_id in np.unique(labels):
            cluster_mask = labels == cluster_id
            cluster_data = X[cluster_mask]
            cluster_mean = cluster_data.mean(axis=0)

            # Calculate z-score difference
            z_scores = (cluster_mean - global_mean) / global_std

            # Get top positive and negative features
            feature_scores = list(zip(feature_names, z_scores))
            feature_scores.sort(key=lambda x: abs(x[1]), reverse=True)

            profiles[int(cluster_id)] = feature_scores[:top_n]

        return profiles

    @staticmethod
    def identify_representative_regions(
        region_df: pd.DataFrame,
        labels: np.ndarray,
        distances: np.ndarray,
        top_n: int = 5
    ) -> Dict[int, List[str]]:
        """
        Find representative regions for each cluster.

        Method: Select regions closest to cluster centroid.

        Args:
            region_df: DataFrame with region_name
            labels: Cluster assignments
            distances: Distance to centroid for each region
            top_n: Number of representative regions

        Returns:
            Dict mapping cluster_id to list of region names
        """
        representatives = {}

        for cluster_id in np.unique(labels):
            cluster_mask = labels == cluster_id
            cluster_regions = region_df[cluster_mask].copy()
            cluster_distances = distances[cluster_mask]

            # Sort by distance (ascending)
            cluster_regions['distance'] = cluster_distances
            cluster_regions = cluster_regions.sort_values('distance')

            # Get top N closest regions
            top_regions = cluster_regions.head(top_n)['region_name'].tolist()
            representatives[int(cluster_id)] = top_regions

        return representatives

    @staticmethod
    def generate_cluster_profiles(
        X: np.ndarray,
        labels: np.ndarray,
        region_df: pd.DataFrame,
        feature_names: List[str],
        distances: np.ndarray,
        top_n_features: int = 10,
        top_n_regions: int = 5
    ) -> pd.DataFrame:
        """
        Generate complete cluster profiles.

        Args:
            X: Feature matrix
            labels: Cluster assignments
            region_df: DataFrame with region info
            feature_names: List of feature names
            distances: Distance to centroid
            top_n_features: Number of top features
            top_n_regions: Number of representative regions

        Returns:
            DataFrame with columns:
            - cluster_id
            - cluster_size
            - top_features_json
            - top_semantic_categories_json
            - top_suffixes_json
            - representative_regions_json
        """
        # Compute distinguishing features
        feature_profiles = ClusterProfiler.compute_distinguishing_features(
            X, labels, feature_names, top_n_features
        )

        # Identify representative regions
        representatives = ClusterProfiler.identify_representative_regions(
            region_df, labels, distances, top_n_regions
        )

        # Build profile DataFrame
        profiles = []

        for cluster_id in np.unique(labels):
            cluster_size = int((labels == cluster_id).sum())
            features = feature_profiles[int(cluster_id)]

            # Separate semantic and suffix features
            semantic_features = [(f, s) for f, s in features if f.startswith('sem_')]
            suffix_features = [(f, s) for f, s in features if f.startswith('suf')]

            # Extract semantic categories
            semantic_categories = {}
            for feat_name, score in semantic_features:
                # Extract category from feature name (e.g., 'sem_mountain_intensity' -> 'mountain')
                parts = feat_name.split('_')
                if len(parts) >= 2:
                    category = parts[1]
                    if category not in semantic_categories:
                        semantic_categories[category] = []
                    semantic_categories[category].append(float(score))

            # Average scores for each category
            semantic_summary = {cat: float(np.mean(scores))
                              for cat, scores in semantic_categories.items()}

            profiles.append({
                'cluster_id': int(cluster_id),
                'cluster_size': cluster_size,
                'top_features_json': json.dumps([(f, float(s)) for f, s in features], ensure_ascii=False),
                'top_semantic_categories_json': json.dumps(semantic_summary, ensure_ascii=False),
                'top_suffixes_json': json.dumps([(f, float(s)) for f, s in suffix_features[:10]], ensure_ascii=False),
                'representative_regions_json': json.dumps(representatives[int(cluster_id)], ensure_ascii=False)
            })

        return pd.DataFrame(profiles)
