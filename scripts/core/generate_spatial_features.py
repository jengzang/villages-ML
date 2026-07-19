"""
Generate spatial features and hotspot tables from preprocessed data.

This script:
1. Creates the village_spatial_features table
2. Loads villages with coordinates from the preprocessed table
3. Computes spatial features (k-NN distances, density, etc.)
4. Writes features to the database
5. Supports hotspot-only mode for Phase 13
"""

import argparse
import sqlite3
import logging
import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.db_writer import (
    create_spatial_analysis_tables,
    create_spatial_analysis_indexes,
    write_spatial_hotspots,
)
from src.spatial.coordinate_loader import CoordinateLoader
from src.spatial.hotspot_detector import HotspotDetector
from src.schema import get_schema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate spatial features or hotspots")
    parser.add_argument("--db-path", default=str(project_root / "data" / "villages.db"))
    parser.add_argument("--schema", default="guangdong", choices=["guangdong", "national"], help="Village table schema")
    parser.add_argument("--run-id", default=f"spatial_{int(time.time())}")
    parser.add_argument(
        "--mode",
        choices=["features", "hotspots"],
        default="features",
        help="features: regenerate village_spatial_features; hotspots: regenerate spatial_hotspots only",
    )
    parser.add_argument("--hotspot-bandwidth-km", type=float, default=5.0)
    parser.add_argument("--hotspot-threshold-percentile", type=float, default=90.0)
    parser.add_argument("--hotspot-sample-size", type=int, default=50000)
    parser.add_argument("--hotspot-cluster-eps-km", type=float, default=1.1)
    parser.add_argument("--hotspot-cluster-min-samples", type=int, default=5)
    parser.add_argument("--hotspot-full-count-radius-km", type=float, default=3.0)
    parser.add_argument("--hotspot-sample-seed", type=int, default=20260712)
    parser.add_argument("--batch-size", type=int, default=10000, help="Rows to write per batch in features mode")
    return parser.parse_args()


def load_villages_with_coordinates(conn: sqlite3.Connection, schema_name: str = "guangdong") -> pd.DataFrame:
    """
    Load villages with valid coordinates from preprocessed table.

    Args:
        conn: SQLite database connection

    Returns:
        DataFrame with village data and coordinates
    """
    logger.info("Loading villages with coordinates from preprocessed table")
    schema = get_schema(schema_name)

    query = f"""
    SELECT
        {schema.village_id_col} as village_id,
        {schema.city_col} as city,
        {schema.county_col} as county,
        {schema.township_col} as town,
        {schema.committee_col_preprocessed} as village_committee,
        {schema.village_name_col_prefix_removed} as village_name,
        {schema.longitude_col} as longitude,
        {schema.latitude_col} as latitude
    FROM {schema.preprocessed_table}
    WHERE {schema.village_id_col} IS NOT NULL
      AND {schema.longitude_col} IS NOT NULL
      AND {schema.latitude_col} IS NOT NULL
      AND {schema.longitude_col} != ''
      AND {schema.latitude_col} != ''
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


def run_hotspot_pipeline(args) -> None:
    logger.info("=" * 80)
    logger.info("Generating spatial_hotspots table")
    logger.info("=" * 80)
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Run ID: {args.run_id}")
    logger.info(
        "Hotspot parameters: "
        f"bandwidth={args.hotspot_bandwidth_km}km, "
        f"threshold=p{args.hotspot_threshold_percentile}, "
        f"sample_size={args.hotspot_sample_size}, "
        f"cluster_eps={args.hotspot_cluster_eps_km}km, "
        f"cluster_min_samples={args.hotspot_cluster_min_samples}, "
        f"full_count_radius={args.hotspot_full_count_radius_km}km"
    )

    conn = sqlite3.connect(str(args.db_path))
    try:
        create_spatial_analysis_tables(conn)
        create_spatial_analysis_indexes(conn)

        loader = CoordinateLoader()
        coords_df = loader.load_coordinates(conn, schema=get_schema(args.schema))
        coords = loader.get_coordinate_array(coords_df)
        if len(coords_df) == 0:
            logger.error("No villages with valid coordinates found!")
            return

        detector = HotspotDetector(
            bandwidth_km=args.hotspot_bandwidth_km,
            threshold_percentile=args.hotspot_threshold_percentile,
            cluster_eps_km=args.hotspot_cluster_eps_km,
            cluster_min_samples=args.hotspot_cluster_min_samples,
            sample_seed=args.hotspot_sample_seed,
            full_count_radius_km=args.hotspot_full_count_radius_km,
        )
        hotspots_df = detector.detect_density_hotspots(
            coords,
            coords_df,
            sample_size=args.hotspot_sample_size,
        )
        if len(hotspots_df) > 0:
            hotspots_df["hotspot_id"] = range(len(hotspots_df))

        cursor = conn.cursor()
        cursor.execute("DELETE FROM spatial_hotspots WHERE run_id = ?", (args.run_id,))
        if len(hotspots_df) > 0:
            write_spatial_hotspots(conn, args.run_id, hotspots_df)
        conn.commit()

        logger.info(f"Detected and wrote {len(hotspots_df)} hotspots")
        if len(hotspots_df) > 0:
            logger.info(f"Village count range: {hotspots_df['village_count'].min()} - {hotspots_df['village_count'].max()}")
            logger.info(f"Average village count: {hotspots_df['village_count'].mean():.1f}")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def run_feature_pipeline(args) -> None:
    db_path = Path(args.db_path)

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
        df = load_villages_with_coordinates(conn, schema_name=args.schema)

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
        batch_size = args.batch_size
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


def main():
    args = parse_args()
    if args.mode == "hotspots":
        run_hotspot_pipeline(args)
    else:
        run_feature_pipeline(args)


if __name__ == '__main__':
    main()
