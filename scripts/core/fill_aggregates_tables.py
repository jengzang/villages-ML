"""
Phase 7: Feature Materialization (DEPRECATED).

This phase previously filled city_aggregates, county_aggregates, and town_aggregates
tables. These precomputed aggregate tables have been replaced by real-time SQL queries
(GROUP BY on 广东省自然村 joined with semantic_indices).

This script is kept as a no-op for backward compatibility with the pipeline runner.
"""

import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Phase 7 deprecated no-op")
    parser.add_argument("--db-path", default="data/villages.db", help="Accepted for pipeline config compatibility")
    parser.add_argument("--run-id", default=None, help="Accepted for pipeline config compatibility")
    parser.parse_args()

    print("=" * 60)
    print("Phase 7: Feature Materialization (DEPRECATED)")
    print("=" * 60)
    print()
    print("Precomputed city/county/town_aggregates tables have been replaced by")
    print("real-time SQL queries. No offline computation needed.")
    print()
    print("Phase 7 complete (no-op)")
    print("=" * 60)


if __name__ == '__main__':
    main()
