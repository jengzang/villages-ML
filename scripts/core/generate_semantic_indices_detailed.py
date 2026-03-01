#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate semantic_indices_detailed table using v4_hybrid lexicon (76 subcategories).

This script creates a detailed version of semantic_indices table with fine-grained
subcategory analysis.

Usage:
    python scripts/core/generate_semantic_indices_detailed.py
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    print("=" * 60)
    print("Generate semantic_indices_detailed Table")
    print("=" * 60)

    db_path = project_root / "data" / "villages.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Create detailed table
    print("\n[Step 1] Creating semantic_indices_detailed table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_indices_detailed (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            category TEXT NOT NULL,
            raw_intensity REAL NOT NULL,
            normalized_index REAL NOT NULL,
            z_score REAL,
            rank_within_province INTEGER NOT NULL,
            village_count INTEGER,
            PRIMARY KEY (run_id, region_level, region_name, category)
        )
    """)
    conn.commit()
    print("[OK] Table created")

    # Step 2: Run populate_semantic_indices.py with v4_hybrid lexicon
    print("\n[Step 2] Running populate_semantic_indices.py with v4_hybrid lexicon...")
    print("This will take a few minutes...")

    import subprocess
    result = subprocess.run([
        sys.executable,
        str(project_root / "scripts" / "core" / "populate_semantic_indices.py"),
        "--output-run-id", "semantic_indices_detailed_001",
        "--lexicon-path", str(project_root / "data" / "semantic_lexicon_v4_hybrid.json")
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[ERROR] Failed to run populate_semantic_indices.py")
        print(result.stderr)
        return

    print(result.stdout)

    # Step 3: Copy data from semantic_indices to semantic_indices_detailed
    print("\n[Step 3] Copying data to semantic_indices_detailed...")
    cursor.execute("""
        INSERT OR REPLACE INTO semantic_indices_detailed
        SELECT * FROM semantic_indices
        WHERE run_id = 'semantic_indices_detailed_001'
    """)
    conn.commit()

    # Step 4: Clean up temporary data from semantic_indices
    print("\n[Step 4] Cleaning up temporary data...")
    cursor.execute("""
        DELETE FROM semantic_indices
        WHERE run_id = 'semantic_indices_detailed_001'
    """)
    conn.commit()

    # Step 5: Verify results
    print("\n[Step 5] Verification...")
    cursor.execute("""
        SELECT COUNT(*) as total_records,
               COUNT(DISTINCT category) as unique_categories,
               COUNT(DISTINCT region_name) as unique_regions
        FROM semantic_indices_detailed
    """)
    stats = cursor.fetchone()
    print(f"  Total records: {stats[0]:,}")
    print(f"  Unique categories: {stats[1]}")
    print(f"  Unique regions: {stats[2]}")

    # Show sample categories
    cursor.execute("""
        SELECT DISTINCT category
        FROM semantic_indices_detailed
        ORDER BY category
        LIMIT 10
    """)
    categories = [row[0] for row in cursor.fetchall()]
    print(f"\n  Sample categories: {', '.join(categories)}")

    conn.close()

    print("\n" + "=" * 60)
    print("[OK] semantic_indices_detailed table generated successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
