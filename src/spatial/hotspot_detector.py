"""
Hotspot Detection using Kernel Density Estimation.

Identifies spatial hotspots and naming pattern concentrations.
"""

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class HotspotDetector:
    """Detect spatial hotspots using KDE."""

    def __init__(self, bandwidth_km: float = 5.0, threshold_percentile: float = 95):
        """
        Initialize hotspot detector.

        Args:
            bandwidth_km: KDE bandwidth in kilometers (~0.05 degrees)
            threshold_percentile: Percentile threshold for hotspot detection (default: 95)
        """
        self.bandwidth_deg = bandwidth_km / 111.0  # Rough conversion to degrees
        self.threshold_percentile = threshold_percentile

    def detect_density_hotspots(
        self,
        coords: np.ndarray,
        df: pd.DataFrame,
        sample_size: int = 10000
    ) -> pd.DataFrame:
        """
        Detect high-density hotspots using KDE.

        Args:
            coords: Array of shape (n_points, 2) with [latitude, longitude]
            df: DataFrame with village data
            sample_size: Number of points to sample for KDE evaluation (default: 10000)

        Returns:
            DataFrame with hotspot information
        """
        logger.info("Detecting density hotspots using KDE")

        # Transpose for KDE (expects shape (2, n_points))
        coords_t = coords.T

        # Compute KDE
        logger.info(f"Computing KDE with bandwidth={self.bandwidth_deg:.4f} degrees")
        kde = gaussian_kde(coords_t, bw_method=self.bandwidth_deg)

        # For large datasets, sample points for density evaluation
        n_points = coords.shape[0]
        if n_points > sample_size:
            logger.info(f"Sampling {sample_size} points from {n_points} for density evaluation")
            sample_indices = np.random.choice(n_points, size=sample_size, replace=False)
            eval_coords_t = coords_t[:, sample_indices]
        else:
            eval_coords_t = coords_t
            sample_indices = np.arange(n_points)

        # Evaluate density at sampled points
        density = kde(eval_coords_t)

        # Find threshold
        threshold = np.percentile(density, self.threshold_percentile)
        logger.info(f"Density threshold (p{self.threshold_percentile}): {threshold:.6f}")

        # Identify hotspot points (only among sampled points)
        hotspot_mask = density >= threshold
        n_hotspot_points = hotspot_mask.sum()
        logger.info(f"Found {n_hotspot_points} villages in hotspots (from {len(sample_indices)} sampled)")

        if n_hotspot_points == 0:
            logger.warning("No hotspots detected")
            return pd.DataFrame()

        # Get hotspot coordinates and data (from sampled points)
        hotspot_sample_indices = sample_indices[hotspot_mask]
        hotspot_coords = coords[hotspot_sample_indices]
        hotspot_df = df.iloc[hotspot_sample_indices].copy()
        hotspot_df['density_score'] = density[hotspot_mask]

        # Cluster hotspot points to identify distinct hotspots
        hotspots = self._cluster_hotspot_points(hotspot_coords, hotspot_df)

        logger.info(f"Identified {len(hotspots)} distinct density hotspots")

        return pd.DataFrame(hotspots)

    def _cluster_hotspot_points(
        self,
        coords: np.ndarray,
        df: pd.DataFrame
    ) -> List[Dict]:
        """
        Cluster hotspot points into distinct hotspots.

        Args:
            coords: Hotspot coordinates
            df: Hotspot DataFrame

        Returns:
            List of hotspot dictionaries
        """
        from sklearn.cluster import DBSCAN

        # Cluster hotspot points (eps=0.05 degrees ≈ 5km)
        clusterer = DBSCAN(eps=0.05, min_samples=3, metric='euclidean')
        labels = clusterer.fit_predict(coords)

        hotspots = []
        for cluster_id in set(labels):
            if cluster_id == -1:
                continue  # Skip noise

            mask = labels == cluster_id
            cluster_coords = coords[mask]
            cluster_df = df[mask]

            # Calculate hotspot center
            center_lat = cluster_coords[:, 0].mean()
            center_lon = cluster_coords[:, 1].mean()

            # Calculate radius (max distance from center)
            distances = np.sqrt(
                (cluster_coords[:, 0] - center_lat)**2 +
                (cluster_coords[:, 1] - center_lon)**2
            )
            radius_deg = distances.max()
            radius_km = radius_deg * 111  # Rough conversion

            # Get density score
            density_score = cluster_df['density_score'].mean()

            # Get dominant region
            city = cluster_df['city'].mode()[0] if len(cluster_df) > 0 else None
            county = cluster_df['county'].mode()[0] if len(cluster_df) > 0 else None

            hotspots.append({
                'hotspot_id': len(hotspots),
                'hotspot_type': 'high_density',
                'center_lat': center_lat,
                'center_lon': center_lon,
                'radius_km': radius_km,
                'village_count': len(cluster_df),
                'density_score': density_score,
                'city': city,
                'county': county,
                'semantic_category': None,
                'pattern': None
            })

        return hotspots

    def detect_naming_hotspots(
        self,
        coords: np.ndarray,
        df: pd.DataFrame,
        semantic_categories: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        Detect hotspots for specific naming patterns.

        Args:
            coords: Array of shape (n_points, 2) with [latitude, longitude]
            df: DataFrame with village data
            semantic_categories: Optional series with semantic category labels

        Returns:
            DataFrame with naming hotspots
        """
        if semantic_categories is None:
            logger.warning("No semantic categories provided, skipping naming hotspot detection")
            return pd.DataFrame()

        logger.info("Detecting naming pattern hotspots")

        hotspots = []

        # Get unique categories
        categories = semantic_categories.unique()
        logger.info(f"Analyzing {len(categories)} semantic categories")

        for category in categories:
            if pd.isna(category):
                continue

            # Filter villages with this category
            mask = semantic_categories == category
            if mask.sum() < 10:  # Skip rare categories
                continue

            category_coords = coords[mask]
            category_df = df[mask]

            # Compute KDE for this category
            coords_t = category_coords.T
            kde = gaussian_kde(coords_t, bw_method=self.bandwidth_deg)
            density = kde(coords_t)

            # Find high-density areas for this category
            threshold = np.percentile(density, 90)  # Lower threshold for categories
            hotspot_mask = density >= threshold

            if hotspot_mask.sum() < 5:
                continue

            # Get hotspot center (weighted by density)
            hotspot_coords = category_coords[hotspot_mask]
            hotspot_density = density[hotspot_mask]

            center_lat = np.average(hotspot_coords[:, 0], weights=hotspot_density)
            center_lon = np.average(hotspot_coords[:, 1], weights=hotspot_density)

            # Calculate radius
            distances = np.sqrt(
                (hotspot_coords[:, 0] - center_lat)**2 +
                (hotspot_coords[:, 1] - center_lon)**2
            )
            radius_km = distances.max() * 111

            # Get dominant region
            hotspot_df = category_df[hotspot_mask]
            city = hotspot_df['city'].mode()[0] if len(hotspot_df) > 0 else None
            county = hotspot_df['county'].mode()[0] if len(hotspot_df) > 0 else None

            hotspots.append({
                'hotspot_id': len(hotspots),
                'hotspot_type': 'naming_hotspot',
                'center_lat': center_lat,
                'center_lon': center_lon,
                'radius_km': radius_km,
                'village_count': hotspot_mask.sum(),
                'density_score': hotspot_density.mean(),
                'city': city,
                'county': county,
                'semantic_category': category,
                'pattern': None
            })

        logger.info(f"Identified {len(hotspots)} naming pattern hotspots")

        return pd.DataFrame(hotspots)
