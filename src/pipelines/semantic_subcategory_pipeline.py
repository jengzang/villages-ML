"""Semantic subcategory refinement pipeline.

Phase 17: Generates semantic_subcategory_* tables from v4 lexicon.
1. Load v4 lexicon
2. Create subcategory tables
3. Populate subcategory labels
4. Calculate global VTF
5. Calculate regional VTF
6. Validate data quality
"""

import json
import logging
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from src.schema import get_schema

logger = logging.getLogger(__name__)


def run_semantic_subcategory_pipeline(
    db_path: str,
    run_id: str = '',
    lexicon_path: str = 'data/semantic_lexicon_v4.json',
    schema_name: str = 'guangdong',
) -> dict:
    """Run the semantic subcategory VTF analysis pipeline.

    Generates: semantic_subcategory_labels, semantic_subcategory_vtf_global,
    semantic_subcategory_vtf_regional tables.
    """
    logger.info("=" * 60)
    logger.info("Phase 17: Semantic Subcategory VTF Analysis (v4)")
    logger.info(f"  DB: {db_path}")
    logger.info(f"  Lexicon: {lexicon_path}")
    logger.info("=" * 60)

    start_time = time.time()

    # Step 1: Load lexicon
    logger.info("Step 1: Loading v4 lexicon...")
    with open(lexicon_path, 'r', encoding='utf-8') as f:
        v4 = json.load(f)
    flat = flatten_v4_subcategories(v4)
    logger.info(f"  Loaded v4 lexicon: {v4.get('version', 'unknown')}")
    logger.info(f"  {len(set(s for s, _, _ in flat))} subcategories, {len(flat)} char mappings")

    conn = sqlite3.connect(db_path)
    S = get_schema(schema_name)

    try:
        # Step 2: Create tables
        logger.info("Step 2: Creating subcategory tables...")
        _create_tables(conn)

        # Step 3: Populate labels
        logger.info("Step 3: Populating subcategory labels...")
        _populate_labels(conn, v4)

        # Step 4: Global VTF
        logger.info("Step 4: Calculating global subcategory VTF...")
        _calculate_global_vtf(conn, S)

        # Step 5: Regional VTF
        logger.info("Step 5: Calculating regional subcategory VTF...")
        _calculate_regional_vtf(conn)

        # Step 6: Validate
        logger.info("Step 6: Validating data quality...")
        _validate(conn)

    finally:
        conn.close()

    elapsed = time.time() - start_time
    logger.info(f"Phase 17 completed in {elapsed:.1f}s")

    return {
        'run_id': run_id,
        'runtime_seconds': round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------


def flatten_v4_subcategories(v4: Dict) -> List[Tuple[str, str, str]]:
    """Flatten nested v4 format {parent: {sub: [chars]}} into (parent_sub, parent, char) tuples.

    Within a parent, a char in multiple subcategories gets ALL entries.
    Cross-parent duplicates: first parent wins, then multi_label entries
    add secondary parent subcategory mappings.
    """
    seen_parent: set = set()
    char_first_parent: dict = {}
    result = []
    categories = v4.get("categories", {})

    for parent, children in categories.items():
        if isinstance(children, dict):
            char_subs: dict = {}
            for sub, chars in children.items():
                for char in chars:
                    char_subs.setdefault(char, []).append(sub)
            for char, subs in char_subs.items():
                if char in seen_parent:
                    continue
                seen_parent.add(char)
                char_first_parent[char] = parent
                for sub in subs:
                    result.append((f'{parent}_{sub}', parent, char))
        else:
            for char in children:
                if char in seen_parent:
                    continue
                seen_parent.add(char)
                char_first_parent[char] = parent
                result.append((parent, parent, char))

    # Add secondary parent entries from multi_label
    multi = v4.get('multi_label', {})
    for char, parents in multi.items():
        first = char_first_parent.get(char)
        if first is None:
            continue
        for parent in parents:
            if parent == first:
                continue
            children = categories.get(parent, {})
            if isinstance(children, dict):
                for sub, chars in children.items():
                    if char in chars:
                        result.append((f'{parent}_{sub}', parent, char))

    return result


def _create_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS semantic_subcategory_labels")
    cursor.execute("""
        CREATE TABLE semantic_subcategory_labels (
            char TEXT NOT NULL,
            parent_category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            labeling_method TEXT DEFAULT 'manual',
            created_at REAL DEFAULT (julianday('now')),
            PRIMARY KEY (char, subcategory)
        )
    """)
    logger.info("  Created: semantic_subcategory_labels")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_subcategory_vtf_global (
            subcategory TEXT PRIMARY KEY,
            parent_category TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            village_count INTEGER NOT NULL,
            vtf REAL NOT NULL,
            percentage REAL NOT NULL,
            created_at REAL DEFAULT (julianday('now'))
        )
    """)
    logger.info("  Created: semantic_subcategory_vtf_global")

    cursor.execute("DROP TABLE IF EXISTS semantic_subcategory_vtf_regional")
    cursor.execute("""
        CREATE TABLE semantic_subcategory_vtf_regional (
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            city TEXT, county TEXT, township TEXT,
            subcategory TEXT NOT NULL,
            parent_category TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            village_count INTEGER NOT NULL,
            vtf REAL NOT NULL,
            percentage REAL NOT NULL,
            tendency REAL,
            created_at REAL DEFAULT (julianday('now')),
            PRIMARY KEY (region_level, region_name, subcategory)
        )
    """)
    logger.info("  Created: semantic_subcategory_vtf_regional")

    conn.commit()


def _populate_labels(conn: sqlite3.Connection, v4: Dict):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM semantic_subcategory_labels")

    flat = flatten_v4_subcategories(v4)
    labels = [(char, parent, subcategory, 1.0, 'v4') for subcategory, parent, char in flat]
    cursor.executemany(
        "INSERT INTO semantic_subcategory_labels "
        "(char, parent_category, subcategory, confidence, labeling_method) "
        "VALUES (?, ?, ?, ?, ?)",
        labels,
    )
    conn.commit()
    logger.info(f"  Inserted {len(labels)} subcategory labels")
    logger.info(f"    {len(set(p for _, p, _ in flat))} parent categories")
    logger.info(f"    {len(set(s for s, _, _ in flat))} subcategories")

    # Coverage by parent category
    cursor.execute("""
        SELECT parent_category, COUNT(DISTINCT char) as char_count
        FROM semantic_subcategory_labels
        GROUP BY parent_category ORDER BY parent_category
    """)
    for parent, count in cursor.fetchall():
        logger.info(f"  {parent}: {count} chars")


def _calculate_global_vtf(conn: sqlite3.Connection, S):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM semantic_subcategory_vtf_global")

    cursor.execute(f"""
        INSERT INTO semantic_subcategory_vtf_global
        (subcategory, parent_category, char_count, village_count, vtf, percentage)
        SELECT
            sl.subcategory,
            sl.parent_category,
            COUNT(DISTINCT sl.char) as char_count,
            SUM(cf.village_count) as village_count,
            CAST(SUM(cf.village_count) AS REAL) /
                (SELECT COUNT(*) FROM {S.preprocessed_table}) as vtf,
            CAST(SUM(cf.village_count) AS REAL) /
                (SELECT COUNT(*) FROM {S.preprocessed_table}) as percentage
        FROM semantic_subcategory_labels sl
        JOIN char_frequency_global cf ON sl.char = cf.char
        GROUP BY sl.subcategory, sl.parent_category
    """)
    conn.commit()

    cursor.execute("""
        SELECT subcategory, parent_category, char_count, village_count, vtf, percentage
        FROM semantic_subcategory_vtf_global
        ORDER BY parent_category, vtf DESC
    """)
    for row in cursor.fetchall():
        subcat, parent, char_count, village_count, vtf, pct = row
        logger.info(f"  {subcat:<30} {parent:<14} chars={char_count:<5} villages={village_count:<8} vtf={vtf:.4f}")

    cursor.execute("SELECT COUNT(*) FROM semantic_subcategory_vtf_global")
    logger.info(f"  Calculated global VTF for {cursor.fetchone()[0]} subcategories")


def _calculate_regional_vtf(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM semantic_subcategory_vtf_regional")

    logger.info("  Computing city/county/township regional VTF...")
    cursor.execute("""
        INSERT INTO semantic_subcategory_vtf_regional
        (region_level, region_name, city, county, township,
         subcategory, parent_category, char_count, village_count,
         vtf, percentage, tendency)
        SELECT
            cra.region_level,
            cra.region_name,
            MAX(cra.city) as city,
            MAX(cra.county) as county,
            MAX(cra.township) as township,
            sl.subcategory,
            sl.parent_category,
            COUNT(DISTINCT sl.char) as char_count,
            SUM(cra.village_count) as village_count,
            CAST(SUM(cra.village_count) AS REAL) / MAX(cra.total_villages) as vtf,
            CAST(SUM(cra.village_count) AS REAL) / MAX(cra.total_villages) as percentage,
            (CAST(SUM(cra.village_count) AS REAL) / MAX(cra.total_villages)) - gv.global_pct as tendency
        FROM semantic_subcategory_labels sl
        JOIN char_regional_analysis cra ON sl.char = cra.char
        JOIN (
            SELECT subcategory, percentage as global_pct
            FROM semantic_subcategory_vtf_global
        ) gv ON sl.subcategory = gv.subcategory
        GROUP BY cra.region_level, cra.region_name, sl.subcategory, sl.parent_category
    """)
    conn.commit()

    cursor.execute("""
        SELECT region_level, COUNT(DISTINCT region_name) as region_count, COUNT(*) as record_count
        FROM semantic_subcategory_vtf_regional
        GROUP BY region_level
    """)
    for region_level, region_count, record_count in cursor.fetchall():
        logger.info(f"  {region_level}: {region_count} regions, {record_count} records")


def _validate(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Coverage
    cursor.execute("""
        SELECT parent_category, COUNT(DISTINCT char) as labeled_count
        FROM semantic_subcategory_labels GROUP BY parent_category
    """)
    logger.info("Subcategory coverage:")
    for parent, count in cursor.fetchall():
        logger.info(f"  {parent}: {count} chars labeled")

    # Subcategory distribution
    cursor.execute("""
        SELECT subcategory, COUNT(*) as char_count
        FROM semantic_subcategory_labels
        GROUP BY subcategory ORDER BY char_count DESC
    """)
    logger.info("Subcategory char distribution:")
    for subcat, count in cursor.fetchall():
        logger.info(f"  {subcat}: {count} chars")

    # VTF completeness
    cursor.execute("SELECT COUNT(*) FROM semantic_subcategory_vtf_global")
    global_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT subcategory) FROM semantic_subcategory_labels")
    expected = cursor.fetchone()[0]
    logger.info(f"VTF completeness: {global_count}/{expected} subcategories")

    # Regional VTF
    cursor.execute("""
        SELECT COUNT(DISTINCT region_name) as region_count, COUNT(*) as record_count
        FROM semantic_subcategory_vtf_regional
    """)
    region_count, record_count = cursor.fetchone()
    logger.info(f"Regional VTF: {region_count} regions, {record_count} records")

    # Top tendency
    cursor.execute("""
        SELECT subcategory, MAX(tendency) as max_tendency, MIN(tendency) as min_tendency,
               AVG(tendency) as avg_tendency
        FROM semantic_subcategory_vtf_regional
        GROUP BY subcategory ORDER BY max_tendency DESC LIMIT 5
    """)
    logger.info("Top 5 subcategories by max tendency:")
    for row in cursor.fetchall():
        subcat, max_t, min_t, avg_t = row
        logger.info(f"  {subcat:<30} max={max_t:+.2f} min={min_t:+.2f} avg={avg_t:+.2f}")
