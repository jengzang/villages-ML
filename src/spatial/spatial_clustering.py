"""
Spatial Clustering using DBSCAN.

Performs geographic clustering based on coordinate proximity.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0


class SpatialClusterer:
    """Perform spatial clustering on geographic coordinates."""

    def __init__(self, eps_km: float = 2.0, min_samples: int = 5):
        """
        Initialize spatial clusterer.

        Args:
            eps_km: Maximum distance between two samples (in km) for one to be
                   considered as in the neighborhood of the other
            min_samples: Minimum number of samples in a neighborhood for a point
                        to be considered as a core point
        """
        self.eps_km = eps_km
        self.min_samples = min_samples
        self.eps_rad = eps_km / EARTH_RADIUS_KM  # Convert to radians
        self.model = None
        self.labels_ = None

    def fit(self, coords: np.ndarray) -> np.ndarray:
        """
        Perform DBSCAN clustering on coordinates.

        Args:
            coords: Array of shape (n_points, 2) with [latitude, longitude] in degrees

        Returns:
            Cluster labels (array of shape (n_points,))
            -1 indicates noise points
        """
        logger.info(f"Running DBSCAN clustering with eps={self.eps_km}km, min_samples={self.min_samples}")
        logger.info(f"Input: {len(coords)} villages")

        # Convert to radians for haversine metric
        coords_rad = np.radians(coords)

        # Run DBSCAN
        self.model = DBSCAN(
            eps=self.eps_rad,
            min_samples=self.min_samples,
            metric='haversine',
            algorithm='ball_tree',
            n_jobs=-1
        )

        self.labels_ = self.model.fit_predict(coords_rad)

        # Log results
        n_clusters = len(set(self.labels_)) - (1 if -1 in self.labels_ else 0)
        n_noise = list(self.labels_).count(-1)

        logger.info(f"Clustering complete:")
        logger.info(f"  - {n_clusters} clusters found")
        logger.info(f"  - {n_noise} noise points ({n_noise/len(coords)*100:.1f}%)")

        return self.labels_

    def get_cluster_profiles(self, coords: np.ndarray, labels: np.ndarray,
                            df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate profile for each cluster.

        Args:
            coords: Array of shape (n_points, 2) with [latitude, longitude]
            labels: Cluster labels
            df: Original DataFrame with village data

        Returns:
            DataFrame with cluster profiles
        """
        logger.info("Calculating cluster profiles")

        profiles = []

        # Get unique cluster IDs (excluding noise -1)
        cluster_ids = sorted([c for c in set(labels) if c != -1])

        for cluster_id in cluster_ids:
            mask = labels == cluster_id
            cluster_coords = coords[mask]
            cluster_df = df[mask]

            # Calculate centroid
            centroid_lat = cluster_coords[:, 0].mean()
            centroid_lon = cluster_coords[:, 1].mean()

            # Calculate cluster size
            cluster_size = mask.sum()

            # Get dominant region
            city_mode = cluster_df['city'].mode()
            dominant_city = city_mode.iloc[0] if len(city_mode) > 0 else None

            county_mode = cluster_df['county'].mode()
            dominant_county = county_mode.iloc[0] if len(county_mode) > 0 else None

            # Calculate average density (avg distance to centroid)
            distances = np.sqrt(
                (cluster_coords[:, 0] - centroid_lat)**2 +
                (cluster_coords[:, 1] - centroid_lon)**2
            )
            avg_distance_deg = distances.mean()
            # Rough conversion to km (1 degree ≈ 111 km at equator)
            avg_distance_km = avg_distance_deg * 111

            profiles.append({
                'cluster_id': cluster_id,
                'cluster_size': cluster_size,
                'centroid_lat': centroid_lat,
                'centroid_lon': centroid_lon,
                'avg_distance_km': avg_distance_km,
                'dominant_city': dominant_city,
                'dominant_county': dominant_county
            })

        profiles_df = pd.DataFrame(profiles)
        logger.info(f"Generated profiles for {len(profiles_df)} clusters")

        return profiles_df
