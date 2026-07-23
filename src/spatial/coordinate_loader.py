"""
Coordinate Loader for Spatial Analysis.

Loads and validates geographic coordinates from the database.
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

from src.schema import REGION_LEVELS, VillageTableSchema, DEFAULT_SCHEMA

logger = logging.getLogger(__name__)

# Guangdong Province coordinate bounds
GUANGDONG_BOUNDS = {
    'lon_min': 109.67,
    'lon_max': 117.31,
    'lat_min': 20.23,
    'lat_max': 25.60
}

CHINA_BOUNDS = {
    'lon_min': 73.0,
    'lon_max': 135.5,
    'lat_min': 18.0,
    'lat_max': 54.0
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

    def load_coordinates(self, conn,
                         schema: VillageTableSchema = DEFAULT_SCHEMA) -> pd.DataFrame:
        """
        Load villages with valid coordinates from database.

        Args:
            conn: Database connection
            schema: Table schema definition

        Returns:
            DataFrame with columns:
                - village_name: str
                - city: str
                - county: str
                - township: str
                - longitude: float
                - latitude: float
        """
        logger.info("Loading coordinates from database")

        S = schema
        query = f"""
        SELECT
            {S.village_id_col},
            {S.city_col} as city,
            {S.county_col} as county,
            {S.township_col} as {REGION_LEVELS[2]},
            {S.committee_col_preprocessed} as village_committee,
            {S.village_name_col_prefix_removed} as village_name,
            {S.longitude_col},
            {S.latitude_col}
        FROM {S.preprocessed_table}
        """
        df = pd.read_sql_query(query, conn)

        logger.info(f"Loaded {len(df)} total villages")

        # Keep only needed columns (including village_id for uniqueness)
        df = df[['village_id', 'village_name', REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2], 'longitude', 'latitude']]

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
