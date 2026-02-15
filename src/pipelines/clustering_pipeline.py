"""
Clustering Pipeline for Region-Level Analysis.

This pipeline:
1. Builds region feature vectors from semantic and morphological data
2. Preprocesses features (StandardScaler + PCA)
3. Runs KMeans clustering with multiple k values
4. Selects best k based on silhouette score
5. Generates cluster profiles
6. Writes results to database and exports CSV reports
"""

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import time
import logging
import pickle

from ..clustering.feature_builder import RegionFeatureBuilder
from ..clustering.clustering_engine import ClusteringEngine
from ..clustering.cluster_profiler import ClusterProfiler
from ..data.db_writer import (
    create_clustering_tables,
    write_region_vectors,
    write_cluster_assignments,
    write_cluster_profiles,
    write_clustering_metrics
)

logger = logging.getLogger(__name__)


def run_clustering_pipeline(
    db_path: str,
    semantic_run_id: str,
    morphology_run_id: str,
    output_run_id: str,
    region_level: str = 'county',
    k_range: List[int] = [4, 6, 8, 10, 12, 15, 18, 20],
    use_semantic: bool = True,
    use_morphology: bool = True,
    use_diversity: bool = True,
    top_n_suffix2: int = 100,
    top_n_suffix3: int = 100,
    use_pca: bool = True,
    pca_n_components: int = 50,
    n_init: int = 20,
    max_iter: int = 500,
    random_state: int = 42,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run complete clustering pipeline.

    Args:
        db_path: Path to SQLite database
        semantic_run_id: Semantic analysis run ID
        morphology_run_id: Morphology analysis run ID
        output_run_id: Output run ID for clustering results
        region_level: Region level ('city', 'county', 'town')
        k_range: List of k values to try
        use_semantic: Include semantic features
        use_morphology: Include morphology features
        use_diversity: Include diversity features
        top_n_suffix2: Number of top bigram suffixes
        top_n_suffix3: Number of top trigram suffixes
        use_pca: Apply PCA dimensionality reduction
        pca_n_components: Number of PCA components
        n_init: KMeans initialization count
        max_iter: KMeans max iterations
        random_state: Random seed
        output_dir: Optional output directory for CSV exports

    Returns:
        Dictionary with pipeline results and metadata
    """
    logger.info(f"Starting clustering pipeline: run_id={output_run_id}")
    start_time = time.time()

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Create clustering tables
        logger.info("Creating clustering tables...")
        create_clustering_tables(conn)

        # Step 2: Build region feature vectors
        logger.info("Building region feature vectors...")
        feature_builder = RegionFeatureBuilder(conn)

        region_df, feature_names = feature_builder.build_region_vectors(
            semantic_run_id=semantic_run_id,
            morphology_run_id=morphology_run_id,
            region_level=region_level,
            use_semantic=use_semantic,
            use_morphology=use_morphology,
            use_diversity=use_diversity,
            top_n_suffix2=top_n_suffix2,
            top_n_suffix3=top_n_suffix3
        )

        logger.info(f"Built feature matrix: {len(region_df)} regions × {len(feature_names)} features")

        # Extract feature matrix
        X = region_df[feature_names].values

        # Step 3: Preprocess features
        logger.info("Preprocessing features...")
        engine = ClusteringEngine(random_state=random_state)
        X_processed = engine.preprocess(X, use_pca=use_pca, n_components=pca_n_components)

        logger.info(f"Preprocessed feature matrix: {X_processed.shape}")

        # Step 4: Run KMeans clustering
        logger.info(f"Running KMeans clustering for k={k_range}...")
        results = engine.fit_kmeans(X_processed, k_range=k_range, n_init=n_init, max_iter=max_iter)

        # Step 5: Select best k
        logger.info("Selecting best k...")
        best_result = engine.select_best_k(results, metric='silhouette_score')
        best_k = best_result['k']
        best_model = best_result['model']
        best_labels = best_result['labels']
        best_silhouette = best_result['silhouette_score']

        logger.info(f"Best k={best_k} with silhouette_score={best_silhouette:.4f}")

        # Step 6: Calculate distances to centroids
        distances = engine.get_cluster_distances(X_processed, best_model)

        # Step 7: Generate cluster profiles
        logger.info("Generating cluster profiles...")
        profiles_df = ClusterProfiler.generate_cluster_profiles(
            X_processed,
            best_labels,
            region_df[['region_id', 'region_name']],
            feature_names,
            distances,
            top_n_features=10,
            top_n_regions=5
        )

        logger.info(f"Generated {len(profiles_df)} cluster profiles")

        # Step 8: Write results to database
        logger.info("Writing results to database...")

        # Write region vectors
        write_region_vectors(conn, output_run_id, region_df)

        # Write cluster assignments
        write_cluster_assignments(
            conn, output_run_id, region_df[['region_id', 'region_name']],
            best_labels, distances, 'kmeans', best_k, best_silhouette
        )

        # Write cluster profiles
        write_cluster_profiles(conn, output_run_id, profiles_df, 'kmeans')

        # Write clustering metrics
        metrics_dict = {
            'algorithm': 'kmeans',
            'results': results,
            'n_features': len(feature_names),
            'pca_enabled': use_pca,
            'pca_n_components': pca_n_components if use_pca else None
        }
        write_clustering_metrics(conn, output_run_id, metrics_dict)

        # Step 9: Export CSV reports (if output_dir specified)
        if output_dir:
            logger.info(f"Exporting CSV reports to {output_dir}...")
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Export config
            config = {
                'run_id': output_run_id,
                'semantic_run_id': semantic_run_id,
                'morphology_run_id': morphology_run_id,
                'region_level': region_level,
                'k_range': k_range,
                'best_k': best_k,
                'best_silhouette_score': float(best_silhouette),
                'use_semantic': use_semantic,
                'use_morphology': use_morphology,
                'use_diversity': use_diversity,
                'top_n_suffix2': top_n_suffix2,
                'top_n_suffix3': top_n_suffix3,
                'use_pca': use_pca,
                'pca_n_components': pca_n_components,
                'n_features': len(feature_names),
                'n_regions': len(region_df),
                'random_state': random_state,
                'created_at': time.time()
            }

            with open(output_path / 'config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            # Export region vectors
            region_df.to_csv(output_path / 'region_vectors.csv', index=False, encoding='utf-8-sig')

            # Export cluster assignments
            assignments_df = region_df[['region_id', 'region_name']].copy()
            assignments_df['cluster_id'] = best_labels
            assignments_df['distance_to_centroid'] = distances
            assignments_df.to_csv(output_path / 'cluster_assignments_kmeans.csv', index=False, encoding='utf-8-sig')

            # Export cluster profiles
            profiles_df.to_csv(output_path / 'cluster_profiles_kmeans.csv', index=False, encoding='utf-8-sig')

            # Export clustering metrics
            metrics_df = pd.DataFrame([{
                'k': r['k'],
                'silhouette_score': r['silhouette_score'],
                'davies_bouldin_index': r['davies_bouldin_index'],
                'calinski_harabasz_score': r['calinski_harabasz_score'],
                'inertia': r['inertia']
            } for r in results])
            metrics_df.to_csv(output_path / 'clustering_metrics.csv', index=False, encoding='utf-8-sig')

            # Save models
            models_dir = output_path / 'models'
            models_dir.mkdir(exist_ok=True)

            with open(models_dir / 'scaler.pkl', 'wb') as f:
                pickle.dump(engine.scaler, f)

            if engine.pca:
                with open(models_dir / 'pca.pkl', 'wb') as f:
                    pickle.dump(engine.pca, f)

            with open(models_dir / f'kmeans_k{best_k}.pkl', 'wb') as f:
                pickle.dump(best_model, f)

            logger.info(f"Exported results to {output_path}")

        elapsed = time.time() - start_time
        logger.info(f"Clustering pipeline completed in {elapsed:.2f}s")

        return {
            'run_id': output_run_id,
            'best_k': best_k,
            'best_silhouette_score': float(best_silhouette),
            'n_regions': len(region_df),
            'n_features': len(feature_names),
            'elapsed_time': elapsed,
            'output_dir': str(output_path) if output_dir else None
        }

    except Exception as e:
        logger.error(f"Error in clustering pipeline: {e}")
        raise
    finally:
        conn.close()

