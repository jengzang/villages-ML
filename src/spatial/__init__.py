"""
Spatial Analysis Module.

Provides geographic analysis capabilities for village data:
- Coordinate loading and validation
- Distance calculation (haversine)
- Spatial clustering (DBSCAN)
- Hotspot detection (KDE)
- Density analysis
- Interactive map generation
"""

from .coordinate_loader import CoordinateLoader
from .distance_calculator import DistanceCalculator
from .spatial_clustering import SpatialClusterer
from .spatial_features import SpatialFeatureExtractor
from .hotspot_detector import HotspotDetector
from .density_analyzer import DensityAnalyzer
from .map_generator import MapGenerator

__all__ = [
    'CoordinateLoader',
    'DistanceCalculator',
    'SpatialClusterer',
    'SpatialFeatureExtractor',
    'HotspotDetector',
    'DensityAnalyzer',
    'MapGenerator',
]
