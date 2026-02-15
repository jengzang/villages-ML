"""
Clustering Engine for Region Analysis.

Implements KMeans clustering with preprocessing and evaluation.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score


class ClusteringEngine:
    """Clustering algorithm engine."""

    def __init__(self, random_state: int = 42):
        """
        Initialize clustering engine.

        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.pca = None
        self.model = None
        self.X_scaled = None
        self.X_transformed = None

    def preprocess(
        self,
        X: np.ndarray,
        use_pca: bool = True,
        n_components: int = 50
    ) -> np.ndarray:
        """
        Preprocess feature matrix.

        Steps:
        1. StandardScaler normalization (z-score)
        2. Optional PCA dimensionality reduction

        Args:
            X: Feature matrix (n_samples, n_features)
            use_pca: Whether to apply PCA
            n_components: Number of PCA components

        Returns:
            Processed feature matrix
        """
        # Standardize features
        self.X_scaled = self.scaler.fit_transform(X)

        # Apply PCA if requested
        if use_pca and X.shape[1] > n_components:
            self.pca = PCA(n_components=n_components, random_state=self.random_state)
            self.X_transformed = self.pca.fit_transform(self.X_scaled)
            return self.X_transformed
        else:
            self.X_transformed = self.X_scaled
            return self.X_scaled

    def fit_kmeans(
        self,
        X: np.ndarray,
        k_range: List[int] = [4, 6, 8, 10, 12, 15, 18, 20],
        n_init: int = 20,
        max_iter: int = 500
    ) -> List[Dict]:
        """
        Run KMeans clustering for multiple k values.

        Args:
            X: Preprocessed feature matrix
            k_range: List of k values to try
            n_init: Number of initializations per k
            max_iter: Maximum iterations

        Returns:
            List of result dictionaries, each containing:
            - k: Number of clusters
            - model: Fitted KMeans model
            - labels: Cluster assignments
            - inertia: Within-cluster sum of squares
            - silhouette_score: Silhouette coefficient
            - davies_bouldin_index: DB index
            - calinski_harabasz_score: CH score
        """
        results = []

        for k in k_range:
            # Fit KMeans
            model = KMeans(
                n_clusters=k,
                n_init=n_init,
                max_iter=max_iter,
                random_state=self.random_state
            )
            labels = model.fit_predict(X)

            # Calculate metrics
            sil_score = silhouette_score(X, labels) if k > 1 else 0.0
            db_index = davies_bouldin_score(X, labels) if k > 1 else 0.0
            ch_score = calinski_harabasz_score(X, labels) if k > 1 else 0.0

            results.append({
                'k': k,
                'model': model,
                'labels': labels,
                'inertia': model.inertia_,
                'silhouette_score': sil_score,
                'davies_bouldin_index': db_index,
                'calinski_harabasz_score': ch_score
            })

        return results

    def select_best_k(
        self,
        results: List[Dict],
        metric: str = 'silhouette_score'
    ) -> Dict:
        """
        Select best k value based on evaluation metric.

        Args:
            results: List of clustering results
            metric: Metric to optimize ('silhouette_score', 'davies_bouldin_index', 'calinski_harabasz_score')

        Returns:
            Best result dictionary
        """
        if metric == 'davies_bouldin_index':
            # Lower is better for DB index
            best_result = min(results, key=lambda x: x[metric])
        else:
            # Higher is better for silhouette and CH scores
            best_result = max(results, key=lambda x: x[metric])

        return best_result

    def get_cluster_distances(
        self,
        X: np.ndarray,
        model: KMeans
    ) -> np.ndarray:
        """
        Calculate distance from each sample to its cluster centroid.

        Args:
            X: Feature matrix
            model: Fitted KMeans model

        Returns:
            Array of distances (n_samples,)
        """
        distances = np.zeros(len(X))
        for i, (sample, label) in enumerate(zip(X, model.labels_)):
            centroid = model.cluster_centers_[label]
            distances[i] = np.linalg.norm(sample - centroid)

        return distances

