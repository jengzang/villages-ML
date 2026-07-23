"""
Spatial Analysis Pipeline.

End-to-end pipeline for geographic analysis of village data.
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import time

from src.spatial.coordinate_loader import CoordinateLoader
from src.spatial.distance_calculator import DistanceCalculator
from src.spatial.spatial_clustering import SpatialClusterer
from src.spatial.spatial_features import SpatialFeatureExtractor
from src.spatial.density_analyzer import DensityAnalyzer
from src.spatial.map_generator import MapGenerator
from src.data.db_writer import (
    create_spatial_analysis_tables,
    create_spatial_analysis_indexes,
    write_spatial_features,
    write_spatial_clusters,
    write_village_cluster_assignments,
    write_region_spatial_aggregates
)
from src.schema import REGION_LEVELS, get_schema

logger = logging.getLogger(__name__)


def run_spatial_analysis_pipeline(
    db_path: str,
    run_id: str,
    eps_km: float = 0.5,
    min_samples: int = 5,
    method: str = 'dbscan',
    feature_run_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    generate_maps: bool = False,
    schema_name: str = 'guangdong',
    coordinate_bounds: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Run complete spatial analysis pipeline.

    Pipeline steps:
    1. Load coordinates from database
    2. Calculate k-nearest neighbors
    3. Run DBSCAN/HDBSCAN spatial clustering
    4. Extract spatial features
    5. Detect hotspots
    6. Calculate regional aggregates
    7. Integrate with semantic features (if feature_run_id provided)
    8. Write results to database
    9. Generate maps (if output_dir provided)

    Args:
        db_path: Path to SQLite database
        run_id: Unique identifier for this spatial analysis run
        eps_km: DBSCAN epsilon in kilometers (default: 0.5)
        min_samples: DBSCAN min_samples / HDBSCAN min_cluster_size (default: 5)
        method: Clustering method - 'dbscan' or 'hdbscan' (default: 'dbscan')
        feature_run_id: Optional run_id to integrate with semantic features
        output_dir: Optional directory for maps and exports
        generate_maps: Whether to generate interactive maps

    Returns:
        Dictionary with pipeline statistics
    """
    logger.info("="*80)
    logger.info("SPATIAL ANALYSIS PIPELINE")
    logger.info("="*80)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Database: {db_path}")
    logger.info(f"Schema: {schema_name}")
    logger.info(f"Clustering: {method}, eps={eps_km}km, min_samples={min_samples}")

    start_time = time.time()

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Create tables if they don't exist
        logger.info("\n" + "="*80)
        logger.info("Step 1: Creating database tables")
        logger.info("="*80)
        create_spatial_analysis_tables(conn)
        create_spatial_analysis_indexes(conn)

        # Step 1: Load coordinates
        logger.info("\n" + "="*80)
        logger.info("Step 2: Loading coordinates")
        logger.info("="*80)
        loader = CoordinateLoader(bounds=coordinate_bounds)
        coords_df = loader.load_coordinates(conn, schema=get_schema(schema_name))
        coords = loader.get_coordinate_array(coords_df)

        n_villages = len(coords_df)
        logger.info(f"Loaded {n_villages} villages with valid coordinates")

        # Step 2: Calculate distances and k-NN
        logger.info("\n" + "="*80)
        logger.info("Step 3: Calculating distances and k-nearest neighbors")
        logger.info("="*80)
        calc = DistanceCalculator()
        calc.build_tree(coords)
        nn_distances, nn_indices = calc.nearest_neighbors(coords, k=10)

        # Step 3: Calculate local density
        logger.info("\n" + "="*80)
        logger.info("Step 4: Calculating local density")
        logger.info("="*80)
        density_analyzer = DensityAnalyzer()
        local_density = density_analyzer.calculate_local_density(calc, coords, radii_km=[1, 5, 10])

        # Step 4: Run spatial clustering
        logger.info("\n" + "="*80)
        logger.info("Step 5: Running spatial clustering")
        logger.info("="*80)
        clusterer = SpatialClusterer(eps_km=eps_km, min_samples=min_samples, method=method)
        labels = clusterer.fit(coords)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        logger.info(f"Found {n_clusters} spatial clusters")
        logger.info(f"Noise points: {n_noise} ({n_noise/n_villages*100:.1f}%)")

        # Get cluster profiles
        clusters_df = clusterer.get_cluster_profiles(coords, labels, coords_df)

        # Step 5: Extract spatial features
        logger.info("\n" + "="*80)
        logger.info("Step 6: Extracting spatial features")
        logger.info("="*80)
        feature_extractor = SpatialFeatureExtractor()
        features_df = feature_extractor.extract_features(
            coords_df, coords, labels, nn_distances, local_density
        )

        # Step 6: Calculate regional aggregates
        logger.info("\n" + "="*80)
        logger.info("Step 7: Calculating regional aggregates")
        logger.info("="*80)

        aggregates_list = []
        for region_level in [REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2]]:
            agg_df = density_analyzer.calculate_regional_aggregates(features_df, region_level)
            aggregates_list.append(agg_df)

        aggregates_df = pd.concat(aggregates_list, ignore_index=True)

        # Step 7: Write to database
        logger.info("\n" + "="*80)
        logger.info("Step 8: Writing results to database")
        logger.info("="*80)

        write_spatial_features(conn, run_id, features_df)
        write_spatial_clusters(conn, run_id, clusters_df)

        # Build village cluster assignments from labels
        probabilities = getattr(clusterer.model, 'probabilities_', None)
        write_village_cluster_assignments(conn, run_id, coords_df, labels, probabilities, clusters_df)

        write_region_spatial_aggregates(conn, run_id, aggregates_df)

        conn.commit()

        # Step 8: Generate maps (if requested)
        if generate_maps and output_dir:
            logger.info("\n" + "="*80)
            logger.info("Step 9: Generating interactive maps")
            logger.info("="*80)

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            try:
                map_gen = MapGenerator()

                # Cluster map
                logger.info("Generating cluster map...")
                map_gen.create_cluster_map(
                    features_df,
                    str(output_path / 'spatial_clusters.html')
                )

                # Density heatmap
                logger.info("Generating density heatmap...")
                map_gen.create_density_heatmap(
                    features_df,
                    str(output_path / 'density_heatmap.html')
                )

                logger.info(f"Maps saved to {output_path}")

            except ImportError as e:
                logger.warning(f"Could not generate maps: {e}")

        # Calculate statistics
        elapsed_time = time.time() - start_time

        stats = {
            'run_id': run_id,
            'n_villages': n_villages,
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'n_hotspots': 0,
            'elapsed_time': elapsed_time
        }

        logger.info("\n" + "="*80)
        logger.info("PIPELINE COMPLETE")
        logger.info("="*80)
        logger.info(f"Villages analyzed: {n_villages}")
        logger.info(f"Spatial clusters: {n_clusters}")
        logger.info(f"Noise points: {n_noise}")
        logger.info(f"Elapsed time: {elapsed_time:.1f}s")
        logger.info("="*80)

        return stats

    finally:
        conn.close()


