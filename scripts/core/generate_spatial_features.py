#!/usr/bin/env python
"""Generate spatial features and hotspot tables from preprocessed data.

Usage:
    python scripts/core/generate_spatial_features.py --mode features
    python scripts/core/generate_spatial_features.py --mode hotspots
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipelines.spatial_pipeline import run_spatial_features_pipeline, run_hotspot_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate spatial features or hotspots")
    parser.add_argument("--db-path", default="data/villages.db")
    parser.add_argument("--schema", default="guangdong", choices=["guangdong", "national"],
                        help="Village table schema")
    parser.add_argument("--run-id", default=f"spatial_{int(time.time())}")
    parser.add_argument("--mode", choices=["features", "hotspots"], default="features",
                        help="features: village_spatial_features; hotspots: spatial_hotspots only")
    parser.add_argument("--hotspot-bandwidth-km", type=float, default=5.0)
    parser.add_argument("--hotspot-threshold-percentile", type=float, default=90.0)
    parser.add_argument("--hotspot-sample-size", type=int, default=50000)
    parser.add_argument("--hotspot-cluster-eps-km", type=float, default=1.1)
    parser.add_argument("--hotspot-cluster-min-samples", type=int, default=5)
    parser.add_argument("--hotspot-full-count-radius-km", type=float, default=3.0)
    parser.add_argument("--hotspot-sample-seed", type=int, default=20260712)
    parser.add_argument("--batch-size", type=int, default=10000, help="Rows per batch in features mode")

    args = parser.parse_args()

    try:
        if args.mode == "hotspots":
            result = run_hotspot_pipeline(
                db_path=args.db_path, run_id=args.run_id, schema_name=args.schema,
                bandwidth_km=args.hotspot_bandwidth_km,
                threshold_percentile=args.hotspot_threshold_percentile,
                sample_size=args.hotspot_sample_size,
                cluster_eps_km=args.hotspot_cluster_eps_km,
                cluster_min_samples=args.hotspot_cluster_min_samples,
                full_count_radius_km=args.hotspot_full_count_radius_km,
                sample_seed=args.hotspot_sample_seed,
            )
            logger.info(f"Done: {result['hotspots_count']} hotspots in {result['runtime_seconds']}s")
        else:
            result = run_spatial_features_pipeline(
                db_path=args.db_path, schema_name=args.schema, batch_size=args.batch_size,
            )
            logger.info(f"Done: {result['total_villages']} villages in {result['runtime_seconds']}s")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
