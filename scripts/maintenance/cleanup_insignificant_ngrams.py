#!/usr/bin/env python3
"""
Remove non-significant n-grams (p_value >= 0.05) from database.

This script:
1. Identifies non-significant n-grams
2. Deletes them from all related tables
3. Runs VACUUM to reclaim space
4. Generates cleanup report
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def cleanup_insignificant_ngrams(db_path: str, dry_run: bool = True):
    """Remove non-significant n-grams from database."""

    print("=" * 70)
    print("N-gram Cleanup Script")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Timestamp: {datetime.now()}")
    print()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Identify non-significant n-grams
    print("Step 1: Identifying non-significant n-grams...")
    cursor.execute("""
        SELECT COUNT(*)
        FROM ngram_significance
        WHERE p_value >= 0.05
    """)
    count_to_delete = cursor.fetchone()[0]
    print(f"  Found {count_to_delete:,} non-significant n-grams to delete")

    # Get breakdown by level
    cursor.execute("""
        SELECT level, COUNT(*)
        FROM ngram_significance
        WHERE p_value >= 0.05
        GROUP BY level
    """)
    for level, count in cursor.fetchall():
        print(f"    {level}: {count:,}")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run with dry_run=False to execute.")
        conn.close()
        return

    # Step 2: Delete from ngram_significance
    print("\nStep 2: Deleting from ngram_significance...")
    cursor.execute("DELETE FROM ngram_significance WHERE p_value >= 0.05")
    deleted_sig = cursor.rowcount
    print(f"  Deleted {deleted_sig:,} rows")

    # Step 3: Delete from ngram_tendency
    print("\nStep 3: Deleting from ngram_tendency...")
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
    deleted_tend = cursor.rowcount
    print(f"  Deleted {deleted_tend:,} rows")

    # Step 4: Delete from regional_ngram_frequency
    print("\nStep 4: Deleting from regional_ngram_frequency...")
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
    deleted_freq = cursor.rowcount
    print(f"  Deleted {deleted_freq:,} rows")

    conn.commit()

    # Step 5: VACUUM to reclaim space
    print("\nStep 5: Running VACUUM to reclaim space...")
    print("  This may take 5-10 minutes...")
    cursor.execute("VACUUM")
    print("  VACUUM complete")

    # Step 6: Verify results
    print("\nStep 6: Verification...")
    cursor.execute("SELECT COUNT(*) FROM ngram_significance")
    remaining_sig = cursor.fetchone()[0]
    print(f"  Remaining in ngram_significance: {remaining_sig:,}")

    cursor.execute("SELECT COUNT(*) FROM ngram_tendency")
    remaining_tend = cursor.fetchone()[0]
    print(f"  Remaining in ngram_tendency: {remaining_tend:,}")

    cursor.execute("SELECT COUNT(*) FROM regional_ngram_frequency")
    remaining_freq = cursor.fetchone()[0]
    print(f"  Remaining in regional_ngram_frequency: {remaining_freq:,}")

    # Check database size
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    new_size_gb = (page_count * page_size) / (1024**3)
    print(f"\n  New database size: {new_size_gb:.2f} GB")

    conn.close()

    # Generate report
    print("\n" + "=" * 70)
    print("Cleanup Summary")
    print("=" * 70)
    print(f"Deleted from ngram_significance: {deleted_sig:,}")
    print(f"Deleted from ngram_tendency: {deleted_tend:,}")
    print(f"Deleted from regional_ngram_frequency: {deleted_freq:,}")
    print(f"Total deleted: {deleted_sig + deleted_tend + deleted_freq:,}")
    print(f"Database size after cleanup: {new_size_gb:.2f} GB")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean up non-significant n-grams")
    parser.add_argument("--db", default="data/villages.db", help="Database path")
    parser.add_argument("--execute", action="store_true", help="Execute cleanup (default is dry run)")

    args = parser.parse_args()

    cleanup_insignificant_ngrams(args.db, dry_run=not args.execute)
