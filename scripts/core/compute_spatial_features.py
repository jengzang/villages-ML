"""
Phase 5: Compute complete spatial features.

This script computes all spatial features for villages and fills the
spatial feature columns in village_spatial_features.
"""

import sqlite3
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import DBSCAN

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate haversine distance between two points in kilometers.
    """
    R = 6371  # Earth radius in km

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c

def compute_spatial_features(conn):
    """
    Compute spatial features for all villages.
    """
    print("Loading village spatial data...")
    query = """
        SELECT
            village_id,
            latitude,
            longitude
        FROM village_spatial_features
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    print(f"  Loaded {len(df)} villages with valid coordinates")

    # Convert to numeric
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Remove invalid coordinates
    df = df.dropna(subset=['latitude', 'longitude'])
    print(f"  {len(df)} villages after removing invalid coordinates")

    # Prepare coordinate matrix
    coords = df[['latitude', 'longitude']].values

    # Build BallTree for efficient spatial queries
    print("Building BallTree for efficient spatial queries...")
    nbrs = NearestNeighbors(n_neighbors=6, metric='haversine', algorithm='ball_tree')
    nbrs.fit(np.radians(coords))

    # Compute nearest neighbor distances
    print("Computing nearest neighbor distances...")
    distances, indices = nbrs.kneighbors(np.radians(coords))

    # Convert to km (distances are in radians)
    distances_km = distances * 6371

    # 5th nearest neighbor distance (index 5, since index 0 is self)
    df['nn_distance_5'] = distances_km[:, 5]

    # Compute local densities using efficient radius queries
    print("Computing local densities using BallTree radius queries...")
    for radius_km in [1, 5, 10]:
        print(f"  Computing density within {radius_km}km...")
        radius_rad = radius_km / 6371  # Convert km to radians

        # Efficient radius query using BallTree
        neighbors = nbrs.radius_neighbors(np.radians(coords), radius=radius_rad, return_distance=False)

        # Count neighbors (excluding self)
        densities = [len(neighbor_indices) - 1 for neighbor_indices in neighbors]
        df[f'local_density_{radius_km}km'] = densities

    # Compute isolation score (inverse of 1km density)
    print("Computing isolation scores...")
    df['isolation_score'] = 1.0 / (df['local_density_1km'] + 1)

    # Mark isolated villages (density < 5 within 1km)
    df['is_isolated'] = (df['local_density_1km'] < 5).astype(int)

    # DBSCAN clustering
    print("Running DBSCAN spatial clustering (eps=2km, min_samples=5)...")
    # Convert eps from km to radians
    eps_rad = 2.0 / 6371
    dbscan = DBSCAN(eps=eps_rad, min_samples=5, metric='haversine')
    df['spatial_cluster_id'] = dbscan.fit_predict(np.radians(coords))

    # Compute cluster sizes
    print("Computing cluster sizes...")
    cluster_sizes = df['spatial_cluster_id'].value_counts().to_dict()
    df['cluster_size'] = df['spatial_cluster_id'].map(cluster_sizes)
    # Noise points (cluster_id = -1) have cluster_size = 1
    df.loc[df['spatial_cluster_id'] == -1, 'cluster_size'] = 1

    # Update database
    print("Updating village_spatial_features table...")
    cursor = conn.cursor()

    update_query = """
        UPDATE village_spatial_features
        SET nn_distance_5 = ?,
            local_density_1km = ?,
            local_density_5km = ?,
            local_density_10km = ?,
            isolation_score = ?,
            is_isolated = ?,
            spatial_cluster_id = ?,
            cluster_size = ?
        WHERE village_id = ?
    """

    updates = [
        (
            float(row['nn_distance_5']),
            int(row['local_density_1km']),
            int(row['local_density_5km']),
            int(row['local_density_10km']),
            float(row['isolation_score']),
            int(row['is_isolated']),
            int(row['spatial_cluster_id']),
            int(row['cluster_size']),
            row['village_id']
        )
        for _, row in df.iterrows()
    ]

    cursor.executemany(update_query, updates)
    conn.commit()

    print(f"  Updated {len(updates)} villages")

    # Print statistics
    print("\nSpatial feature statistics:")
    print(f"  Avg 5-NN distance: {df['nn_distance_5'].mean():.2f} km")
    print(f"  Avg 1km density: {df['local_density_1km'].mean():.1f} villages")
    print(f"  Avg 5km density: {df['local_density_5km'].mean():.1f} villages")
    print(f"  Avg 10km density: {df['local_density_10km'].mean():.1f} villages")
    print(f"  Isolated villages: {df['is_isolated'].sum()} ({df['is_isolated'].mean()*100:.1f}%)")
    print(f"  Spatial clusters: {df['spatial_cluster_id'].nunique()} (including {(df['spatial_cluster_id'] == -1).sum()} noise points)")

def main():
    db_path = project_root / 'data' / 'villages.db'

    print(f"Connecting to database: {db_path}\n")
    conn = sqlite3.connect(db_path)

    compute_spatial_features(conn)

    # Verify updates
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(nn_distance_5) as nn5,
            COUNT(local_density_1km) as dens1,
            COUNT(local_density_5km) as dens5,
            COUNT(local_density_10km) as dens10,
            COUNT(isolation_score) as iso,
            COUNT(is_isolated) as is_iso,
            COUNT(spatial_cluster_id) as cluster,
            COUNT(cluster_size) as cluster_size
        FROM village_spatial_features
    """)
    result = cursor.fetchone()
    print(f"\nVerification:")
    print(f"  Total villages: {result[0]}")
    print(f"  nn_distance_5 filled: {result[1]}")
    print(f"  local_density_1km filled: {result[2]}")
    print(f"  local_density_5km filled: {result[3]}")
    print(f"  local_density_10km filled: {result[4]}")
    print(f"  isolation_score filled: {result[5]}")
    print(f"  is_isolated filled: {result[6]}")
    print(f"  spatial_cluster_id filled: {result[7]}")
    print(f"  cluster_size filled: {result[8]}")

    conn.close()
    print("\nPhase 5 complete")

if __name__ == '__main__':
    main()
