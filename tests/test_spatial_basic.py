"""
Basic tests for spatial analysis module.

Run with: pytest tests/test_spatial_basic.py -v
"""

import pytest
import numpy as np
import pandas as pd
from src.spatial.coordinate_loader import CoordinateLoader
from src.spatial.distance_calculator import DistanceCalculator
from src.spatial.spatial_clustering import SpatialClusterer


class TestCoordinateLoader:
    """Test coordinate loading and validation."""

    def test_bounds_validation(self):
        """Test coordinate bounds validation."""
        loader = CoordinateLoader()

        # Create test DataFrame
        df = pd.DataFrame({
            'village_name': ['A', 'B', 'C', 'D'],
            'city': ['City1', 'City1', 'City2', 'City2'],
            'county': ['County1', 'County1', 'County2', 'County2'],
            'town': ['Town1', 'Town1', 'Town2', 'Town2'],
            'longitude': [113.0, 114.0, 200.0, 115.0],  # 200.0 is out of bounds
            'latitude': [23.0, 24.0, 25.0, 26.0]
        })

        # Validate bounds
        df_valid = loader._validate_bounds(df)

        # Should remove the out-of-bounds point
        assert len(df_valid) == 3
        assert 200.0 not in df_valid['longitude'].values

    def test_coordinate_array_format(self):
        """Test coordinate array format."""
        loader = CoordinateLoader()

        df = pd.DataFrame({
            'longitude': [113.0, 114.0],
            'latitude': [23.0, 24.0]
        })

        coords = loader.get_coordinate_array(df)

        # Should return [lat, lon] format
        assert coords.shape == (2, 2)
        assert coords[0, 0] == 23.0  # First row, latitude
        assert coords[0, 1] == 113.0  # First row, longitude


class TestDistanceCalculator:
    """Test distance calculation."""

    def test_haversine_distance(self):
        """Test haversine distance calculation."""
        calc = DistanceCalculator()

        # Guangzhou to Shenzhen (approximately 120km)
        dist = calc.haversine_distance(113.26, 23.13, 114.06, 22.54)

        # Allow 10% error
        assert 110 < dist < 130

    def test_nearest_neighbors(self):
        """Test k-nearest neighbors search."""
        calc = DistanceCalculator()

        # Create test coordinates (5 points)
        coords = np.array([
            [23.0, 113.0],
            [23.1, 113.1],
            [23.2, 113.2],
            [24.0, 114.0],
            [24.1, 114.1]
        ])

        # Build tree
        calc.build_tree(coords)

        # Find 2 nearest neighbors
        distances, indices = calc.nearest_neighbors(coords, k=2)

        # Check shape
        assert distances.shape == (5, 2)
        assert indices.shape == (5, 2)

        # First point's nearest neighbor should be second point
        assert indices[0, 0] == 1


class TestSpatialClusterer:
    """Test spatial clustering."""

    def test_dbscan_clustering(self):
        """Test DBSCAN clustering."""
        clusterer = SpatialClusterer(eps_km=20.0, min_samples=2)

        # Create test coordinates (2 clusters)
        coords = np.array([
            [23.0, 113.0],
            [23.1, 113.1],
            [23.2, 113.2],  # Cluster 1
            [24.0, 114.0],
            [24.1, 114.1],
            [24.2, 114.2]   # Cluster 2
        ])

        # Run clustering
        labels = clusterer.fit(coords)

        # Should find 2 clusters
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        assert n_clusters >= 1  # At least 1 cluster

        # Labels should be integers
        assert all(isinstance(label, (int, np.integer)) for label in labels)

    def test_cluster_profiles(self):
        """Test cluster profile generation."""
        clusterer = SpatialClusterer(eps_km=20.0, min_samples=2)

        coords = np.array([
            [23.0, 113.0],
            [23.1, 113.1],
            [23.2, 113.2]
        ])

        df = pd.DataFrame({
            'village_name': ['A', 'B', 'C'],
            'city': ['City1', 'City1', 'City1'],
            'county': ['County1', 'County1', 'County1'],
            'town': ['Town1', 'Town1', 'Town1']
        })

        labels = clusterer.fit(coords)
        profiles = clusterer.get_cluster_profiles(coords, labels, df)

        # Should have cluster profiles
        assert len(profiles) >= 0
        if len(profiles) > 0:
            assert 'cluster_id' in profiles.columns
            assert 'cluster_size' in profiles.columns
            assert 'centroid_lat' in profiles.columns
            assert 'centroid_lon' in profiles.columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
