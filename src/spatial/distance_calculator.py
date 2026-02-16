"""
Distance Calculator for Spatial Analysis.

Implements haversine distance calculation and k-nearest neighbor search.
"""

import numpy as np
from sklearn.neighbors import BallTree
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0


class DistanceCalculator:
    """Calculate distances and nearest neighbors for geographic coordinates."""

    def __init__(self):
        """Initialize distance calculator."""
        self.ball_tree = None

    @staticmethod
    def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Calculate haversine distance between two points.

        Args:
            lon1, lat1: First point coordinates (degrees)
            lon2, lat2: Second point coordinates (degrees)

        Returns:
            Distance in kilometers
        """
        # Convert to radians
        lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))

        return EARTH_RADIUS_KM * c

    def build_tree(self, coords: np.ndarray):
        """
        Build BallTree for efficient nearest neighbor search.

        Args:
            coords: Array of shape (n_points, 2) with [latitude, longitude] in degrees
        """
        logger.info(f"Building BallTree for {len(coords)} points")

        # Convert to radians for haversine metric
        coords_rad = np.radians(coords)

        # Build tree with haversine metric
        self.ball_tree = BallTree(coords_rad, metric='haversine')

        logger.info("BallTree built successfully")

    def nearest_neighbors(self, coords: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find k nearest neighbors for each point.

        Args:
            coords: Array of shape (n_points, 2) with [latitude, longitude] in degrees
            k: Number of nearest neighbors (default: 10)

        Returns:
            Tuple of (distances, indices):
                - distances: Array of shape (n_points, k) with distances in km
                - indices: Array of shape (n_points, k) with neighbor indices
        """
        if self.ball_tree is None:
            raise ValueError("BallTree not built. Call build_tree() first.")

        logger.info(f"Finding {k} nearest neighbors for {len(coords)} points")

        # Convert to radians
        coords_rad = np.radians(coords)

        # Query tree (k+1 because first neighbor is the point itself)
        distances_rad, indices = self.ball_tree.query(coords_rad, k=k+1)

        # Remove self (first column)
        distances_rad = distances_rad[:, 1:]
        indices = indices[:, 1:]

        # Convert distances from radians to kilometers
        distances_km = distances_rad * EARTH_RADIUS_KM

        logger.info(f"Nearest neighbor search complete")

        return distances_km, indices

    def radius_neighbors(self, coords: np.ndarray, radius_km: float) -> Tuple[list, list]:
        """
        Find all neighbors within radius for each point.

        Args:
            coords: Array of shape (n_points, 2) with [latitude, longitude] in degrees
            radius_km: Search radius in kilometers

        Returns:
            Tuple of (distances, indices):
                - distances: List of arrays with distances in km
                - indices: List of arrays with neighbor indices
        """
        if self.ball_tree is None:
            raise ValueError("BallTree not built. Call build_tree() first.")

        logger.info(f"Finding neighbors within {radius_km}km for {len(coords)} points")

        # Convert to radians
        coords_rad = np.radians(coords)
        radius_rad = radius_km / EARTH_RADIUS_KM

        # Query tree
        distances_rad, indices = self.ball_tree.query_radius(
            coords_rad, r=radius_rad, return_distance=True
        )

        # Convert distances from radians to kilometers
        distances_km = [d * EARTH_RADIUS_KM for d in distances_rad]

        logger.info("Radius neighbor search complete")

        return distances_km, indices
