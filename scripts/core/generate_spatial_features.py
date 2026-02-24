"""
Generate village_spatial_features table from preprocessed data.

This script:
1. Creates the village_spatial_features table
2. Loads villages with coordinates from the preprocessed table
3. Computes spatial features (k-NN distances, density, etc.)
4. Writes features to the database
"""

import sqlite3
import logging
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.db_writer import create_feature_materialization_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_villages_with_coordinates(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load villages with valid coordinates from preprocessed table.

    Args:
        conn: SQLite database connection

    Returns:
        DataFrame with village data and coordinates
    """
    logger.info("Loading villages with coordinates from preprocessed table")

    query = """
    SELECT
        village_id,
        市级 as city,
        区县级 as county,
        乡镇级 as town,
        村委会 as village_committee,
        自然村_去前缀 as village_name,
        longitude,
        latitude
    FROM 广东省自然村_预处理
    WHERE village_id IS NOT NULL
      AND longitude IS NOT NULL
      AND latitude IS NOT NULL
      AND longitude != ''
      AND latitude != ''
    """

    df = pd.read_sql_query(query, conn)

    # Convert coordinates to float
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')

    # Filter out invalid coordinates
    df = df.dropna(subset=['longitude', 'latitude'])
    df = df[(df['longitude'] != 0) & (df['latitude'] != 0)]

    logger.info(f"Loaded {len(df)} villages with valid coordinates")

    return df


def compute_spatial_features(df: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """
    Compute spatial features for villages.

    Args:
        df: DataFrame with village coordinates
        k: Number of nearest neighbors to consider

    Returns:
        DataFrame with spatial features
    """
    logger.info(f"Computing spatial features (k={k})...")

    # Prepare coordinates array
    coords = df[['latitude', 'longitude']].values

    # Fit k-NN model (using haversine metric for geographic coordinates)
    logger.info("Fitting k-NN model...")
    nbrs = NearestNeighbors(n_neighbors=k+1, metric='haversine', algorithm='ball_tree')
    nbrs.fit(np.radians(coords))

    # Find k nearest neighbors
    logger.info("Finding nearest neighbors...")
    distances, indices = nbrs.kneighbors(np.radians(coords))

    # Convert distances from radians to kilometers
    # Earth radius = 6371 km
    distances_km = distances * 6371

    # Compute features
    logger.info("Computing features...")
    features = pd.DataFrame()
    features['village_id'] = df['village_id'].values

    # Distance to nearest neighbor (excluding self)
    features['nn1_distance_km'] = distances_km[:, 1]

    # Average distance to k nearest neighbors
    features['avg_knn_distance_km'] = distances_km[:, 1:].mean(axis=1)

    # Density (inverse of average distance)
    features['density'] = 1.0 / (features['avg_knn_distance_km'] + 0.001)

    # Standard deviation of distances (measure of clustering uniformity)
    features['knn_distance_std'] = distances_km[:, 1:].std(axis=1)

    logger.info(f"Computed spatial features for {len(features)} villages")

    return features


def main():
    db_path = project_root / 'data' / 'villages.db'

    logger.info("=" * 80)
    logger.info("Generating village_spatial_features table")
    logger.info("=" * 80)
    logger.info(f"Database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(str(db_path))

    try:
        # Step 1: Create table
        logger.info("Creating village_spatial_features table...")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS village_spatial_features (
                village_id TEXT PRIMARY KEY,
                village_name TEXT NOT NULL,
                city TEXT,
                county TEXT,
                town TEXT,
                longitude REAL NOT NULL,
                latitude REAL NOT NULL,
                nn_distance_1 REAL,
                nn_distance_5 REAL,
                nn_distance_10 REAL,
                local_density_1km INTEGER,
                local_density_5km INTEGER,
                local_density_10km INTEGER,
                isolation_score REAL,
                is_isolated INTEGER,
                spatial_cluster_id INTEGER,
                cluster_size INTEGER
            )
        """)
        conn.commit()
        logger.info("Table created successfully")

        # Step 2: Load villages with coordinates
        df = load_villages_with_coordinates(conn)

        if len(df) == 0:
            logger.error("No villages with valid coordinates found!")
            return

        # Step 3: Compute spatial features
        features_df = compute_spatial_features(df, k=10)

        # Merge with original data to get administrative info
        logger.info("Merging with administrative data...")
        merged_df = features_df.merge(df, on='village_id', how='left')

        # Step 4: Write to database
        logger.info("Writing spatial features to database...")

        cursor = conn.cursor()
        batch_size = 10000
        total_batches = (len(merged_df) + batch_size - 1) // batch_size

        for i in range(0, len(merged_df), batch_size):
            batch = merged_df.iloc[i:i+batch_size]
            batch_num = i // batch_size + 1

            # Prepare values for insertion
            values = []
            for _, row in batch.iterrows():
                values.append((
                    row['village_id'],
                    row['village_name'],
                    row['city'],
                    row['county'],
                    row['town'],
                    float(row['longitude']),
                    float(row['latitude']),
                    float(row['nn1_distance_km']),  # nn_distance_1
                    None,  # nn_distance_5 (not computed)
                    float(row['avg_knn_distance_km']),  # nn_distance_10
                    None,  # local_density_1km (not computed)
                    None,  # local_density_5km (not computed)
                    None,  # local_density_10km (not computed)
                    None,  # isolation_score (not computed)
                    None,  # is_isolated (not computed)
                    None,  # spatial_cluster_id (not computed)
                    None   # cluster_size (not computed)
                ))

            # Insert batch
            cursor.executemany("""
                INSERT OR REPLACE INTO village_spatial_features
                (village_id, village_name, city, county, town, longitude, latitude,
                 nn_distance_1, nn_distance_5, nn_distance_10,
                 local_density_1km, local_density_5km, local_density_10km,
                 isolation_score, is_isolated, spatial_cluster_id, cluster_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)

            logger.info(f"Batch {batch_num}/{total_batches} written ({len(batch)} rows)")

        conn.commit()
        logger.info("Spatial features written successfully")

        # Step 5: Verify
        cursor.execute("SELECT COUNT(*) FROM village_spatial_features")
        count = cursor.fetchone()[0]
        logger.info(f"Verification: village_spatial_features has {count} rows")

        logger.info("=" * 80)
        logger.info("village_spatial_features generation completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == '__main__':
    main()
