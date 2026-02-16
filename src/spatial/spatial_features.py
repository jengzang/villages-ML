"""
Spatial Feature Extraction.

Extracts spatial features for each village based on geographic location.
"""

import numpy as np
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SpatialFeatureExtractor:
    """Extract spatial features for villages."""

    def __init__(self):
        """Initialize feature extractor."""
        pass

    def extract_features(
        self,
        df: pd.DataFrame,
        coords: np.ndarray,
        labels: np.ndarray,
        nn_distances: np.ndarray,
        local_density: dict
    ) -> pd.DataFrame:
        """
        Extract spatial features for each village.

        Args:
            df: DataFrame with village data
            coords: Array of shape (n_points, 2) with [latitude, longitude]
            labels: Cluster labels from DBSCAN
            nn_distances: Array of shape (n_points, k) with k-NN distances
            local_density: Dict with density counts at different radii

        Returns:
            DataFrame with spatial features
        """
        logger.info(f"Extracting spatial features for {len(df)} villages")

        # Create features DataFrame
        features_df = df.copy()

        # Add coordinates
        features_df['longitude'] = coords[:, 1]
        features_df['latitude'] = coords[:, 0]

        # Add nearest neighbor distances
        if nn_distances.shape[1] >= 1:
            features_df['nn_distance_1'] = nn_distances[:, 0]
        if nn_distances.shape[1] >= 5:
            features_df['nn_distance_5'] = nn_distances[:, 4]
        if nn_distances.shape[1] >= 10:
            features_df['nn_distance_10'] = nn_distances[:, 9]

        # Add local density
        features_df['local_density_1km'] = local_density.get('1km', [0] * len(df))
        features_df['local_density_5km'] = local_density.get('5km', [0] * len(df))
        features_df['local_density_10km'] = local_density.get('10km', [0] * len(df))

        # Add cluster assignment
        features_df['spatial_cluster_id'] = labels

        # Calculate cluster size
        cluster_sizes = pd.Series(labels).value_counts().to_dict()
        features_df['cluster_size'] = features_df['spatial_cluster_id'].map(cluster_sizes)
        features_df['cluster_size'] = features_df['cluster_size'].fillna(0).astype(int)

        # Calculate isolation score
        features_df['isolation_score'] = self._calculate_isolation(
            nn_distances, features_df['local_density_5km'].values
        )

        # Mark isolated villages (>10km from nearest neighbor)
        features_df['is_isolated'] = (features_df['nn_distance_1'] > 10.0).astype(int)

        logger.info("Spatial feature extraction complete")

        return features_df

    def _calculate_isolation(self, nn_distances: np.ndarray, local_density: np.ndarray) -> np.ndarray:
        """
        Calculate isolation score for each village.

        Isolation score combines:
        - Distance to nearest neighbor (higher = more isolated)
        - Local density (lower = more isolated)

        Args:
            nn_distances: Array of shape (n_points, k) with k-NN distances
            local_density: Array of local density counts

        Returns:
            Array of isolation scores (0-1, higher = more isolated)
        """
        # Use first nearest neighbor distance
        nn_dist = nn_distances[:, 0]

        # Normalize distance (0-1)
        nn_dist_norm = (nn_dist - nn_dist.min()) / (nn_dist.max() - nn_dist.min() + 1e-10)

        # Normalize density (inverse, so low density = high isolation)
        density_norm = 1 - (local_density - local_density.min()) / (local_density.max() - local_density.min() + 1e-10)

        # Combine (average)
        isolation = (nn_dist_norm + density_norm) / 2

        return isolation

    def aggregate_by_region(
        self,
        features_df: pd.DataFrame,
        region_level: str = 'city'
    ) -> pd.DataFrame:
        """
        Aggregate spatial features by region.

        Args:
            features_df: DataFrame with spatial features
            region_level: Region level ('city', 'county', 'town')

        Returns:
            DataFrame with regional aggregates
        """
        logger.info(f"Aggregating spatial features by {region_level}")

        agg_dict = {
            'village_name': 'count',
            'nn_distance_1': 'mean',
            'local_density_5km': 'mean',
            'isolation_score': 'mean',
            'is_isolated': 'sum'
        }

        agg_df = features_df.groupby(region_level).agg(agg_dict).reset_index()

        # Rename columns
        agg_df.columns = [
            region_level,
            'total_villages',
            'avg_nn_distance',
            'avg_local_density',
            'avg_isolation_score',
            'n_isolated_villages'
        ]

        logger.info(f"Generated aggregates for {len(agg_df)} {region_level}s")

        return agg_df
