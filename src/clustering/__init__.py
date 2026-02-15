"""
Clustering module for region-level analysis.

This module provides tools for:
- Building region feature vectors from semantic and morphological data
- Running clustering algorithms (KMeans)
- Generating interpretable cluster profiles
"""

from .feature_builder import RegionFeatureBuilder
from .clustering_engine import ClusteringEngine
from .cluster_profiler import ClusterProfiler

__all__ = [
    'RegionFeatureBuilder',
    'ClusteringEngine',
    'ClusterProfiler',
]
