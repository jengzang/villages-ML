#!/usr/bin/env python3
"""
Phase 12: N-gram Structure Analysis

This script performs comprehensive n-gram analysis on village names:
1. Extract bigrams and trigrams (全局和區域)
2. Calculate frequency statistics
3. Compute tendency scores (lift, z-score)
4. Statistical significance testing
5. Clean up non-significant data (NEW: 2026-02-25)
6. Detect structural patterns
7. Auto-update active_run_ids (NEW: 2026-02-25)

Approach: Offline-heavy, maximum accuracy, full dataset

IMPORTANT (2026-02-25):
- Only statistically significant n-grams (p < 0.05) are stored in the database
- Non-significant n-grams are filtered out during generation to optimize storage
- This reduces database size by ~40% while maintaining analytical quality
- Automatically updates active_run_ids table after completion
"""

import sqlite3
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ngram_analysis import NgramExtractor, NgramAnalyzer, StructuralPatternDetector
from src.ngram_schema import create_ngram_tables

# Import run_id manager for auto-update (NEW: 2026-02-25)
sys.path.insert(0, str(project_root / 'scripts'))
from utils.update_run_id import update_active_run_id


def step1_create_tables(db_path: str):
    """Step 1: Create database tables."""
    print("\n" + "="*60)
    print("Step 1: Creating N-gram Analysis Tables")
    print("="*60)

    create_ngram_tables(db_path)
    print("[OK] Tables created successfully")


def step2_extract_global_ngrams(db_path: str):
    """Step 2: Extract global n-gram frequencies."""
    print("\n" + "="*60)
    print("Step 2: Extracting Global N-grams")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with NgramExtractor(db_path) as extractor:
        # Extract bigrams
        print("\nExtracting bigrams...")
        bigram_data = extractor.extract_all_ngrams(n=2)

        # Extract trigrams
        print("Extracting trigrams...")
        trigram_data = extractor.extract_all_ngrams(n=3)

        # Extract 4-grams
        print("Extracting 4-grams...")
        fourgram_data = extractor.extract_all_ngrams(n=4)

    # Store bigrams
    print("\nStoring bigram frequencies...")
    for position, counter in bigram_data.items():
        total = sum(counter.values())
        for ngram, freq in counter.items():
            percentage = (freq / total * 100) if total > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_frequency
                (ngram, n, position, frequency, total_count, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ngram, 2, position, freq, total, percentage))

    # Store trigrams
    print("Storing trigram frequencies...")
    for position, counter in trigram_data.items():
        total = sum(counter.values())
        for ngram, freq in counter.items():
            percentage = (freq / total * 100) if total > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_frequency
                (ngram, n, position, frequency, total_count, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ngram, 3, position, freq, total, percentage))

    # Store 4-grams
    print("Storing 4-gram frequencies...")
    for position, counter in fourgram_data.items():
        total = sum(counter.values())
        for ngram, freq in counter.items():
            percentage = (freq / total * 100) if total > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_frequency
                (ngram, n, position, frequency, total_count, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ngram, 4, position, freq, total, percentage))

    conn.commit()

    # Print statistics
    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_frequency WHERE n = 2")
    bigram_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_frequency WHERE n = 3")
    trigram_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT ngram) FROM ngram_frequency WHERE n = 4")
    fourgram_count = cursor.fetchone()[0]

    print(f"\n[OK] Extracted {bigram_count:,} unique bigrams")
    print(f"[OK] Extracted {trigram_count:,} unique trigrams")
    print(f"[OK] Extracted {fourgram_count:,} unique 4-grams")

    conn.close()


