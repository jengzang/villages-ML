"""Region similarity analysis pipeline.

Computes pairwise similarity between regions based on character frequency patterns.
Three metrics are calculated:
- Cosine similarity: angle between region character-frequency vectors
- Jaccard similarity: overlap of high-tendency character sets
- Euclidean distance: absolute distance in feature space

Each region pair also gets:
- Common high-tendency characters (shared between both regions)
- Distinctive characters unique to each region
"""

import logging
import sqlite3
import time
from typing import Any

from src.analysis.region_similarity import RegionSimilarityAnalyzer
from src.schema import REGION_LEVELS

logger = logging.getLogger(__name__)


def run_region_similarity_pipeline(
    db_path: str,
    region_levels: list[str] | None = None,
    top_k_global: int = 100,
    z_score_threshold: float = 2.0,
) -> dict[str, Any]:
    """Compute pairwise region similarity from character frequency data.

    Pipeline:
    1. For each region level, load the top-K global characters as features
    2. Build a region × character frequency matrix
    3. Compute cosine, Jaccard, and Euclidean pairwise similarity
    4. Generate region pair records with distinctive character identification
    5. Persist to region_similarity table

    Args:
        db_path: Path to SQLite database.
        region_levels: Region levels to analyse (default: REGION_LEVELS[:2]).
        top_k_global: Number of most frequent global characters to use as features.
        z_score_threshold: Z-score cutoff for "high-tendency" character detection.
    """
    if region_levels is None:
        region_levels = REGION_LEVELS[:2]

    logger.info("=" * 60)
    logger.info("Region Similarity Analysis Pipeline")
    logger.info(f"  Levels: {region_levels}")
    logger.info(f"  Top-K features: {top_k_global}")
    logger.info(f"  Z-score threshold: {z_score_threshold}")
    logger.info("=" * 60)

    start_time = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create result table and indexes if not present
    _create_tables(conn)
    logger.info("Tables ready")

    analyzer = RegionSimilarityAnalyzer(db_path)
    created_at = time.time()
    total_pairs = 0

    for level in region_levels:
        logger.info(f"Processing {level} level...")

        # Step 1: Load regional frequency data.
        # Each region gets a vector of length top_k_global (one value per feature character).
        logger.info(f"  Loading regional data (top {top_k_global} chars)...")
        df = analyzer.load_regional_data(
            region_level=level, top_k_global=top_k_global,
            z_score_threshold=z_score_threshold,
        )
        n_regions = df['region_name'].nunique()
        logger.info(f"  {n_regions} regions, {len(analyzer.feature_chars)} feature characters")

        # Step 2: Build feature matrix (regions × characters).
        feature_matrix = analyzer.build_feature_vectors(df)
        logger.info(f"  Feature matrix: {feature_matrix.shape[0]} regions × {feature_matrix.shape[1]} chars")

        if feature_matrix.shape[0] < 2:
            logger.warning(f"  Skipping {level}: need at least 2 regions, got {feature_matrix.shape[0]}")
            continue

        # Step 3: Compute three similarity/distance metrics.
        # Cosine: measures orientation (0 = orthogonal, 1 = identical direction).
        # Jaccard: set overlap of high-tendency characters.
        # Euclidean: absolute distance — lower = more similar.
        logger.info("  Computing cosine similarity...")
        cosine_matrix = analyzer.compute_cosine_similarity()

        logger.info("  Computing Jaccard similarity...")
        jaccard_matrix = analyzer.compute_jaccard_similarity(df, z_score_threshold=z_score_threshold)

        logger.info("  Computing Euclidean distance...")
        euclidean_matrix = analyzer.compute_euclidean_distance()

        # Step 4: Generate pair records.
        # Each record = one region pair with all three metrics + distinctive chars.
        records = analyzer.generate_similarity_pairs(
            cosine_matrix, jaccard_matrix, euclidean_matrix, df, level,
        )
        logger.info(f"  Generated {len(records):,} region pairs")

        # Step 5: Write to database.
        for record in records:
            record['created_at'] = created_at
            cursor.execute("""
                INSERT OR REPLACE INTO region_similarity (
                    region_level, region1, region2,
                    cosine_similarity, jaccard_similarity, euclidean_distance,
                    common_high_tendency_chars, distinctive_chars_r1, distinctive_chars_r2,
                    feature_dimension, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['region_level'], record['region1'], record['region2'],
                record['cosine_similarity'], record['jaccard_similarity'], record['euclidean_distance'],
                record['common_high_tendency_chars'], record['distinctive_chars_r1'],
                record['distinctive_chars_r2'], record['feature_dimension'], record['created_at'],
            ))
        conn.commit()
        total_pairs += len(records)

        # Per-level summary statistics
        level_pairs = [r for r in records]
        if level_pairs:
            avg_cos = sum(r['cosine_similarity'] for r in level_pairs) / len(level_pairs)
            logger.info(f"  Avg cosine similarity: {avg_cos:.4f}")

    # Global summary across all levels
    logger.info("---")
    cursor.execute("""
        SELECT region_level, COUNT(*) as total_pairs,
               AVG(cosine_similarity) as avg_cosine, AVG(jaccard_similarity) as avg_jaccard
        FROM region_similarity
        GROUP BY region_level ORDER BY region_level
    """)
    for row in cursor.fetchall():
        logger.info(f"  [{row[0]}] {row[1]} pairs, avg_cosine={row[2]:.4f}, avg_jaccard={row[3]:.4f}")

    conn.close()

    elapsed = time.time() - start_time
    logger.info(f"Region similarity pipeline completed in {elapsed:.1f}s")
    logger.info(f"Total pairs: {total_pairs:,}")

    return {
        'region_levels': region_levels,
        'total_pairs': total_pairs,
        'runtime_seconds': round(elapsed, 2),
    }


def _create_tables(conn: sqlite3.Connection) -> None:
    """Create region_similarity table and supporting indexes."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS region_similarity (
            region_level TEXT NOT NULL, region1 TEXT NOT NULL, region2 TEXT NOT NULL,
            cosine_similarity REAL, jaccard_similarity REAL, euclidean_distance REAL,
            common_high_tendency_chars TEXT, distinctive_chars_r1 TEXT, distinctive_chars_r2 TEXT,
            feature_dimension INTEGER, created_at REAL,
            PRIMARY KEY (region_level, region1, region2)
        )
    """)
    # Indexes for fast lookup by region name and similarity ordering
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_region_similarity_r1 ON region_similarity(region1)",
        "CREATE INDEX IF NOT EXISTS idx_region_similarity_r2 ON region_similarity(region2)",
        "CREATE INDEX IF NOT EXISTS idx_region_similarity_cosine ON region_similarity(cosine_similarity DESC)",
    ]:
        cursor.execute(idx_sql)
    conn.commit()
    logger.info("  region_similarity table + 3 indexes created")
