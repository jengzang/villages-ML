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
from src.schema import get_schema

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
        for region_level in ['city', 'county', 'town']:
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
