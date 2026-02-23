"""
Phase 4: Compute village-level clustering.

This script computes clustering for individual villages and fills the
kmeans_cluster_id, dbscan_cluster_id, and gmm_cluster_id columns in village_features.
"""

import sqlite3
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def compute_village_clustering(conn):
    """
    Compute clustering for villages based on their features.
    """
    print("Loading village features...")
    query = """
        SELECT
            village_id,
            name_length,
            sem_mountain, sem_water, sem_settlement, sem_direction,
            sem_clan, sem_symbolic, sem_agriculture, sem_vegetation, sem_infrastructure
        FROM village_features
        WHERE has_valid_chars = 1
    """
    df = pd.read_sql_query(query, conn)
    print(f"  Loaded {len(df)} villages with valid features")

    # Prepare feature matrix
    feature_cols = [
        'name_length',
        'sem_mountain', 'sem_water', 'sem_settlement', 'sem_direction',
        'sem_clan', 'sem_symbolic', 'sem_agriculture', 'sem_vegetation', 'sem_infrastructure'
    ]
    X = df[feature_cols].values

    # Standardize features
    print("Standardizing features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # KMeans clustering
    print("Running KMeans clustering (k=8)...")
    kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
    df['kmeans_cluster_id'] = kmeans.fit_predict(X_scaled)

    # DBSCAN clustering
    print("Running DBSCAN clustering (eps=0.3, min_samples=50)...")
    dbscan = DBSCAN(eps=0.3, min_samples=50)
    df['dbscan_cluster_id'] = dbscan.fit_predict(X_scaled)

    # GMM clustering
    print("Running GMM clustering (n_components=6)...")
    gmm = GaussianMixture(n_components=6, random_state=42)
    df['gmm_cluster_id'] = gmm.fit_predict(X_scaled)

    # Update database
    print("Updating village_features table...")
    cursor = conn.cursor()

    update_query = """
        UPDATE village_features
        SET kmeans_cluster_id = ?,
            dbscan_cluster_id = ?,
            gmm_cluster_id = ?
        WHERE village_id = ?
    """

    updates = [
        (
            int(row['kmeans_cluster_id']),
            int(row['dbscan_cluster_id']),
            int(row['gmm_cluster_id']),
            row['village_id']
        )
        for _, row in df.iterrows()
    ]

    cursor.executemany(update_query, updates)
    conn.commit()

    print(f"  Updated {len(updates)} villages")

    # Print cluster statistics
    print("\nCluster statistics:")
    print(f"  KMeans: {df['kmeans_cluster_id'].nunique()} clusters")
    print(f"  DBSCAN: {df['dbscan_cluster_id'].nunique()} clusters (including noise: {(df['dbscan_cluster_id'] == -1).sum()})")
    print(f"  GMM: {df['gmm_cluster_id'].nunique()} clusters")

def main():
    db_path = project_root / 'data' / 'villages.db'

    print(f"Connecting to database: {db_path}\n")
    conn = sqlite3.connect(db_path)

    compute_village_clustering(conn)

    # Verify updates
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(kmeans_cluster_id) as kmeans,
            COUNT(dbscan_cluster_id) as dbscan,
            COUNT(gmm_cluster_id) as gmm
        FROM village_features
    """)
    result = cursor.fetchone()
    print(f"\nVerification:")
    print(f"  Total villages: {result[0]}")
    print(f"  kmeans_cluster_id filled: {result[1]}")
    print(f"  dbscan_cluster_id filled: {result[2]}")
    print(f"  gmm_cluster_id filled: {result[3]}")

    conn.close()
    print("\nPhase 4 complete")

if __name__ == '__main__':
    main()
