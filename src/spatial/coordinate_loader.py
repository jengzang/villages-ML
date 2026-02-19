"""
Coordinate Loader for Spatial Analysis.

Loads and validates geographic coordinates from the database.
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Guangdong Province coordinate bounds
GUANGDONG_BOUNDS = {
    'lon_min': 109.67,
    'lon_max': 117.31,
    'lat_min': 20.23,
    'lat_max': 25.60
}


class CoordinateLoader:
    """Load and validate village coordinates."""

    def __init__(self, bounds: Optional[dict] = None):
        """
        Initialize coordinate loader.

        Args:
            bounds: Optional custom coordinate bounds
                   Default: Guangdong Province bounds
        """
        self.bounds = bounds or GUANGDONG_BOUNDS

    def load_coordinates(self, conn) -> pd.DataFrame:
        """
        Load villages with valid coordinates from database.

        Args:
            conn: Database connection

        Returns:
            DataFrame with columns:
                - village_name: str
                - city: str
                - county: str
                - town: str
                - longitude: float
                - latitude: float
        """
        logger.info("Loading coordinates from database")

        # Query from preprocessed table with cleaned village names
        query = """
        SELECT
            市级 as city,
            区县级 as county,
            乡镇级 as town,
            行政村 as village_committee,
            自然村_去前缀 as village_name,
            拼音 as pinyin,
            语言分布 as language_distribution,
            longitude,
            latitude
        FROM 广东省自然村_预处理
        WHERE 有效 = 1
        """
        df = pd.read_sql_query(query, conn)

        logger.info(f"Loaded {len(df)} total villages")

        # Keep only needed columns
        df = df[['village_name', 'city', 'county', 'town', 'longitude', 'latitude']]

        # Convert coordinates to numeric
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')

        # Filter out invalid coordinates
        initial_count = len(df)
        df = df.dropna(subset=['longitude', 'latitude'])
        logger.info(f"Removed {initial_count - len(df)} villages with missing coordinates")

        # Validate coordinate bounds
        df = self._validate_bounds(df)

        logger.info(f"Final dataset: {len(df)} villages with valid coordinates")

        return df

    def _validate_bounds(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate coordinates are within expected bounds.

        Args:
            df: DataFrame with longitude and latitude columns

        Returns:
            Filtered DataFrame with valid coordinates
        """
        initial_count = len(df)

        # Filter by bounds
        mask = (
            (df['longitude'] >= self.bounds['lon_min']) &
            (df['longitude'] <= self.bounds['lon_max']) &
            (df['latitude'] >= self.bounds['lat_min']) &
            (df['latitude'] <= self.bounds['lat_max'])
        )

        df_valid = df[mask].copy()

        removed = initial_count - len(df_valid)
        if removed > 0:
            logger.warning(f"Removed {removed} villages with out-of-bounds coordinates")

        return df_valid

    def get_coordinate_array(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract coordinate array from DataFrame.

        Args:
            df: DataFrame with longitude and latitude columns

        Returns:
            Array of shape (n_villages, 2) with [latitude, longitude]
            Note: Order is [lat, lon] for compatibility with haversine metric
        """
        # Return as [lat, lon] for sklearn haversine metric
        return df[['latitude', 'longitude']].values