def step3_extract_regional_ngrams(db_path: str):
    """Step 3: Extract regional n-gram frequencies with hierarchical grouping."""
    print("\n" + "="*60)
    print("Step 3: Extracting Regional N-grams (Hierarchical)")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Map Chinese level names to English for database
    level_map = {
        '市级': 'city',
        '县区级': 'county',
        '乡镇': 'township'
    }

    levels = ['市级', '县区级', '乡镇']

    with NgramExtractor(db_path) as extractor:
        for level in levels:
            print(f"\nProcessing level: {level}")
            level_en = level_map[level]

            # Bigrams
            print(f"  Extracting bigrams for {level}...")
            bigram_data = extractor.extract_regional_ngrams(n=2, level=level)

            for hierarchical_key, position_data in bigram_data.items():
                # Extract hierarchical components
                city, county, township = hierarchical_key

                # Get region name for display (the actual region at this level)
                if level == '市级':
                    region_name = city
                elif level == '县区级':
                    region_name = county
                else:  # 乡镇
                    region_name = township

                for position, counter in position_data.items():
                    total = sum(counter.values())
                    for ngram, freq in counter.items():
                        percentage = (freq / total * 100) if total > 0 else 0
                        cursor.execute("""
                            INSERT OR REPLACE INTO regional_ngram_frequency
                            (level, city, county, township, region, ngram, n, position, frequency, total_count, percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (level_en, city, county, township, region_name, ngram, 2, position, freq, total, percentage))

            # Trigrams
            print(f"  Extracting trigrams for {level}...")
            trigram_data = extractor.extract_regional_ngrams(n=3, level=level)

            for hierarchical_key, position_data in trigram_data.items():
                # Extract hierarchical components
                city, county, township = hierarchical_key

                # Get region name for display
                if level == '市级':
                    region_name = city
                elif level == '县区级':
                    region_name = county
                else:  # 乡镇
                    region_name = township

                for position, counter in position_data.items():
                    total = sum(counter.values())
                    for ngram, freq in counter.items():
                        percentage = (freq / total * 100) if total > 0 else 0
                        cursor.execute("""
                            INSERT OR REPLACE INTO regional_ngram_frequency
                            (level, city, county, township, region, ngram, n, position, frequency, total_count, percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (level_en, city, county, township, region_name, ngram, 3, position, freq, total, percentage))

            conn.commit()
            print(f"  [OK] Completed {level}")

    print("\n[OK] Regional n-gram extraction complete (with hierarchical separation)")
    conn.close()


def step3_5_calculate_regional_totals_raw(db_path: str):
    """Step 3.5: Calculate and store regional total raw counts (before filtering)."""
    print("\n" + "="*60)
    print("Step 3.5: Calculating Regional Total Raw Counts")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create temporary table to store raw totals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_regional_totals_raw (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            total_raw INTEGER NOT NULL,
            PRIMARY KEY (level, city, county, township, n, position)
        )
    """)

    # Clear old data
    cursor.execute("DELETE FROM temp_regional_totals_raw")

    # Calculate raw totals for each region-position combination
    cursor.execute("""
        INSERT INTO temp_regional_totals_raw
        SELECT level, city, county, township, n, position, COUNT(*) as total_raw
        FROM regional_ngram_frequency
        GROUP BY level, city, county, township, n, position
    """)

    rows_inserted = cursor.rowcount
    print(f"  Calculated raw totals for {rows_inserted:,} region-position combinations")

    conn.commit()
    conn.close()

    print("[OK] Regional total raw counts calculated")


def step4_calculate_tendency(db_path: str):
    """Step 4: Calculate tendency scores with hierarchical grouping."""
    print("\n" + "="*60)
    print("Step 4: Calculating Tendency Scores (Hierarchical)")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    # Map Chinese level names to English
    level_map = {
        '市级': 'city',
        '县区级': 'county',
        '乡镇': 'township'
    }

    levels = ['市级', '县区级', '乡镇']

    for level in levels:
        print(f"\nProcessing level: {level}")
        level_en = level_map[level]

        # Get all regional n-grams with hierarchical keys
        cursor.execute("""
            SELECT DISTINCT level, city, county, township, region, ngram, n, position
            FROM regional_ngram_frequency
            WHERE level = ?
        """, (level_en,))

        rows = cursor.fetchall()
        total_rows = len(rows)

        for idx, (level_db, city, county, township, region, ngram, n, position) in enumerate(rows, 1):
            if idx % 1000 == 0:
                print(f"  Progress: {idx}/{total_rows}")

            # Get regional counts
            cursor.execute("""
                SELECT frequency, total_count
                FROM regional_ngram_frequency
                WHERE level = ? AND city IS ? AND county IS ? AND township IS ?
                  AND ngram = ? AND n = ? AND position = ?
            """, (level_en, city, county, township, ngram, n, position))

            regional_result = cursor.fetchone()
            if not regional_result:
                continue

            regional_count, regional_total = regional_result

            # Get regional_total_raw from temp table
            cursor.execute("""
                SELECT total_raw
                FROM temp_regional_totals_raw
                WHERE level = ? AND city IS ? AND county IS ? AND township IS ?
                  AND n = ? AND position = ?
            """, (level_en, city, county, township, n, position))

            raw_result = cursor.fetchone()
            regional_total_raw = raw_result[0] if raw_result else regional_total

            # Get global counts
            cursor.execute("""
                SELECT frequency, total_count
                FROM ngram_frequency
                WHERE ngram = ? AND n = ? AND position = ?
            """, (ngram, n, position))

            global_result = cursor.fetchone()
            if not global_result:
                continue

            global_count, global_total = global_result

            # Calculate tendency
            tendency = analyzer.calculate_tendency(
                regional_count, regional_total,
                global_count, global_total
            )

            # Store results with hierarchical columns (including regional_total_raw)
            cursor.execute("""
                INSERT OR REPLACE INTO ngram_tendency
                (level, city, county, township, region, ngram, n, position, lift, log_odds, z_score,
                 regional_count, regional_total, regional_total_raw, global_count, global_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                level_en, city, county, township, region, ngram, n, position,
                tendency['lift'], tendency['log_odds'], tendency['z_score'],
                regional_count, regional_total, regional_total_raw, global_count, global_total
            ))

        conn.commit()
        print(f"  [OK] Completed {level}")

    analyzer.__exit__(None, None, None)
    conn.close()
    print("\n[OK] Tendency calculation complete (with hierarchical separation)")


