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
from src.spatial.hotspot_detector import HotspotDetector
from src.spatial.density_analyzer import DensityAnalyzer
from src.spatial.map_generator import MapGenerator
from src.data.db_writer import (
    create_spatial_analysis_tables,
    create_spatial_analysis_indexes,
    write_spatial_features,
    write_spatial_clusters,
    write_spatial_hotspots,
    write_region_spatial_aggregates
)

logger = logging.getLogger(__name__)


def run_spatial_analysis_pipeline(
    db_path: str,
    run_id: str,
    eps_km: float = 2.0,
    min_samples: int = 5,
    feature_run_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    generate_maps: bool = False
) -> Dict[str, Any]:
    """
    Run complete spatial analysis pipeline.

    Pipeline steps:
    1. Load coordinates from database
    2. Calculate k-nearest neighbors
    3. Run DBSCAN spatial clustering
    4. Extract spatial features
    5. Detect hotspots
    6. Calculate regional aggregates
    7. Integrate with semantic features (if feature_run_id provided)
    8. Write results to database
    9. Generate maps (if output_dir provided)

    Args:
        db_path: Path to SQLite database
        run_id: Unique identifier for this spatial analysis run
        eps_km: DBSCAN epsilon in kilometers (default: 2.0)
        min_samples: DBSCAN min_samples (default: 5)
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
    logger.info(f"DBSCAN parameters: eps={eps_km}km, min_samples={min_samples}")

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
        loader = CoordinateLoader()
        coords_df = loader.load_coordinates(conn)
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
        clusterer = SpatialClusterer(eps_km=eps_km, min_samples=min_samples)
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

        # Step 6: Detect hotspots
        logger.info("\n" + "="*80)
        logger.info("Step 7: Detecting spatial hotspots")
        logger.info("="*80)
        hotspot_detector = HotspotDetector(bandwidth_km=5.0, threshold_percentile=90)

        # Detect density hotspots (use all data for maximum accuracy)
        density_hotspots_df = hotspot_detector.detect_density_hotspots(
            coords, coords_df, sample_size=None  # None = use all data
        )

        # Detect naming hotspots (if semantic features available)
        naming_hotspots_df = pd.DataFrame()
        if feature_run_id:
            logger.info(f"Loading semantic features from run_id: {feature_run_id}")
            try:
                semantic_query = f"""
                    SELECT village_name, dominant_semantic_category
                    FROM village_features
                    WHERE run_id = '{feature_run_id}'
                """
                semantic_df = pd.read_sql_query(semantic_query, conn)

                # Merge with coords_df
                coords_with_semantic = coords_df.merge(semantic_df, on='village_name', how='left')
                semantic_categories = coords_with_semantic['dominant_semantic_category']

                naming_hotspots_df = hotspot_detector.detect_naming_hotspots(
                    coords, coords_df, semantic_categories
                )
            except Exception as e:
                logger.warning(f"Could not load semantic features: {e}")

        # Combine hotspots
        hotspots_df = pd.concat([density_hotspots_df, naming_hotspots_df], ignore_index=True)
        if len(hotspots_df) > 0:
            hotspots_df['hotspot_id'] = range(len(hotspots_df))

        logger.info(f"Detected {len(hotspots_df)} total hotspots")
        logger.info(f"  - Density hotspots: {len(density_hotspots_df)}")
        logger.info(f"  - Naming hotspots: {len(naming_hotspots_df)}")

        # Step 7: Calculate regional aggregates
        logger.info("\n" + "="*80)
        logger.info("Step 8: Calculating regional aggregates")
        logger.info("="*80)

        aggregates_list = []
        for region_level in ['city', 'county', 'town']:
            agg_df = density_analyzer.calculate_regional_aggregates(features_df, region_level)
            aggregates_list.append(agg_df)

        aggregates_df = pd.concat(aggregates_list, ignore_index=True)

        # Step 8: Write to database
        logger.info("\n" + "="*80)
        logger.info("Step 9: Writing results to database")
        logger.info("="*80)

        write_spatial_features(conn, run_id, features_df)
        write_spatial_clusters(conn, run_id, clusters_df)
        if len(hotspots_df) > 0:
            write_spatial_hotspots(conn, run_id, hotspots_df)
        write_region_spatial_aggregates(conn, run_id, aggregates_df)

        conn.commit()

        # Step 9: Generate maps (if requested)
        if generate_maps and output_dir:
            logger.info("\n" + "="*80)
            logger.info("Step 10: Generating interactive maps")
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

                # Hotspot map
                if len(hotspots_df) > 0:
                    logger.info("Generating hotspot map...")
                    map_gen.create_hotspot_map(
                        hotspots_df,
                        str(output_path / 'spatial_hotspots.html')
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
            'n_hotspots': len(hotspots_df),
            'n_density_hotspots': len(density_hotspots_df),
            'n_naming_hotspots': len(naming_hotspots_df),
            'elapsed_time': elapsed_time
        }

        logger.info("\n" + "="*80)
        logger.info("PIPELINE COMPLETE")
        logger.info("="*80)
        logger.info(f"Villages analyzed: {n_villages}")
        logger.info(f"Spatial clusters: {n_clusters}")
        logger.info(f"Noise points: {n_noise}")
        logger.info(f"Hotspots detected: {len(hotspots_df)}")
        logger.info(f"Elapsed time: {elapsed_time:.1f}s")
        logger.info("="*80)

        return stats

    finally:
        conn.close()