def run_spatial_features_pipeline(
    db_path: str,
    schema_name: str = 'guangdong',
    k: int = 10,
    batch_size: int = 10000,
) -> dict[str, Any]:
    """Generate village_spatial_features from preprocessed coordinate data.

    Computes k-NN distances, density, and isolation scores per village.
    """
    from sklearn.neighbors import NearestNeighbors
    from src.schema import get_schema, REGION_LEVELS

    logger.info("=" * 80)
    logger.info("Generating village_spatial_features table")
    logger.info("=" * 80)
    logger.info(f"Database: {db_path}")

    S = get_schema(schema_name)
    start_time = time.time()
    conn = sqlite3.connect(db_path)

    try:
        # Create table
        logger.info("Creating village_spatial_features table...")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS village_spatial_features (
                village_id TEXT PRIMARY KEY,
                village_name TEXT NOT NULL,
                city TEXT, county TEXT, town TEXT,
                longitude REAL NOT NULL, latitude REAL NOT NULL,
                nn_distance_1 REAL, nn_distance_5 REAL, nn_distance_10 REAL,
                local_density_1km INTEGER, local_density_5km INTEGER, local_density_10km INTEGER,
                isolation_score REAL, is_isolated INTEGER,
                spatial_cluster_id INTEGER, cluster_size INTEGER
            )
        """)
        conn.commit()

        # Load villages with coordinates
        logger.info("Loading villages with coordinates...")
        query = f"""
        SELECT {S.village_id_col} as village_id,
               "{S.city_col}" as city,
               "{S.county_col}" as county,
               "{S.township_col}" as town,
               "{S.committee_col_preprocessed}" as village_committee,
               "{S.village_name_col_prefix_removed}" as village_name,
               {S.longitude_col} as longitude,
               {S.latitude_col} as latitude
        FROM "{S.preprocessed_table}"
        WHERE {S.village_id_col} IS NOT NULL
          AND {S.longitude_col} IS NOT NULL AND {S.latitude_col} IS NOT NULL
          AND {S.longitude_col} != '' AND {S.latitude_col} != ''
        """
        df = pd.read_sql_query(query, conn)
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df = df.dropna(subset=['longitude', 'latitude'])
        df = df[(df['longitude'] != 0) & (df['latitude'] != 0)]
        logger.info(f"Loaded {len(df):,} villages with valid coordinates")

        if len(df) == 0:
            logger.error("No villages with valid coordinates found!")
            conn.close()
            return {'error': 'no_valid_coordinates'}

        # Compute k-NN spatial features
        logger.info(f"Computing spatial features (k={k})...")
        coords = df[['latitude', 'longitude']].values
        nbrs = NearestNeighbors(n_neighbors=k + 1, metric='haversine', algorithm='ball_tree')
        nbrs.fit(np.radians(coords))
        distances, _ = nbrs.kneighbors(np.radians(coords))
        distances_km = distances * 6371

        features = pd.DataFrame()
        features['village_id'] = df['village_id'].values
        features['village_name'] = df['village_name'].values
        features[REGION_LEVELS[0]] = df['city'].values
        features[REGION_LEVELS[1]] = df['county'].values
        features[REGION_LEVELS[2]] = df['town'].values
        features['longitude'] = df['longitude'].values
        features['latitude'] = df['latitude'].values
        features['nn_distance_1'] = distances_km[:, 1]
        features['nn_distance_5'] = None
        features['nn_distance_10'] = distances_km[:, 1:].mean(axis=1)
        for col in ['local_density_1km', 'local_density_5km', 'local_density_10km',
                     'isolation_score', 'is_isolated', 'spatial_cluster_id', 'cluster_size']:
            features[col] = None

        logger.info(f"Computed spatial features for {len(features):,} villages")

        # Write in batches
        logger.info("Writing spatial features to database...")
        total_batches = (len(features) + batch_size - 1) // batch_size
        cols = ['village_id', 'village_name', REGION_LEVELS[0], REGION_LEVELS[1], REGION_LEVELS[2],
                'longitude', 'latitude', 'nn_distance_1', 'nn_distance_5', 'nn_distance_10',
                'local_density_1km', 'local_density_5km', 'local_density_10km',
                'isolation_score', 'is_isolated', 'spatial_cluster_id', 'cluster_size']

        for i in range(0, len(features), batch_size):
            batch = features.iloc[i:i + batch_size]
            values = [tuple(row[col] for col in cols) for _, row in batch.iterrows()]
            placeholders = '(' + ','.join(['?'] * len(cols)) + ')'
            cursor.executemany(
                f"INSERT OR REPLACE INTO village_spatial_features ({', '.join(cols)}) VALUES {placeholders}",
                values,
            )
            batch_num = i // batch_size + 1
            logger.info(f"Batch {batch_num}/{total_batches} written ({len(batch)} rows)")

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM village_spatial_features")
        count = cursor.fetchone()[0]
        logger.info(f"Verification: village_spatial_features has {count:,} rows")
        logger.info("village_spatial_features generation completed successfully!")

        elapsed = time.time() - start_time
        return {'total_villages': len(features), 'runtime_seconds': round(elapsed, 2)}

    except Exception:
        logger.error("Error in spatial features pipeline", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def run_hotspot_pipeline(
    db_path: str,
    run_id: str = '',
    schema_name: str = 'guangdong',
    bandwidth_km: float = 5.0,
    threshold_percentile: float = 90.0,
    sample_size: int = 50000,
    cluster_eps_km: float = 1.1,
    cluster_min_samples: int = 5,
    full_count_radius_km: float = 3.0,
    sample_seed: int = 20260712,
) -> dict[str, Any]:
    """Generate spatial_hotspots from preprocessed coordinate data."""
    from src.schema import get_schema
    from src.data.db_writer import create_spatial_analysis_tables, create_spatial_analysis_indexes, write_spatial_hotspots
    from src.spatial.hotspot_detector import HotspotDetector

    if not run_id:
        run_id = f"spatial_{int(time.time())}"

    logger.info("=" * 80)
    logger.info("Generating spatial_hotspots table")
    logger.info("=" * 80)
    logger.info(f"Database: {db_path}, Run ID: {run_id}")
    logger.info(f"Hotspot params: bandwidth={bandwidth_km}km, threshold=p{threshold_percentile}, "
                f"sample={sample_size}, cluster_eps={cluster_eps_km}km")

    start_time = time.time()
    conn = sqlite3.connect(db_path)

    try:
        create_spatial_analysis_tables(conn)
        create_spatial_analysis_indexes(conn)

        loader = CoordinateLoader()
        coords_df = loader.load_coordinates(conn, schema=get_schema(schema_name))
        coords = loader.get_coordinate_array(coords_df)

        if len(coords_df) == 0:
            logger.error("No villages with valid coordinates found!")
            return {'error': 'no_valid_coordinates'}

        detector = HotspotDetector(
            bandwidth_km=bandwidth_km,
            threshold_percentile=threshold_percentile,
            cluster_eps_km=cluster_eps_km,
            cluster_min_samples=cluster_min_samples,
            sample_seed=sample_seed,
            full_count_radius_km=full_count_radius_km,
        )
        hotspots_df = detector.detect_density_hotspots(coords, coords_df, sample_size=sample_size)

        if len(hotspots_df) > 0:
            hotspots_df["hotspot_id"] = range(len(hotspots_df))

        cursor = conn.cursor()
        cursor.execute("DELETE FROM spatial_hotspots WHERE run_id = ?", (run_id,))
        if len(hotspots_df) > 0:
            write_spatial_hotspots(conn, run_id, hotspots_df)
        conn.commit()

        logger.info(f"Detected and wrote {len(hotspots_df):,} hotspots")
        if len(hotspots_df) > 0:
            logger.info(f"Village count range: {hotspots_df['village_count'].min()} - {hotspots_df['village_count'].max()}")
            logger.info(f"Average village count: {hotspots_df['village_count'].mean():.1f}")

        elapsed = time.time() - start_time
        return {'hotspots_count': len(hotspots_df), 'runtime_seconds': round(elapsed, 2)}

    except Exception:
        logger.error("Error in hotspot pipeline", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()