def step5_calculate_significance(db_path: str):
    """Step 5: Calculate statistical significance with hierarchical grouping.

    IMPORTANT: Only stores significant n-grams (p < 0.05) to optimize database size.
    Non-significant n-grams are not stored in ngram_significance table.
    """
    print("\n" + "="*60)
    print("Step 5: Calculating Statistical Significance (Hierarchical)")
    print("="*60)
    print("NOTE: Only storing significant n-grams (p < 0.05)")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    analyzer = NgramAnalyzer(db_path)
    analyzer.__enter__()

    # Map Chinese level names to English
    level_map = {
        '市级': 'city',
        '县区级': 'county',
        '乡镇': 'township'
    }

    levels = ['市级', '县区级', '乡镇']
    alpha = 0.05  # Significance level

    # Track statistics
    total_tested = 0
    total_significant = 0

    for level in levels:
        print(f"\nProcessing level: {level}")
        level_en = level_map[level]

        # Get all tendency records with hierarchical columns
        cursor.execute("""
            SELECT level, city, county, township, region, ngram, n, position,
                   regional_count, regional_total, global_count, global_total
            FROM ngram_tendency
            WHERE level = ?
        """, (level_en,))

        rows = cursor.fetchall()
        total_rows = len(rows)
        significant_count = 0

        for idx, row in enumerate(rows, 1):
            if idx % 1000 == 0:
                print(f"  Progress: {idx}/{total_rows} ({significant_count} significant)")

            level_db, city, county, township, region, ngram, n, position, regional_count, regional_total, global_count, global_total = row

            # Calculate significance
            sig = analyzer.calculate_significance(
                regional_count, regional_total,
                global_count, global_total
            )

            is_significant = sig['p_value'] < alpha

            # ONLY store significant results (p < 0.05)
            if is_significant:
                # Get total_before_filter from temp table
                cursor.execute("""
                    SELECT total_raw
                    FROM temp_regional_totals_raw
                    WHERE level = ? AND city IS ? AND county IS ? AND township IS ?
                      AND n = ? AND position = ?
                """, (level_db, city, county, township, n, position))

                raw_result = cursor.fetchone()
                total_before_filter = raw_result[0] if raw_result else regional_total

                cursor.execute("""
                    INSERT OR REPLACE INTO ngram_significance
                    (level, city, county, township, region, ngram, n, position, chi2, p_value, cramers_v, is_significant, total_before_filter)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    level_db, city, county, township, region, ngram, n, position,
                    sig['chi2'], sig['p_value'], sig['cramers_v'], 1, total_before_filter
                ))
                significant_count += 1

        total_tested += total_rows
        total_significant += significant_count

        conn.commit()
        print(f"  [OK] Completed {level}: {significant_count}/{total_rows} significant ({significant_count/total_rows*100:.1f}%)")

    analyzer.__exit__(None, None, None)
    conn.close()

    print(f"\n[OK] Significance testing complete")
    print(f"    Total tested: {total_tested:,}")
    print(f"    Total significant: {total_significant:,} ({total_significant/total_tested*100:.1f}%)")
    print(f"    Filtered out: {total_tested - total_significant:,} non-significant n-grams")


def step6_cleanup_insignificant_data(db_path: str):
    """Step 6: Clean up non-significant n-grams from tendency and frequency tables.

    This step removes non-significant n-grams from:
    - ngram_tendency
    - regional_ngram_frequency

    Only n-grams that exist in ngram_significance (p < 0.05) are retained.
    """
    print("\n" + "="*60)
    print("Step 6: Cleaning Up Non-Significant N-grams")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count before cleanup
    cursor.execute("SELECT COUNT(*) FROM ngram_tendency")
    tendency_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regional_ngram_frequency")
    frequency_before = cursor.fetchone()[0]

    print(f"\nBefore cleanup:")
    print(f"  ngram_tendency: {tendency_before:,} rows")
    print(f"  regional_ngram_frequency: {frequency_before:,} rows")

    # Delete from ngram_tendency
    print("\nDeleting non-significant n-grams from ngram_tendency...")
    cursor.execute("""
        DELETE FROM ngram_tendency
        WHERE NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = ngram_tendency.ngram
            AND ngram_significance.level = ngram_tendency.level
            AND ngram_significance.city = ngram_tendency.city
            AND ngram_significance.county = ngram_tendency.county
            AND ngram_significance.township = ngram_tendency.township
        )
    """)
    tendency_deleted = cursor.rowcount
    print(f"  Deleted {tendency_deleted:,} rows")

    # Delete from regional_ngram_frequency
    print("\nDeleting non-significant n-grams from regional_ngram_frequency...")
    cursor.execute("""
        DELETE FROM regional_ngram_frequency
        WHERE NOT EXISTS (
            SELECT 1 FROM ngram_significance
            WHERE ngram_significance.ngram = regional_ngram_frequency.ngram
            AND ngram_significance.level = regional_ngram_frequency.level
            AND ngram_significance.city = regional_ngram_frequency.city
            AND ngram_significance.county = regional_ngram_frequency.county
            AND ngram_significance.township = regional_ngram_frequency.township
        )
    """)
    frequency_deleted = cursor.rowcount
    print(f"  Deleted {frequency_deleted:,} rows")

    conn.commit()

    # Count after cleanup
    cursor.execute("SELECT COUNT(*) FROM ngram_tendency")
    tendency_after = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regional_ngram_frequency")
    frequency_after = cursor.fetchone()[0]

    print(f"\nAfter cleanup:")
    print(f"  ngram_tendency: {tendency_after:,} rows (retained {tendency_after/tendency_before*100:.1f}%)")
    print(f"  regional_ngram_frequency: {frequency_after:,} rows (retained {frequency_after/frequency_before*100:.1f}%)")

    print(f"\nTotal space saved: {tendency_deleted + frequency_deleted:,} rows deleted")

    conn.close()
    print("\n[OK] Cleanup complete - only significant n-grams retained")


def step7_detect_patterns(db_path: str):
    """Step 7: Detect structural patterns."""
    print("\n" + "="*60)
    print("Step 7: Detecting Structural Patterns")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    detector = StructuralPatternDetector(db_path)

    # Get bigrams, trigrams, and 4-grams
    from collections import Counter

    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 2 AND position = 'all'
        ORDER BY frequency DESC
    """)
    bigrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})

    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 3 AND position = 'all'
        ORDER BY frequency DESC
    """)
    trigrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})

    cursor.execute("""
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE n = 4 AND position = 'all'
        ORDER BY frequency DESC
    """)
    fourgrams = Counter({ngram: freq for ngram, freq in cursor.fetchall()})

    # Detect bigram templates
    print("\nDetecting bigram templates...")
    bigram_templates = detector.detect_templates(bigrams, min_freq=100)

    for template in bigram_templates:
        cursor.execute("""
            INSERT OR REPLACE INTO structural_patterns
            (pattern, pattern_type, n, position, frequency, example, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template['pattern'],
            template['type'],
            2,
            'all',
            template['frequency'],
            template['example'],
            f"{template['type']} pattern"
        ))

    print(f"  [OK] Found {len(bigram_templates)} bigram templates")

    # Detect trigram templates
    print("Detecting trigram templates...")
    trigram_templates = detector.detect_templates(trigrams, min_freq=50)

    for template in trigram_templates:
        cursor.execute("""
            INSERT OR REPLACE INTO structural_patterns
            (pattern, pattern_type, n, position, frequency, example, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template['pattern'],
            template['type'],
            3,
            'all',
            template['frequency'],
            template['example'],
            f"{template['type']} pattern"
        ))

    print(f"  [OK] Found {len(trigram_templates)} trigram templates")

    # Detect 4-gram templates
    print("Detecting 4-gram templates...")
    fourgram_templates = detector.detect_templates(fourgrams, min_freq=30)

    for template in fourgram_templates:
        cursor.execute("""
            INSERT OR REPLACE INTO structural_patterns
            (pattern, pattern_type, n, position, frequency, example, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template['pattern'],
            template['type'],
            4,
            'all',
            template['frequency'],
            template['example'],
            f"{template['type']} pattern"
        ))

    print(f"  [OK] Found {len(fourgram_templates)} 4-gram templates")

    conn.commit()
    conn.close()
    print("\n[OK] Pattern detection complete")


