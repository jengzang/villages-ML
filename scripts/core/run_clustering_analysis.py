"""
Command-line script to run clustering analysis pipeline.

Usage:
    python scripts/run_clustering_analysis.py \\
        --semantic-run-id semantic_001 \\
        --morphology-run-id morph_001 \\
        --output-run-id cluster_001 \\
        --region-level county \\
        --k-range 4 6 8 10 12 15 18 20

Example:
    python scripts/run_clustering_analysis.py \\
        --semantic-run-id semantic_001 \\
        --morphology-run-id morph_001 \\
        --output-run-id cluster_001
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.pipelines.clustering_pipeline import run_clustering_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Run clustering analysis on region-level features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Required arguments
    parser.add_argument(
        '--semantic-run-id',
        required=True,
        help='Semantic analysis run ID (e.g., semantic_001)'
    )
    parser.add_argument(
        '--morphology-run-id',
        required=True,
        help='Morphology analysis run ID (e.g., morph_001)'
    )
    parser.add_argument(
        '--output-run-id',
        required=True,
        help='Output run ID for clustering results (e.g., cluster_001)'
    )

    # Optional arguments
    parser.add_argument(
        '--db-path',
        default='data/villages.db',
        help='Path to SQLite database (default: data/villages.db)'
    )
    parser.add_argument(
        '--region-level',
        default='county',
        choices=['city', 'county', 'town'],
        help='Region level for clustering (default: county)'
    )
    parser.add_argument(
        '--k-range',
        nargs='+',
        type=int,
        default=[4, 6, 8, 10, 12, 15, 18, 20],
        help='List of k values to try (default: 4 6 8 10 12 15 18 20)'
    )
    parser.add_argument(
        '--top-n-suffix2',
        type=int,
        default=100,
        help='Number of top bigram suffixes to use (default: 100)'
    )
    parser.add_argument(
        '--top-n-suffix3',
        type=int,
        default=100,
        help='Number of top trigram suffixes to use (default: 100)'
    )
    parser.add_argument(
        '--no-pca',
        action='store_true',
        help='Disable PCA dimensionality reduction'
    )
    parser.add_argument(
        '--pca-components',
        type=int,
        default=50,
        help='Number of PCA components (default: 50)'
    )
    parser.add_argument(
        '--n-init',
        type=int,
        default=20,
        help='KMeans initialization count (default: 20)'
    )
    parser.add_argument(
        '--max-iter',
        type=int,
        default=500,
        help='KMeans max iterations (default: 500)'
    )
    parser.add_argument(
        '--random-state',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory for CSV exports (default: results/<output_run_id>)'
    )

    args = parser.parse_args()

    # Set default output directory
    if not args.output_dir:
        args.output_dir = f'results/{args.output_run_id}'

    # Log configuration
    logger.info("=" * 80)
    logger.info("Clustering Analysis Pipeline")
    logger.info("=" * 80)
    logger.info(f"Semantic run ID: {args.semantic_run_id}")
    logger.info(f"Morphology run ID: {args.morphology_run_id}")
    logger.info(f"Output run ID: {args.output_run_id}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Region level: {args.region_level}")
    logger.info(f"K range: {args.k_range}")
    logger.info(f"Top N suffix2: {args.top_n_suffix2}")
    logger.info(f"Top N suffix3: {args.top_n_suffix3}")
    logger.info(f"Use PCA: {not args.no_pca}")
    if not args.no_pca:
        logger.info(f"PCA components: {args.pca_components}")
    logger.info(f"N init: {args.n_init}")
    logger.info(f"Max iter: {args.max_iter}")
    logger.info(f"Random state: {args.random_state}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info("=" * 80)

    try:
        # Run pipeline
        result = run_clustering_pipeline(
            db_path=args.db_path,
            semantic_run_id=args.semantic_run_id,
            morphology_run_id=args.morphology_run_id,
            output_run_id=args.output_run_id,
            region_level=args.region_level,
            k_range=args.k_range,
            use_semantic=True,
            use_morphology=True,
            use_diversity=True,
            top_n_suffix2=args.top_n_suffix2,
            top_n_suffix3=args.top_n_suffix3,
            use_pca=not args.no_pca,
            pca_n_components=args.pca_components,
            n_init=args.n_init,
            max_iter=args.max_iter,
            random_state=args.random_state,
            output_dir=args.output_dir
        )

        # Print summary
        logger.info("=" * 80)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 80)
        logger.info(f"Run ID: {result['run_id']}")
        logger.info(f"Best k: {result['best_k']}")
        logger.info(f"Best silhouette score: {result['best_silhouette_score']:.4f}")
        logger.info(f"Number of regions: {result['n_regions']}")
        logger.info(f"Number of features: {result['n_features']}")
        logger.info(f"Elapsed time: {result['elapsed_time']:.2f}s")
        if result['output_dir']:
            logger.info(f"Results exported to: {result['output_dir']}")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
