"""Benchmark query performance with village_id.

This script benchmarks:
1. Query speed using village_id vs. composite keys
2. Average query time per operation
3. Performance improvement metrics
"""

import sqlite3
import time
import random
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def benchmark_village_id_queries(db_path: str, sample_size: int = 1000):
    """Benchmark queries using village_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get sample village_ids
    cursor.execute(f"""
        SELECT village_id
        FROM 广东省自然村_预处理
        WHERE village_id IS NOT NULL
        LIMIT {sample_size}
    """)
    village_ids = [row[0] for row in cursor.fetchall()]

    if len(village_ids) == 0:
        logger.error("No village_ids found in database")
        return

    logger.info(f"Benchmarking with {len(village_ids)} village_ids...")

    # Benchmark: Query village_ngrams using village_id
    start = time.time()
    for vid in village_ids:
        cursor.execute("SELECT * FROM village_ngrams WHERE village_id = ?", (vid,))
        cursor.fetchone()
    elapsed_ngrams = time.time() - start

    # Benchmark: Query village_semantic_structure using village_id
    start = time.time()
    for vid in village_ids:
        cursor.execute("SELECT * FROM village_semantic_structure WHERE village_id = ?", (vid,))
        cursor.fetchone()
    elapsed_semantic = time.time() - start

    # Benchmark: Query village_features using village_id
    start = time.time()
    for vid in village_ids:
        cursor.execute("SELECT * FROM village_features WHERE village_id = ?", (vid,))
        cursor.fetchone()
    elapsed_features = time.time() - start

    conn.close()

    return {
        'ngrams': elapsed_ngrams,
        'semantic': elapsed_semantic,
        'features': elapsed_features,
        'sample_size': len(village_ids)
    }


def main():
    """Run benchmark tests."""
    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info("\n" + "="*60)
    logger.info("Village ID Query Performance Benchmark")
    logger.info("="*60)
    logger.info(f"Database: {db_path}")

    # Run benchmark
    results = benchmark_village_id_queries(str(db_path), sample_size=1000)

    if results:
        logger.info("\n" + "="*60)
        logger.info("Benchmark Results")
        logger.info("="*60)
        logger.info(f"Sample size: {results['sample_size']} queries")
        logger.info("")
        logger.info("Query times using village_id:")
        logger.info(f"  village_ngrams:           {results['ngrams']:.2f}s total, {results['ngrams']/results['sample_size']*1000:.2f}ms avg")
        logger.info(f"  village_semantic_structure: {results['semantic']:.2f}s total, {results['semantic']/results['sample_size']*1000:.2f}ms avg")
        logger.info(f"  village_features:         {results['features']:.2f}s total, {results['features']/results['sample_size']*1000:.2f}ms avg")
        logger.info("")
        logger.info("✅ Benchmark complete!")


if __name__ == "__main__":
    main()