def step8_create_optimization_indexes(db_path: str):
    """Step 8: Create optimization indexes and regional centroids table."""
    print("\n" + "="*60)
    print("Step 8: Creating Optimization Indexes")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Part 1: Create indexes on village preprocessing table
    print("\n[1/3] Creating indexes on village preprocessing table...")
    village_indexes = [
        ('idx_village_township', '广东省自然村_预处理', '乡镇级'),
        ('idx_village_county', '广东省自然村_预处理', '区县级'),
        ('idx_village_city', '广东省自然村_预处理', '市级')
    ]

    for idx_name, table, column in village_indexes:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})')
            print(f"  [OK] {idx_name}")
        except Exception as e:
            print(f"  [SKIP] {idx_name}: {e}")

    # Part 2: Create regional centroids table
    print("\n[2/3] Creating regional centroids table...")

    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS regional_centroids (
        region_level TEXT NOT NULL,
        region_name TEXT NOT NULL,
        centroid_lon REAL NOT NULL,
        centroid_lat REAL NOT NULL,
        village_count INTEGER NOT NULL,
        PRIMARY KEY (region_level, region_name)
    )
    ''')
    print("  [OK] Table created")

    # Create index
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_regional_centroids_lookup
    ON regional_centroids(region_level, region_name)
    ''')
    print("  [OK] Index created")

    # Populate data
    print("  Populating data...")
    cursor.execute('''
    INSERT OR REPLACE INTO regional_centroids (region_level, region_name, centroid_lon, centroid_lat, village_count)
    SELECT
        'township' as region_level,
        乡镇级 as region_name,
        AVG(CAST(longitude AS REAL)) as centroid_lon,
        AVG(CAST(latitude AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM 广东省自然村_预处理
    WHERE 乡镇级 IS NOT NULL AND longitude IS NOT NULL AND latitude IS NOT NULL
    GROUP BY 乡镇级

    UNION ALL

    SELECT
        'county' as region_level,
        区县级 as region_name,
        AVG(CAST(longitude AS REAL)) as centroid_lon,
        AVG(CAST(latitude AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM 广东省自然村_预处理
    WHERE 区县级 IS NOT NULL AND longitude IS NOT NULL AND latitude IS NOT NULL
    GROUP BY 区县级

    UNION ALL

    SELECT
        'city' as region_level,
        市级 as region_name,
        AVG(CAST(longitude AS REAL)) as centroid_lon,
        AVG(CAST(latitude AS REAL)) as centroid_lat,
        COUNT(*) as village_count
    FROM 广东省自然村_预处理
    WHERE 市级 IS NOT NULL AND longitude IS NOT NULL AND latitude IS NOT NULL
    GROUP BY 市级
    ''')

    # Verify data
    cursor.execute('SELECT region_level, COUNT(*) FROM regional_centroids GROUP BY region_level')
    results = cursor.fetchall()
    total = sum(count for _, count in results)
    print(f"  [OK] {total} regions populated")
    for level, count in results:
        print(f"    - {level}: {count}")

    # Part 3: Create composite indexes on ngram_tendency
    print("\n[3/3] Creating composite indexes on ngram_tendency...")
    ngram_indexes = [
        ('idx_ngram_tendency_level_ngram', 'ngram_tendency', 'level, ngram'),
        ('idx_ngram_tendency_level_township', 'ngram_tendency', 'level, township'),
        ('idx_ngram_tendency_level_county', 'ngram_tendency', 'level, county'),
        ('idx_ngram_tendency_level_city', 'ngram_tendency', 'level, city'),
        ('idx_ngram_tendency_level_lift', 'ngram_tendency', 'level, lift DESC')
    ]

    for idx_name, table, columns in ngram_indexes:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})')
            print(f"  [OK] {idx_name}")
        except Exception as e:
            print(f"  [SKIP] {idx_name}: {e}")

    conn.commit()
    conn.close()

    print("\n[OK] Optimization indexes created")
    print("Expected API performance improvement: 95%+ (2-3s -> 0.1-0.15s)")


