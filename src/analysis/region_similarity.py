"""
Region Similarity Analysis Module

Computes pairwise similarity between regions based on character frequency patterns.
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from collections import defaultdict
import json


class RegionSimilarityAnalyzer:
    """
    Compute pairwise similarity between regions.

    Uses character frequency patterns to measure naming style similarity.
    """

    def __init__(self, db_path: str):
        """
        Initialize analyzer.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.feature_vectors = None
        self.region_names = None
        self.feature_chars = None

    def load_regional_data(
        self,
        region_level: str = 'county',
        top_k_global: int = 100,
        z_score_threshold: float = 2.0
    ) -> pd.DataFrame:
        """
        Load character frequency data for regions.

        Args:
            region_level: 'city', 'county', or 'township'
            top_k_global: Number of top global frequency characters to include
            z_score_threshold: Minimum |z_score| for high-tendency characters

        Returns:
            DataFrame with regional character data
        """
        conn = sqlite3.connect(self.db_path)

        # Get top-k global frequency characters
        query_top_chars = """
        SELECT char, global_frequency
        FROM char_regional_analysis
        WHERE region_level = ?
        GROUP BY char
        ORDER BY global_frequency DESC
        LIMIT ?
        """
        top_chars_df = pd.read_sql_query(
            query_top_chars,
            conn,
            params=(region_level, top_k_global)
        )
        top_chars = set(top_chars_df['char'].tolist())

        # Get high-tendency characters (|z_score| > threshold)
        query_high_tendency = """
        SELECT DISTINCT char
        FROM char_regional_analysis
        WHERE region_level = ?
        AND ABS(z_score) >= ?
        """
        high_tendency_df = pd.read_sql_query(
            query_high_tendency,
            conn,
            params=(region_level, z_score_threshold)
        )
        high_tendency_chars = set(high_tendency_df['char'].tolist())

        # Combine feature characters
        feature_chars = top_chars.union(high_tendency_chars)

        # Load data for feature characters
        placeholders = ','.join(['?'] * len(feature_chars))
        query_data = f"""
        SELECT region_name, char, frequency, z_score
        FROM char_regional_analysis
        WHERE region_level = ?
        AND char IN ({placeholders})
        """
        params = [region_level] + list(feature_chars)
        df = pd.read_sql_query(query_data, conn, params=params)

        conn.close()

        self.feature_chars = sorted(feature_chars)
        return df

    def build_feature_vectors(self, df: pd.DataFrame) -> np.ndarray:
        """
        Build feature vectors for each region.

        Args:
            df: DataFrame with region_name, char, frequency columns

        Returns:
            Feature matrix (n_regions × n_features)
        """
        # Get unique regions
        regions = sorted(df['region_name'].unique())
        self.region_names = regions

        # Build feature matrix
        n_regions = len(regions)
        n_features = len(self.feature_chars)
        feature_matrix = np.zeros((n_regions, n_features))

        # Create char to index mapping
        char_to_idx = {char: idx for idx, char in enumerate(self.feature_chars)}

        # Fill matrix
        for _, row in df.iterrows():
            region = row['region_name']
            char = row['char']
            freq = row['frequency']

            region_idx = regions.index(region)
            char_idx = char_to_idx.get(char)

            if char_idx is not None:
                feature_matrix[region_idx, char_idx] = freq

        self.feature_vectors = feature_matrix
        return feature_matrix

    def compute_cosine_similarity(self) -> np.ndarray:
        """
        Compute cosine similarity between all region pairs.

        Returns:
            Similarity matrix (n_regions × n_regions)
        """
        if self.feature_vectors is None:
            raise ValueError("Must build feature vectors first")

        return cosine_similarity(self.feature_vectors)

    def compute_jaccard_similarity(
        self,
        df: pd.DataFrame,
        z_score_threshold: float = 2.0
    ) -> np.ndarray:
        """
        Compute Jaccard similarity on high-tendency character sets.

        Args:
            df: DataFrame with region_name, char, z_score columns
            z_score_threshold: Minimum z_score for high-tendency

        Returns:
            Jaccard similarity matrix (n_regions × n_regions)
        """
        if self.region_names is None:
            raise ValueError("Must build feature vectors first")

        # Extract high-tendency character sets per region
        high_tendency_sets = {}
        for region in self.region_names:
            region_data = df[
                (df['region_name'] == region) &
                (df['z_score'] >= z_score_threshold)
            ]
            high_tendency_sets[region] = set(region_data['char'].tolist())

        # Compute Jaccard similarity
        n_regions = len(self.region_names)
        jaccard_matrix = np.zeros((n_regions, n_regions))

        for i, region1 in enumerate(self.region_names):
            for j, region2 in enumerate(self.region_names):
                set1 = high_tendency_sets.get(region1, set())
                set2 = high_tendency_sets.get(region2, set())

                if len(set1) == 0 and len(set2) == 0:
                    jaccard_matrix[i, j] = 0.0
                else:
                    intersection = len(set1.intersection(set2))
                    union = len(set1.union(set2))
                    jaccard_matrix[i, j] = intersection / union if union > 0 else 0.0

        return jaccard_matrix

    def compute_euclidean_distance(self) -> np.ndarray:
        """
        Compute Euclidean distance between all region pairs.

        Returns:
            Distance matrix (n_regions × n_regions)
        """
        if self.feature_vectors is None:
            raise ValueError("Must build feature vectors first")

        return euclidean_distances(self.feature_vectors)

    def extract_distinctive_chars(
        self,
        df: pd.DataFrame,
        region: str,
        top_k: int = 10,
        min_z_score: float = 2.0
    ) -> List[str]:
        """
        Extract distinctive characters for a region.

        Args:
            df: DataFrame with region_name, char, z_score columns
            region: Region name
            top_k: Number of top distinctive characters
            min_z_score: Minimum z_score threshold

        Returns:
            List of distinctive characters
        """
        region_data = df[
            (df['region_name'] == region) &
            (df['z_score'] >= min_z_score)
        ].copy()

        region_data = region_data.sort_values('z_score', ascending=False)
        return region_data['char'].head(top_k).tolist()

    def find_common_chars(
        self,
        df: pd.DataFrame,
        region1: str,
        region2: str,
        min_z_score: float = 2.0
    ) -> List[str]:
        """
        Find common high-tendency characters between two regions.

        Args:
            df: DataFrame with region_name, char, z_score columns
            region1: First region name
            region2: Second region name
            min_z_score: Minimum z_score threshold

        Returns:
            List of common characters
        """
        r1_chars = set(df[
            (df['region_name'] == region1) &
            (df['z_score'] >= min_z_score)
        ]['char'].tolist())

        r2_chars = set(df[
            (df['region_name'] == region2) &
            (df['z_score'] >= min_z_score)
        ]['char'].tolist())

        return sorted(r1_chars.intersection(r2_chars))

    def generate_similarity_pairs(
        self,
        cosine_matrix: np.ndarray,
        jaccard_matrix: np.ndarray,
        euclidean_matrix: np.ndarray,
        df: pd.DataFrame,
        region_level: str
    ) -> List[Dict]:
        """
        Generate similarity records for all region pairs.

        Args:
            cosine_matrix: Cosine similarity matrix
            jaccard_matrix: Jaccard similarity matrix
            euclidean_matrix: Euclidean distance matrix
            df: DataFrame with regional data
            region_level: Region level name

        Returns:
            List of similarity records
        """
        records = []
        n_regions = len(self.region_names)

        for i in range(n_regions):
            for j in range(i + 1, n_regions):  # Upper triangle only
                region1 = self.region_names[i]
                region2 = self.region_names[j]

                # Extract metrics
                cosine_sim = float(cosine_matrix[i, j])
                jaccard_sim = float(jaccard_matrix[i, j])
                euclidean_dist = float(euclidean_matrix[i, j])

                # Extract distinctive and common characters
                distinctive_r1 = self.extract_distinctive_chars(df, region1, top_k=10)
                distinctive_r2 = self.extract_distinctive_chars(df, region2, top_k=10)
                common_chars = self.find_common_chars(df, region1, region2)

                record = {
                    'region_level': region_level,
                    'region1': region1,
                    'region2': region2,
                    'cosine_similarity': cosine_sim,
                    'jaccard_similarity': jaccard_sim,
                    'euclidean_distance': euclidean_dist,
                    'common_high_tendency_chars': json.dumps(common_chars, ensure_ascii=False),
                    'distinctive_chars_r1': json.dumps(distinctive_r1, ensure_ascii=False),
                    'distinctive_chars_r2': json.dumps(distinctive_r2, ensure_ascii=False),
                    'feature_dimension': len(self.feature_chars)
                }

                records.append(record)

        return records

