"""
Phase 15: Region Similarity Analysis

Computes pairwise similarity between regions based on character frequency patterns.

Output:
- region_similarity table with cosine, Jaccard, and Euclidean metrics
- Distinctive and common characters for each region pair
"""

import sqlite3
import time
import argparse
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.region_similarity import RegionSimilarityAnalyzer


def create_tables(conn: sqlite3.Connection):
    """Create region_similarity table."""
    cursor = conn.cursor()

    # Create table if not exists (preserve existing data on re-run)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS region_similarity (
        region_level TEXT NOT NULL,
        region1 TEXT NOT NULL,
        region2 TEXT NOT NULL,
        cosine_similarity REAL,
        jaccard_similarity REAL,
        euclidean_distance REAL,
        common_high_tendency_chars TEXT,
        distinctive_chars_r1 TEXT,
        distinctive_chars_r2 TEXT,
        feature_dimension INTEGER,
        created_at REAL,
        PRIMARY KEY (region_level, region1, region2)
    )
    """)

    # Create indexes
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_region_similarity_r1
    ON region_similarity(region1)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_region_similarity_r2
    ON region_similarity(region2)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_region_similarity_cosine
    ON region_similarity(cosine_similarity DESC)
    """)

    conn.commit()
    print("[OK] Created region_similarity table with indexes")


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 15: Region Similarity Analysis")
    parser.add_argument("--run-id", default=None, help="Accepted for pipeline run tracking")
    parser.add_argument("--db-path", default=str(project_root / "data" / "villages.db"))
    parser.add_argument(
        "--region-levels",
        default="city,county",
        help="Comma-separated region levels to analyze",
    )
    parser.add_argument("--top-k-global", type=int, default=100)
    parser.add_argument("--z-score-threshold", type=float, default=2.0)
    parser.add_argument("--summary-limit", type=int, default=10)
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()
    region_levels = [level.strip() for level in args.region_levels.split(",") if level.strip()]

    print("=" * 60)
    print("Phase 15: Region Similarity Analysis")
    print("=" * 60)

    db_path = Path(args.db_path)
    conn = sqlite3.connect(db_path)

    # Step 1: Create tables
    print("\n[Step 1] Creating tables...")
    create_tables(conn)

    # Step 2: Initialize analyzer
    print("\n[Step 2] Initializing analyzer...")
    analyzer = RegionSimilarityAnalyzer(str(db_path))

    cursor = conn.cursor()
    created_at = time.time()

    for region_level in region_levels:
        # Step 3: Load regional data
        print(f"\n[Step 3] Loading {region_level}-level character data...")
        df = analyzer.load_regional_data(
            region_level=region_level,
            top_k_global=args.top_k_global,
            z_score_threshold=args.z_score_threshold
        )
        print(f"  Loaded {len(df)} character-region records")
        print(f"  Feature characters: {len(analyzer.feature_chars)}")

        # Step 4: Build feature vectors
        print(f"\n[Step 4] Building feature vectors ({region_level})...")
        feature_matrix = analyzer.build_feature_vectors(df)
        n_regions = len(analyzer.region_names)
        print(f"  Built feature matrix: {feature_matrix.shape}")
        print(f"  Regions: {n_regions}")

        # Step 5: Compute similarities
        print(f"\n[Step 5] Computing pairwise similarities ({region_level})...")
        print("  Computing cosine similarity...")
        cosine_matrix = analyzer.compute_cosine_similarity()

        print("  Computing Jaccard similarity...")
        jaccard_matrix = analyzer.compute_jaccard_similarity(
            df,
            z_score_threshold=args.z_score_threshold,
        )

        print("  Computing Euclidean distance...")
        euclidean_matrix = analyzer.compute_euclidean_distance()

        # Step 6: Generate similarity pairs
        print(f"\n[Step 6] Generating similarity records ({region_level})...")
        records = analyzer.generate_similarity_pairs(
            cosine_matrix,
            jaccard_matrix,
            euclidean_matrix,
            df,
            region_level
        )
        print(f"  Generated {len(records)} region pairs")

        # Step 7: Save to database
        print(f"\n[Step 7] Saving {region_level} records to database...")
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
                record['region_level'],
                record['region1'],
                record['region2'],
                record['cosine_similarity'],
                record['jaccard_similarity'],
                record['euclidean_distance'],
                record['common_high_tendency_chars'],
                record['distinctive_chars_r1'],
                record['distinctive_chars_r2'],
                record['feature_dimension'],
                record['created_at']
            ))

        conn.commit()
        print(f"  Saved {len(records)} records")

    # Step 8: Generate summary statistics
    print("\n[Step 8] Summary Statistics")
    print("=" * 60)

    cursor.execute("""
    SELECT
        region_level,
        COUNT(*) as total_pairs,
        AVG(cosine_similarity) as avg_cosine,
        MIN(cosine_similarity) as min_cosine,
        MAX(cosine_similarity) as max_cosine,
        AVG(jaccard_similarity) as avg_jaccard,
        MIN(jaccard_similarity) as min_jaccard,
        MAX(jaccard_similarity) as max_jaccard
    FROM region_similarity
    GROUP BY region_level
    ORDER BY region_level
    """)
    for row in cursor.fetchall():
        print(f"\n[{row[0]}] {row[1]} pairs")
        print(f"  Cosine:  avg={row[2]:.4f}  min={row[3]:.4f}  max={row[4]:.4f}")
        print(f"  Jaccard: avg={row[5]:.4f}  min={row[6]:.4f}  max={row[7]:.4f}")

    # Top 10 most similar pairs per level
    for region_level in region_levels:
        print(f"\n[Top {args.summary_limit} Most Similar Pairs ({region_level})]")
        cursor.execute("""
        SELECT region1, region2, cosine_similarity, jaccard_similarity
        FROM region_similarity
        WHERE region_level = ?
        ORDER BY cosine_similarity DESC
        LIMIT ?
        """, (region_level, args.summary_limit))
        for i, row in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. {row[0]} <-> {row[1]}: cosine={row[2]:.4f}, jaccard={row[3]:.4f}")

        print(f"\n[Top {args.summary_limit} Most Dissimilar Pairs ({region_level})]")
        cursor.execute("""
        SELECT region1, region2, cosine_similarity, jaccard_similarity
        FROM region_similarity
        WHERE region_level = ?
        ORDER BY cosine_similarity ASC
        LIMIT ?
        """, (region_level, args.summary_limit))
        for i, row in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. {row[0]} <-> {row[1]}: cosine={row[2]:.4f}, jaccard={row[3]:.4f}")

    conn.close()

    print("\n" + "=" * 60)
    print("Phase 15 Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