def main():
    """Main execution function."""
    db_path = 'data/villages.db'

    print("\n" + "="*60)
    print("Phase 12: N-gram Structure Analysis")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    # Generate run_id for this analysis
    run_id = f"ngram_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Run ID: {run_id}")

    try:
        step1_create_tables(db_path)
        step2_extract_global_ngrams(db_path)
        step3_extract_regional_ngrams(db_path)
        step3_5_calculate_regional_totals_raw(db_path)  # NEW: Calculate raw totals
        step4_calculate_tendency(db_path)
        step5_calculate_significance(db_path)
        step6_cleanup_insignificant_data(db_path)  # NEW: Clean up non-significant data
        step7_detect_patterns(db_path)
        step8_create_optimization_indexes(db_path)  # NEW: Create optimization indexes

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*60)
        print("Phase 12 Complete!")
        print("="*60)
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print("\nAll n-gram analysis results stored in database.")
        print("NOTE: Only statistically significant n-grams (p < 0.05) are retained.")

        # Auto-update active_run_ids (NEW: 2026-02-25)
        print("\n" + "="*60)
        print("Updating active_run_ids...")
        print("="*60)

        # Count significant n-grams for notes
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ngram_significance")
        sig_count = cursor.fetchone()[0]
        conn.close()

        update_active_run_id(
            analysis_type="ngrams",
            run_id=run_id,
            script_name="phase12_ngram_analysis",
            notes=f"N-gram analysis complete. {sig_count:,} significant n-grams (p < 0.05) stored.",
            db_path=db_path
        )

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

