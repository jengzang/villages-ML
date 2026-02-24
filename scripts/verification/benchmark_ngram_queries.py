#!/usr/bin/env python3
"""
Benchmark n-gram query performance.

This script measures query performance for common n-gram operations.
Run before and after cleanup to compare performance.
"""

import sqlite3
import time
from typing import List, Tuple


def benchmark_queries(db_path: str) -> List[Tuple[str, float]]:
    """Benchmark common n-gram queries."""

    print("=" * 70)
    print("N-gram Query Performance Benchmark")
    print("=" * 70)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    queries = [
        ("Regional n-gram query (township)", """
            SELECT * FROM regional_ngram_frequency
            WHERE level = 'township' LIMIT 1000
        """),
        ("Significance query (p < 0.05)", """
            SELECT * FROM ngram_significance
            WHERE p_value < 0.05 LIMIT 1000
        """),
        ("Tendency query (city level)", """
            SELECT * FROM ngram_tendency
            WHERE level = 'city' LIMIT 1000
        """),
        ("Join query (frequency + significance)", """
            SELECT f.*, s.p_value, s.is_significant
            FROM regional_ngram_frequency f
            JOIN ngram_significance s
              ON f.ngram = s.ngram
              AND f.level = s.level
              AND f.city = s.city
              AND f.county = s.county
              AND f.township = s.township
            WHERE s.is_significant = 1
            LIMIT 1000
        """),
        ("Aggregation query (count by level)", """
            SELECT level, COUNT(*), AVG(p_value)
            FROM ngram_significance
            GROUP BY level
        """),
        ("Top n-grams query", """
            SELECT ngram, COUNT(*) as freq
            FROM regional_ngram_frequency
            WHERE level = 'township'
            GROUP BY ngram
            ORDER BY freq DESC
            LIMIT 100
        """),
    ]

    results = []

    for name, query in queries:
        print(f"Running: {name}")

        # Warm up
        cursor.execute(query)
        cursor.fetchall()

        # Actual benchmark (3 runs)
        times = []
        for i in range(3):
            start = time.time()
            cursor.execute(query)
            cursor.fetchall()
            duration = time.time() - start
            times.append(duration)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"  Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s\n")
        results.append((name, avg_time))

    conn.close()

    print("=" * 70)
    print("Summary")
    print("=" * 70)
    for name, avg_time in results:
        print(f"{name}: {avg_time:.3f}s")
    print("=" * 70)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark n-gram queries")
    parser.add_argument("--db", default="data/villages.db", help="Database path")

    args = parser.parse_args()

    benchmark_queries(args.db)
