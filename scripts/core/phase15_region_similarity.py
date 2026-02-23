"""
Phase 15: Region Similarity Analysis

Computes pairwise similarity between regions based on character frequency patterns.

Output:
- region_similarity table with cosine, Jaccard, and Euclidean metrics
- Distinctive and common characters for each region pair
"""

import sqlite3
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.region_similarity import RegionSimilarityAnalyzer


def create_tables(conn: sqlite3.Connection):
    """Create region_similarity table."""
    cursor = conn.cursor()

    # Drop existing table
    cursor.execute("DROP TABLE IF EXISTS region_similarity")

    # Create table
    cursor.execute("""
    CREATE TABLE region_similarity (
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
    CREATE INDEX idx_region_similarity_r1
    ON region_similarity(region1)
    """)

    cursor.execute("""
    CREATE INDEX idx_region_similarity_r2
    ON region_similarity(region2)
    """)

    cursor.execute("""
    CREATE INDEX idx_region_similarity_cosine
    ON region_similarity(cosine_similarity DESC)
    """)

    conn.commit()
    print("[OK] Created region_similarity table with indexes")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Phase 15: Region Similarity Analysis")
    print("=" * 60)

    db_path = project_root / "data" / "villages.db"
    conn = sqlite3.connect(db_path)

    # Step 1: Create tables
    print("\n[Step 1] Creating tables...")
    create_tables(conn)

    # Step 2: Initialize analyzer
    print("\n[Step 2] Initializing analyzer...")
    analyzer = RegionSimilarityAnalyzer(str(db_path))

    # Step 3: Load regional data
    print("\n[Step 3] Loading regional character data...")
    region_level = 'county'
    df = analyzer.load_regional_data(
        region_level=region_level,
        top_k_global=100,
        z_score_threshold=2.0
    )
    print(f"  Loaded {len(df)} character-region records")
    print(f"  Feature characters: {len(analyzer.feature_chars)}")

    # Step 4: Build feature vectors
    print("\n[Step 4] Building feature vectors...")
    feature_matrix = analyzer.build_feature_vectors(df)
    n_regions = len(analyzer.region_names)
    print(f"  Built feature matrix: {feature_matrix.shape}")
    print(f"  Regions: {n_regions}")

    # Step 5: Compute similarities
    print("\n[Step 5] Computing pairwise similarities...")
    print("  Computing cosine similarity...")
    cosine_matrix = analyzer.compute_cosine_similarity()

    print("  Computing Jaccard similarity...")
    jaccard_matrix = analyzer.compute_jaccard_similarity(df, z_score_threshold=2.0)

    print("  Computing Euclidean distance...")
    euclidean_matrix = analyzer.compute_euclidean_distance()

    # Step 6: Generate similarity pairs
    print("\n[Step 6] Generating similarity records...")
    records = analyzer.generate_similarity_pairs(
        cosine_matrix,
        jaccard_matrix,
        euclidean_matrix,
        df,
        region_level
    )
    print(f"  Generated {len(records)} region pairs")

    # Step 7: Save to database
    print("\n[Step 7] Saving to database...")
    cursor = conn.cursor()
    created_at = time.time()

    for record in records:
        record['created_at'] = created_at
        cursor.execute("""
        INSERT INTO region_similarity (
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
        COUNT(*) as total_pairs,
        AVG(cosine_similarity) as avg_cosine,
        MIN(cosine_similarity) as min_cosine,
        MAX(cosine_similarity) as max_cosine,
        AVG(jaccard_similarity) as avg_jaccard,
        MIN(jaccard_similarity) as min_jaccard,
        MAX(jaccard_similarity) as max_jaccard
    FROM region_similarity
    """)
    stats = cursor.fetchone()

    print(f"Total region pairs: {stats[0]}")
    print(f"\nCosine Similarity:")
    print(f"  Average: {stats[1]:.4f}")
    print(f"  Min: {stats[2]:.4f}")
    print(f"  Max: {stats[3]:.4f}")
    print(f"\nJaccard Similarity:")
    print(f"  Average: {stats[4]:.4f}")
    print(f"  Min: {stats[5]:.4f}")
    print(f"  Max: {stats[6]:.4f}")

    # Top 10 most similar pairs
    print("\n[Top 10 Most Similar Pairs (Cosine)]")
    cursor.execute("""
    SELECT region1, region2, cosine_similarity, jaccard_similarity
    FROM region_similarity
    ORDER BY cosine_similarity DESC
    LIMIT 10
    """)
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {row[0]} <-> {row[1]}: cosine={row[2]:.4f}, jaccard={row[3]:.4f}")

    # Top 10 most dissimilar pairs
    print("\n[Top 10 Most Dissimilar Pairs (Cosine)]")
    cursor.execute("""
    SELECT region1, region2, cosine_similarity, jaccard_similarity
    FROM region_similarity
    ORDER BY cosine_similarity ASC
    LIMIT 10
    """)
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {row[0]} <-> {row[1]}: cosine={row[2]:.4f}, jaccard={row[3]:.4f}")

    conn.close()

    print("\n" + "=" * 60)
    print("Phase 15 Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

