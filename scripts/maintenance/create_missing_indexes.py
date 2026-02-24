"""
Create missing database indexes based on API query analysis.

This script creates 47 indexes across 30 tables, prioritized by:
- CRITICAL (25): Heavy query load, large tables
- MEDIUM (15): Improves query performance
- LOW (7): Nice to have

Usage:
    python scripts/maintenance/create_missing_indexes.py
    python scripts/maintenance/create_missing_indexes.py --priority critical
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Tuple


def create_indexes_by_priority(db_path: str, priority: str = "all"):
    """
    Create missing indexes based on API query analysis.

    Args:
        db_path: Path to villages.db
        priority: "critical", "medium", "low", or "all"
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Priority 1: CRITICAL (25 indexes) - Heavy query load, large tables
    critical_indexes = [
        # Character analysis (no run_id after optimization)
        "CREATE INDEX IF NOT EXISTS idx_char_freq_global_freq ON char_frequency_global(frequency DESC)",
        "CREATE INDEX IF NOT EXISTS idx_char_regional_composite ON char_regional_analysis(region_level, region_name, rank_within_region)",
        "CREATE INDEX IF NOT EXISTS idx_char_regional_zscore ON char_regional_analysis(region_level, region_name, z_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_char_regional_char ON char_regional_analysis(char, region_level, z_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_char_embeddings_lookup ON char_embeddings(run_id, char)",
        "CREATE INDEX IF NOT EXISTS idx_char_similarity_lookup ON char_similarity(run_id, char1, cosine_similarity DESC)",
        "CREATE INDEX IF NOT EXISTS idx_tendency_sig_char ON tendency_significance(run_id, char, region_level)",
        "CREATE INDEX IF NOT EXISTS idx_tendency_sig_region ON tendency_significance(run_id, region_name, region_level, is_significant)",

        # Semantic analysis (semantic_labels table doesn't exist in optimized DB)
        "CREATE INDEX IF NOT EXISTS idx_semantic_indices_lookup ON semantic_indices(region_level, run_id, region_name, category)",

        # Clustering
        "CREATE INDEX IF NOT EXISTS idx_cluster_assignments_lookup ON cluster_assignments(run_id, algorithm, region_level, cluster_id)",
        "CREATE INDEX IF NOT EXISTS idx_cluster_assignments_region ON cluster_assignments(run_id, region_name, algorithm, region_level)",
        "CREATE INDEX IF NOT EXISTS idx_cluster_profiles_lookup ON cluster_profiles(run_id, algorithm, cluster_id)",
        "CREATE INDEX IF NOT EXISTS idx_clustering_metrics_lookup ON clustering_metrics(run_id, algorithm, k)",

        # Spatial analysis
        "CREATE INDEX IF NOT EXISTS idx_spatial_hotspots_lookup ON spatial_hotspots(run_id, density_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_spatial_hotspots_id ON spatial_hotspots(run_id, hotspot_id)",
        "CREATE INDEX IF NOT EXISTS idx_spatial_clusters_lookup ON spatial_clusters(run_id, cluster_id)",
        "CREATE INDEX IF NOT EXISTS idx_spatial_integration_char ON spatial_tendency_integration(run_id, character, spatial_coherence)",
        "CREATE INDEX IF NOT EXISTS idx_spatial_integration_cluster ON spatial_tendency_integration(run_id, cluster_id, cluster_size DESC)",

        # N-grams (no run_id after optimization)
        "CREATE INDEX IF NOT EXISTS idx_ngram_frequency_lookup ON ngram_frequency(n, frequency DESC)",
        "CREATE INDEX IF NOT EXISTS idx_regional_ngram_lookup ON regional_ngram_frequency(level, region, n, frequency DESC)",

        # Village-level (no run_id after optimization)
        "CREATE INDEX IF NOT EXISTS idx_village_features_lookup ON village_features(village_id)",
        "CREATE INDEX IF NOT EXISTS idx_village_spatial_lookup ON village_spatial_features(village_id)",

        # Main table
        'CREATE INDEX IF NOT EXISTS idx_main_composite ON "广东省自然村"("自然村", "市级", "区县级")',
    ]

    # Priority 2: MEDIUM (15 indexes)
    medium_indexes = [
        # N-gram analysis (use "level" instead of "region_level")
        "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_lookup ON ngram_tendency(level, ngram, lift DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ngram_significance_lookup ON ngram_significance(level, ngram, is_significant)",

        # Village data
        "CREATE INDEX IF NOT EXISTS idx_village_ngrams_id ON village_ngrams(village_id)",
        "CREATE INDEX IF NOT EXISTS idx_village_semantic_id ON village_semantic_structure(village_id)",

        # Main table regional filters
        'CREATE INDEX IF NOT EXISTS idx_main_city ON "广东省自然村"("市级")',
        'CREATE INDEX IF NOT EXISTS idx_main_county ON "广东省自然村"("区县级")',
        'CREATE INDEX IF NOT EXISTS idx_main_township ON "广东省自然村"("乡镇级")',

        # Region similarity
        "CREATE INDEX IF NOT EXISTS idx_region_sim_r1 ON region_similarity(region1, cosine_similarity DESC)",
        "CREATE INDEX IF NOT EXISTS idx_region_sim_r2 ON region_similarity(region2, cosine_similarity DESC)",
        "CREATE INDEX IF NOT EXISTS idx_region_sim_pair ON region_similarity(region1, region2)",

        # Semantic network centrality
        "CREATE INDEX IF NOT EXISTS idx_semantic_centrality_runid ON semantic_network_centrality(run_id, pagerank DESC)",
        "CREATE INDEX IF NOT EXISTS idx_semantic_centrality_category ON semantic_network_centrality(run_id, category)",
        "CREATE INDEX IF NOT EXISTS idx_semantic_centrality_community ON semantic_network_centrality(run_id, community_id)",
        "CREATE INDEX IF NOT EXISTS idx_semantic_stats_runid ON semantic_network_stats(run_id)",
        "CREATE INDEX IF NOT EXISTS idx_semantic_stats_created ON semantic_network_stats(created_at DESC)",
    ]

    # Priority 3: LOW (7 indexes)
    low_indexes = [
        # Semantic composition
        "CREATE INDEX IF NOT EXISTS idx_semantic_bigrams_freq ON semantic_bigrams(frequency DESC)",
        "CREATE INDEX IF NOT EXISTS idx_semantic_pmi_lookup ON semantic_pmi(category1, category2, pmi DESC)",
        "CREATE INDEX IF NOT EXISTS idx_semantic_patterns_type ON semantic_composition_patterns(pattern_type, frequency DESC)",

        # Pattern analysis (no run_id after optimization)
        "CREATE INDEX IF NOT EXISTS idx_structural_patterns_lookup ON structural_patterns(pattern_type, frequency DESC)",
        "CREATE INDEX IF NOT EXISTS idx_pattern_freq_global_type ON pattern_frequency_global(pattern_type, frequency DESC)",
        "CREATE INDEX IF NOT EXISTS idx_pattern_regional_lookup ON pattern_regional_analysis(region_level, region_name, pattern_type)",
        "CREATE INDEX IF NOT EXISTS idx_pattern_tendency_lookup ON pattern_regional_analysis(region_level, pattern, lift DESC)",
    ]

    # Select indexes based on priority
    if priority == "critical":
        indexes_to_create = critical_indexes
    elif priority == "medium":
        indexes_to_create = medium_indexes
    elif priority == "low":
        indexes_to_create = low_indexes
    else:  # "all"
        indexes_to_create = critical_indexes + medium_indexes + low_indexes

    # Create indexes with progress tracking
    print(f"\nCreating {len(indexes_to_create)} indexes (priority: {priority})...")
    print("=" * 80)

    created_count = 0
    skipped_count = 0
    error_count = 0
    total_time = 0

    for idx_sql in indexes_to_create:
        # Extract table name for display
        try:
            table_name = idx_sql.split(" ON ")[1].split("(")[0].strip().strip('"')
        except:
            table_name = "unknown"

        try:
            start = time.time()
            cursor.execute(idx_sql)
            elapsed = time.time() - start
            total_time += elapsed
            created_count += 1
            print(f"  [OK] [{elapsed:5.2f}s] {table_name}")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                skipped_count += 1
                print(f"  [SKIP] {table_name} (already exists)")
            elif "no such table" in str(e):
                error_count += 1
                print(f"  [ERROR] {table_name}: table does not exist")
            else:
                error_count += 1
                print(f"  [ERROR] {table_name}: {e}")

    conn.commit()
    conn.close()

    # Summary
    print("=" * 80)
    print(f"\n[SUCCESS] Index creation complete!")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Errors: {error_count}")
    print(f"   Total time: {total_time:.2f}s")

    if error_count > 0:
        print(f"\n[WARNING] {error_count} indexes failed to create (likely missing tables)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create missing database indexes")
    parser.add_argument(
        "--priority",
        choices=["critical", "medium", "low", "all"],
        default="all",
        help="Index priority level to create"
    )
    args = parser.parse_args()

    db_path = Path(__file__).parent.parent.parent / "data" / "villages.db"

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        exit(1)

    print(f"Database: {db_path}")
    create_indexes_by_priority(str(db_path), args.priority)
