"""
Density Analysis for Spatial Features.

Calculates local density and regional aggregates.
"""

import numpy as np
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DensityAnalyzer:
    """Analyze spatial density patterns."""

    def __init__(self):
        """Initialize density analyzer."""
        pass

    def calculate_local_density(
        self,
        distance_calculator,
        coords: np.ndarray,
        radii_km: list = [1, 5, 10]
    ) -> Dict[str, list]:
        """
        Calculate local density at multiple radii.

        Args:
            distance_calculator: DistanceCalculator instance with built tree
            coords: Array of shape (n_points, 2) with [latitude, longitude]
            radii_km: List of radii in kilometers

        Returns:
            Dictionary mapping radius to density counts
        """
        logger.info(f"Calculating local density at radii: {radii_km}km")

        density_dict = {}

        for radius_km in radii_km:
            logger.info(f"Computing density within {radius_km}km")

            # Get neighbors within radius
            distances, indices = distance_calculator.radius_neighbors(coords, radius_km)

            # Count neighbors (excluding self)
            counts = [len(idx) - 1 for idx in indices]  # -1 to exclude self

            density_dict[f'{radius_km}km'] = counts

            logger.info(f"  Mean density: {np.mean(counts):.1f} villages")
            logger.info(f"  Max density: {np.max(counts)} villages")

        return density_dict

    def calculate_regional_aggregates(
        self,
        features_df: pd.DataFrame,
        region_level: str = 'city'
    ) -> pd.DataFrame:
        """
        Calculate spatial aggregates by region.

        Args:
            features_df: DataFrame with spatial features
            region_level: Region level ('city', 'county', 'town')

        Returns:
            DataFrame with regional aggregates
        """
        logger.info(f"Calculating regional spatial aggregates for {region_level}")

        agg_dict = {
            'village_name': 'count',
            'nn_distance_1': 'mean',
            'local_density_5km': 'mean',
            'isolation_score': 'mean',
            'is_isolated': 'sum',
            'spatial_cluster_id': lambda x: x.nunique()
        }

        agg_df = features_df.groupby(region_level).agg(agg_dict).reset_index()

        # Rename columns
        agg_df.columns = [
            'region_name',
            'total_villages',
            'avg_nn_distance',
            'avg_local_density',
            'avg_isolation_score',
            'n_isolated_villages',
            'n_spatial_clusters'
        ]

        # Add region level
        agg_df.insert(0, 'region_level', region_level)

        # Calculate spatial dispersion (coefficient of variation of nn_distance)
        dispersion = features_df.groupby(region_level)['nn_distance_1'].std() / \
                    features_df.groupby(region_level)['nn_distance_1'].mean()
        agg_df['spatial_dispersion'] = dispersion.values

        logger.info(f"Generated aggregates for {len(agg_df)} regions")

        return agg_df

    def calculate_hotspot_coverage(
        self,
        features_df: pd.DataFrame,
        hotspots_df: pd.DataFrame,
        region_level: str = 'city'
    ) -> pd.DataFrame:
        """
        Calculate hotspot coverage by region.

        Args:
            features_df: DataFrame with spatial features
            hotspots_df: DataFrame with hotspot information
            region_level: Region level ('city', 'county', 'town')

        Returns:
            DataFrame with hotspot coverage statistics
        """
        logger.info(f"Calculating hotspot coverage for {region_level}")

        # Count hotspots by region
        hotspot_counts = hotspots_df.groupby(region_level).size().reset_index(name='n_hotspots')

        # Calculate total villages by region
        village_counts = features_df.groupby(region_level).size().reset_index(name='total_villages')

        # Merge
        coverage_df = pd.merge(village_counts, hotspot_counts, on=region_level, how='left')
        coverage_df['n_hotspots'] = coverage_df['n_hotspots'].fillna(0).astype(int)

        # Calculate coverage ratio
        coverage_df['hotspot_coverage'] = coverage_df['n_hotspots'] / coverage_df['total_villages']

        logger.info(f"Generated hotspot coverage for {len(coverage_df)} regions")

        return coverage_df
