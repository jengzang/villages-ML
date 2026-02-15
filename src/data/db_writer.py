"""
Database writer module for persisting frequency analysis results.

This module handles:
- Creating analysis result tables
- Batch inserting data from CSV files
- Creating indexes for query optimization
- Transaction management
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def create_analysis_tables(conn: sqlite3.Connection) -> None:
    """
    Create analysis result tables if they don't exist.

    Creates 4 tables:
    - analysis_runs: Run metadata
    - char_frequency_global: Global character frequency
    - char_frequency_regional: Regional character frequency
    - regional_tendency: Regional tendency analysis

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Table 1: analysis_runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            total_villages INTEGER NOT NULL,
            valid_villages INTEGER NOT NULL,
            unique_chars INTEGER NOT NULL,
            config_json TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT
        )
    """)

    # Table 2: char_frequency_global
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS char_frequency_global (
            run_id TEXT NOT NULL,
            char TEXT NOT NULL,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank INTEGER NOT NULL,
            PRIMARY KEY (run_id, char),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 3: char_frequency_regional
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS char_frequency_regional (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            char TEXT NOT NULL,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            PRIMARY KEY (run_id, region_level, region_name, char),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 4: regional_tendency
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regional_tendency (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            char TEXT NOT NULL,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            global_village_count INTEGER NOT NULL,
            global_frequency REAL NOT NULL,
            lift REAL NOT NULL,
            log_lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL,
            support_flag INTEGER NOT NULL,
            rank_overrepresented INTEGER,
            rank_underrepresented INTEGER,
            PRIMARY KEY (run_id, region_level, region_name, char),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 5: semantic_vtf_global
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_vtf_global (
            run_id TEXT NOT NULL,
            category TEXT NOT NULL,
            vtf_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank INTEGER NOT NULL,
            PRIMARY KEY (run_id, category),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 6: semantic_vtf_regional
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_vtf_regional (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            category TEXT NOT NULL,
            vtf_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            PRIMARY KEY (run_id, region_level, region_name, category),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 7: semantic_tendency
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_tendency (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            category TEXT NOT NULL,
            frequency REAL NOT NULL,
            global_frequency REAL NOT NULL,
            lift REAL NOT NULL,
            log_lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL,
            vtf_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            support_flag INTEGER NOT NULL,
            PRIMARY KEY (run_id, region_level, region_name, category),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 8: semantic_indices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_indices (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            category TEXT NOT NULL,
            raw_intensity REAL NOT NULL,
            normalized_index REAL NOT NULL,
            z_score REAL,
            rank_within_province INTEGER NOT NULL,
            PRIMARY KEY (run_id, region_level, region_name, category),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    conn.commit()
    logger.info("Analysis tables created successfully")


def create_indexes(conn: sqlite3.Connection) -> None:
    """
    Create indexes for query optimization.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Indexes for analysis_runs
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_created ON analysis_runs(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON analysis_runs(status)")

    # Indexes for char_frequency_global
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_global_char ON char_frequency_global(run_id, char)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_global_rank ON char_frequency_global(run_id, rank)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_global_freq ON char_frequency_global(run_id, frequency DESC)")

    # Indexes for char_frequency_regional
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regional_level ON char_frequency_regional(run_id, region_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regional_name ON char_frequency_regional(run_id, region_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regional_char ON char_frequency_regional(run_id, char)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regional_freq ON char_frequency_regional(run_id, region_level, frequency DESC)")

    # Indexes for regional_tendency
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tendency_level ON regional_tendency(run_id, region_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tendency_char ON regional_tendency(run_id, char)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tendency_lift ON regional_tendency(run_id, region_level, lift DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tendency_logodds ON regional_tendency(run_id, region_level, log_odds DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tendency_zscore ON regional_tendency(run_id, region_level, z_score DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tendency_support ON regional_tendency(run_id, support_flag)")

    conn.commit()
    logger.info("Indexes created successfully")


def save_run_metadata(conn: sqlite3.Connection, run_id: str, metadata: Dict[str, Any]) -> None:
    """
    Save run metadata to analysis_runs table.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        metadata: Dictionary containing run metadata
    """
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO analysis_runs
        (run_id, created_at, total_villages, valid_villages, unique_chars, config_json, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        metadata['created_at'],
        metadata['total_villages'],
        metadata['valid_villages'],
        metadata['unique_chars'],
        json.dumps(metadata.get('config', {}), ensure_ascii=False),
        metadata.get('status', 'completed'),
        metadata.get('notes')
    ))

    conn.commit()
    logger.info(f"Saved metadata for run_id={run_id}")


def save_global_frequency(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame, batch_size: int = 10000) -> None:
    """
    Save global frequency data to char_frequency_global table.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with columns: char, village_count, total_villages, frequency, rank
        batch_size: Number of rows to insert per batch
    """
    cursor = conn.cursor()

    # Prepare data for insertion
    df_copy = df.copy()
    df_copy['run_id'] = run_id

    # Select and reorder columns
    columns = ['run_id', 'char', 'village_count', 'total_villages', 'frequency', 'rank']
    data = df_copy[columns].values.tolist()

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO char_frequency_global
            (run_id, char, village_count, total_villages, frequency, rank)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} global frequency records for run_id={run_id}")


def save_regional_frequency(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame, batch_size: int = 10000) -> None:
    """
    Save regional frequency data to char_frequency_regional table.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with columns: region_level, region_name, char, village_count, total_villages, frequency, rank_within_region
        batch_size: Number of rows to insert per batch
    """
    cursor = conn.cursor()

    # Prepare data for insertion
    df_copy = df.copy()
    df_copy['run_id'] = run_id

    # Select and reorder columns
    columns = ['run_id', 'region_level', 'region_name', 'char', 'village_count', 'total_villages', 'frequency', 'rank_within_region']
    data = df_copy[columns].values.tolist()

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO char_frequency_regional
            (run_id, region_level, region_name, char, village_count, total_villages, frequency, rank_within_region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} regional frequency records for run_id={run_id}")


def save_regional_tendency(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame, batch_size: int = 10000) -> None:
    """
    Save regional tendency data to regional_tendency table.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with tendency analysis columns
        batch_size: Number of rows to insert per batch
    """
    cursor = conn.cursor()

    # Prepare data for insertion
    df_copy = df.copy()
    df_copy['run_id'] = run_id

    # Handle NaN values for optional columns
    df_copy['z_score'] = df_copy['z_score'].where(pd.notna(df_copy['z_score']), None)
    df_copy['rank_overrepresented'] = df_copy['rank_overrepresented'].where(pd.notna(df_copy['rank_overrepresented']), None)
    df_copy['rank_underrepresented'] = df_copy['rank_underrepresented'].where(pd.notna(df_copy['rank_underrepresented']), None)

    # Select and reorder columns
    columns = [
        'run_id', 'region_level', 'region_name', 'char',
        'village_count', 'total_villages', 'frequency', 'rank_within_region',
        'global_village_count', 'global_frequency',
        'lift', 'log_lift', 'log_odds', 'z_score', 'support_flag',
        'rank_overrepresented', 'rank_underrepresented'
    ]
    data = df_copy[columns].values.tolist()

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO regional_tendency
            (run_id, region_level, region_name, char,
             village_count, total_villages, frequency, rank_within_region,
             global_village_count, global_frequency,
             lift, log_lift, log_odds, z_score, support_flag,
             rank_overrepresented, rank_underrepresented)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} regional tendency records for run_id={run_id}")


def persist_results_to_db(db_path: str, run_id: str, results_dir: Path,
                         region_levels: list = None, batch_size: int = 10000) -> None:
    """
    Main function to persist all analysis results to database.

    Args:
        db_path: Path to SQLite database
        run_id: Run identifier
        results_dir: Directory containing CSV result files
        region_levels: List of region levels to process (default: ['city', 'county', 'township'])
        batch_size: Number of rows to insert per batch
    """
    import time

    if region_levels is None:
        region_levels = ['city', 'county', 'township']

    logger.info(f"Starting database persistence for run_id={run_id}")
    start_time = time.time()

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Create tables and indexes
        logger.info("Creating tables...")
        create_analysis_tables(conn)

        # Step 2: Load CSV files
        logger.info("Loading CSV files...")

        # Load global frequency
        global_freq_file = results_dir / "char_frequency_global.csv"
        if not global_freq_file.exists():
            raise FileNotFoundError(f"Global frequency file not found: {global_freq_file}")
        global_freq_df = pd.read_csv(global_freq_file)
        logger.info(f"Loaded {len(global_freq_df)} global frequency records")

        # Load and combine regional frequency files
        regional_freq_dfs = []
        for level in region_levels:
            regional_freq_file = results_dir / f"char_frequency_{level}.csv"
            if regional_freq_file.exists():
                df = pd.read_csv(regional_freq_file)
                regional_freq_dfs.append(df)
                logger.info(f"Loaded {len(df)} {level}-level frequency records")
            else:
                logger.warning(f"Regional frequency file not found: {regional_freq_file}")

        if not regional_freq_dfs:
            raise FileNotFoundError("No regional frequency files found")
        regional_freq_df = pd.concat(regional_freq_dfs, ignore_index=True)
        logger.info(f"Combined {len(regional_freq_df)} total regional frequency records")

        # Load and combine tendency files
        tendency_dfs = []
        for level in region_levels:
            tendency_file = results_dir / f"regional_tendency_{level}.csv"
            if tendency_file.exists():
                df = pd.read_csv(tendency_file)
                # Remove run_id column if it exists (we'll add it during insertion)
                if 'run_id' in df.columns:
                    df = df.drop(columns=['run_id'])
                tendency_dfs.append(df)
                logger.info(f"Loaded {len(df)} {level}-level tendency records")
            else:
                logger.warning(f"Tendency file not found: {tendency_file}")

        if not tendency_dfs:
            raise FileNotFoundError("No tendency files found")
        tendency_df = pd.concat(tendency_dfs, ignore_index=True)
        logger.info(f"Combined {len(tendency_df)} total tendency records")

        # Step 3: Save run metadata
        logger.info("Saving run metadata...")
        metadata = {
            'created_at': time.time(),
            'total_villages': int(global_freq_df['total_villages'].iloc[0]) if len(global_freq_df) > 0 else 0,
            'valid_villages': int(global_freq_df['total_villages'].iloc[0]) if len(global_freq_df) > 0 else 0,
            'unique_chars': len(global_freq_df),
            'config': {'batch_size': batch_size, 'region_levels': region_levels},
            'status': 'completed'
        }
        save_run_metadata(conn, run_id, metadata)

        # Step 4: Save frequency data
        logger.info("Saving global frequency data...")
        save_global_frequency(conn, run_id, global_freq_df, batch_size)

        logger.info("Saving regional frequency data...")
        save_regional_frequency(conn, run_id, regional_freq_df, batch_size)

        logger.info("Saving regional tendency data...")
        save_regional_tendency(conn, run_id, tendency_df, batch_size)

        # Step 5: Create indexes
        logger.info("Creating indexes...")
        create_indexes(conn)

        elapsed = time.time() - start_time
        logger.info(f"Database persistence completed in {elapsed:.2f}s")

    except Exception as e:
        logger.error(f"Error persisting results to database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def create_morphology_tables(conn: sqlite3.Connection) -> None:
    """
    Create morphology analysis result tables if they don't exist.

    Creates 3 tables:
    - pattern_frequency_global: Global pattern frequency
    - pattern_frequency_regional: Regional pattern frequency
    - pattern_tendency: Regional pattern tendency analysis

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Table 1: pattern_frequency_global
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_frequency_global (
            run_id TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank INTEGER NOT NULL,
            PRIMARY KEY (run_id, pattern_type, pattern),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 2: pattern_frequency_regional
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_frequency_regional (
            run_id TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            pattern TEXT NOT NULL,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            PRIMARY KEY (run_id, pattern_type, region_level, region_name, pattern),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # Table 3: pattern_tendency
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_tendency (
            run_id TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_name TEXT NOT NULL,
            pattern TEXT NOT NULL,
            village_count INTEGER NOT NULL,
            total_villages INTEGER NOT NULL,
            frequency REAL NOT NULL,
            rank_within_region INTEGER NOT NULL,
            global_village_count INTEGER NOT NULL,
            global_frequency REAL NOT NULL,
            lift REAL NOT NULL,
            log_lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL,
            support_flag INTEGER NOT NULL,
            rank_overrepresented INTEGER,
            rank_underrepresented INTEGER,
            PRIMARY KEY (run_id, pattern_type, region_level, region_name, pattern),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    conn.commit()
    logger.info("Morphology analysis tables created successfully")


def create_morphology_indexes(conn: sqlite3.Connection) -> None:
    """
    Create indexes for morphology tables.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Indexes for pattern_frequency_global
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_global_type ON pattern_frequency_global(run_id, pattern_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_global_pattern ON pattern_frequency_global(run_id, pattern)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_global_rank ON pattern_frequency_global(run_id, pattern_type, rank)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_global_freq ON pattern_frequency_global(run_id, pattern_type, frequency DESC)")

    # Indexes for pattern_frequency_regional
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_regional_type ON pattern_frequency_regional(run_id, pattern_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_regional_level ON pattern_frequency_regional(run_id, region_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_regional_name ON pattern_frequency_regional(run_id, region_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_regional_pattern ON pattern_frequency_regional(run_id, pattern)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_regional_freq ON pattern_frequency_regional(run_id, pattern_type, region_level, frequency DESC)")

    # Indexes for pattern_tendency
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_tendency_type ON pattern_tendency(run_id, pattern_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_tendency_level ON pattern_tendency(run_id, region_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_tendency_pattern ON pattern_tendency(run_id, pattern)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_tendency_lift ON pattern_tendency(run_id, pattern_type, region_level, lift DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_tendency_logodds ON pattern_tendency(run_id, pattern_type, region_level, log_odds DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_tendency_zscore ON pattern_tendency(run_id, pattern_type, region_level, z_score DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_tendency_support ON pattern_tendency(run_id, support_flag)")

    conn.commit()
    logger.info("Morphology indexes created successfully")


def save_pattern_frequency_global(conn: sqlite3.Connection, run_id: str, pattern_type: str, df: pd.DataFrame, batch_size: int = 10000) -> None:
    """
    Save global pattern frequency data.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        pattern_type: Pattern type (e.g., 'suffix_1', 'prefix_2')
        df: DataFrame with columns: pattern, village_count, total_villages, frequency, rank
        batch_size: Number of rows to insert per batch
    """
    cursor = conn.cursor()

    # Prepare data for insertion
    df_copy = df.copy()
    df_copy['run_id'] = run_id
    df_copy['pattern_type'] = pattern_type

    # Select and reorder columns
    columns = ['run_id', 'pattern_type', 'pattern', 'village_count', 'total_villages', 'frequency', 'rank']
    data = df_copy[columns].values.tolist()

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO pattern_frequency_global
            (run_id, pattern_type, pattern, village_count, total_villages, frequency, rank)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} global pattern frequency records for {pattern_type}")


def save_pattern_frequency_regional(conn: sqlite3.Connection, run_id: str, pattern_type: str, df: pd.DataFrame, batch_size: int = 10000) -> None:
    """
    Save regional pattern frequency data.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        pattern_type: Pattern type (e.g., 'suffix_1', 'prefix_2')
        df: DataFrame with columns: region_level, region_name, pattern, village_count, total_villages, frequency, rank_within_region
        batch_size: Number of rows to insert per batch
    """
    cursor = conn.cursor()

    # Prepare data for insertion
    df_copy = df.copy()
    df_copy['run_id'] = run_id
    df_copy['pattern_type'] = pattern_type

    # Select and reorder columns
    columns = ['run_id', 'pattern_type', 'region_level', 'region_name', 'pattern', 'village_count', 'total_villages', 'frequency', 'rank_within_region']
    data = df_copy[columns].values.tolist()

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO pattern_frequency_regional
            (run_id, pattern_type, region_level, region_name, pattern, village_count, total_villages, frequency, rank_within_region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} regional pattern frequency records for {pattern_type}")


def save_pattern_tendency(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame, batch_size: int = 10000) -> None:
    """
    Save pattern tendency data.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with tendency analysis columns (must include pattern_type column)
        batch_size: Number of rows to insert per batch
    """
    cursor = conn.cursor()

    # Prepare data for insertion
    df_copy = df.copy()

    # Handle NaN values for optional columns
    df_copy['z_score'] = df_copy['z_score'].where(pd.notna(df_copy['z_score']), None)
    df_copy['rank_overrepresented'] = df_copy['rank_overrepresented'].where(pd.notna(df_copy['rank_overrepresented']), None)
    df_copy['rank_underrepresented'] = df_copy['rank_underrepresented'].where(pd.notna(df_copy['rank_underrepresented']), None)

    # Select and reorder columns
    columns = [
        'run_id', 'pattern_type', 'region_level', 'region_name', 'pattern',
        'village_count', 'total_villages', 'frequency', 'rank_within_region',
        'global_village_count', 'global_frequency',
        'lift', 'log_lift', 'log_odds', 'z_score', 'support_flag',
        'rank_overrepresented', 'rank_underrepresented'
    ]
    data = df_copy[columns].values.tolist()

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO pattern_tendency
            (run_id, pattern_type, region_level, region_name, pattern,
             village_count, total_villages, frequency, rank_within_region,
             global_village_count, global_frequency,
             lift, log_lift, log_odds, z_score, support_flag,
             rank_overrepresented, rank_underrepresented)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} pattern tendency records")


def persist_morphology_results_to_db(
    db_path: str,
    run_id: str,
    results_dir: Path,
    suffix_lengths: list,
    prefix_lengths: list,
    region_levels: list = None,
    batch_size: int = 10000
) -> None:
    """
    Main function to persist morphology analysis results to database.

    Args:
        db_path: Path to SQLite database
        run_id: Run identifier
        results_dir: Directory containing CSV result files
        suffix_lengths: List of suffix n-gram lengths
        prefix_lengths: List of prefix n-gram lengths
        region_levels: List of region levels to process
        batch_size: Number of rows to insert per batch
    """
    import time

    if region_levels is None:
        region_levels = ['city', 'county', 'township']

    logger.info(f"Starting morphology database persistence for run_id={run_id}")
    start_time = time.time()

    # Build list of pattern types
    pattern_types = []
    for n in suffix_lengths:
        pattern_types.append(f'suffix_{n}')
    for n in prefix_lengths:
        pattern_types.append(f'prefix_{n}')

    logger.info(f"Pattern types to persist: {pattern_types}")

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Create tables and indexes
        logger.info("Creating morphology tables...")
        create_morphology_tables(conn)

        # Step 2: Process each pattern type
        for pattern_type in pattern_types:
            logger.info(f"\nProcessing {pattern_type}...")

            # Load global frequency
            global_freq_file = results_dir / f"{pattern_type}_frequency_global.csv"
            if not global_freq_file.exists():
                logger.warning(f"Global frequency file not found: {global_freq_file}")
                continue

            global_freq_df = pd.read_csv(global_freq_file)
            logger.info(f"Loaded {len(global_freq_df)} global frequency records")

            # Save global frequency
            save_pattern_frequency_global(conn, run_id, pattern_type, global_freq_df, batch_size)

            # Load and combine regional frequency files
            regional_freq_dfs = []
            for level in region_levels:
                regional_freq_file = results_dir / f"{pattern_type}_frequency_{level}.csv"
                if regional_freq_file.exists():
                    df = pd.read_csv(regional_freq_file)
                    regional_freq_dfs.append(df)
                    logger.info(f"Loaded {len(df)} {level}-level frequency records")

            if regional_freq_dfs:
                regional_freq_df = pd.concat(regional_freq_dfs, ignore_index=True)
                save_pattern_frequency_regional(conn, run_id, pattern_type, regional_freq_df, batch_size)

            # Load and combine tendency files
            tendency_dfs = []
            for level in region_levels:
                tendency_file = results_dir / f"{pattern_type}_tendency_{level}.csv"
                if tendency_file.exists():
                    df = pd.read_csv(tendency_file)
                    tendency_dfs.append(df)
                    logger.info(f"Loaded {len(df)} {level}-level tendency records")

            if tendency_dfs:
                tendency_df = pd.concat(tendency_dfs, ignore_index=True)
                save_pattern_tendency(conn, run_id, tendency_df, batch_size)

        # Step 3: Create indexes
        logger.info("\nCreating morphology indexes...")
        create_morphology_indexes(conn)

        elapsed = time.time() - start_time
        logger.info(f"Morphology database persistence completed in {elapsed:.2f}s")

    except Exception as e:
        logger.error(f"Error persisting morphology results to database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def write_semantic_vtf_global(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame) -> None:
    """
    Write global semantic VTF to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with columns: category, vtf_count, total_villages, frequency, rank
    """
    cursor = conn.cursor()

    df_copy = df.copy()
    df_copy['run_id'] = run_id

    columns = ['run_id', 'category', 'vtf_count', 'total_villages', 'frequency', 'rank']
    data = df_copy[columns].values.tolist()

    cursor.executemany("""
        INSERT OR REPLACE INTO semantic_vtf_global
        (run_id, category, vtf_count, total_villages, frequency, rank)
        VALUES (?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    logger.info(f"Saved {len(data)} global semantic VTF records for run_id={run_id}")


def write_semantic_vtf_regional(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame) -> None:
    """
    Write regional semantic VTF to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with columns: region_level, region_name, category, vtf_count,
                                    total_villages, frequency, rank_within_region
    """
    cursor = conn.cursor()

    df_copy = df.copy()
    df_copy['run_id'] = run_id

    columns = ['run_id', 'region_level', 'region_name', 'category', 'vtf_count',
               'total_villages', 'frequency', 'rank_within_region']
    data = df_copy[columns].values.tolist()

    cursor.executemany("""
        INSERT OR REPLACE INTO semantic_vtf_regional
        (run_id, region_level, region_name, category, vtf_count, total_villages, frequency, rank_within_region)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    logger.info(f"Saved {len(data)} regional semantic VTF records for run_id={run_id}")


def write_semantic_tendency(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame) -> None:
    """
    Write semantic tendency to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with tendency columns
    """
    cursor = conn.cursor()

    df_copy = df.copy()
    df_copy['run_id'] = run_id

    # Handle NaN values
    df_copy['z_score'] = df_copy['z_score'].where(pd.notna(df_copy['z_score']), None)

    columns = ['run_id', 'region_level', 'region_name', 'category', 'frequency',
               'global_frequency', 'lift', 'log_lift', 'log_odds', 'z_score',
               'vtf_count', 'total_villages', 'support_flag']
    data = df_copy[columns].values.tolist()

    cursor.executemany("""
        INSERT OR REPLACE INTO semantic_tendency
        (run_id, region_level, region_name, category, frequency, global_frequency,
         lift, log_lift, log_odds, z_score, vtf_count, total_villages, support_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    logger.info(f"Saved {len(data)} semantic tendency records for run_id={run_id}")


def write_semantic_indices(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame) -> None:
    """
    Write semantic indices to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with index columns
    """
    cursor = conn.cursor()

    df_copy = df.copy()
    df_copy['run_id'] = run_id

    # Handle NaN values
    df_copy['z_score'] = df_copy['z_score'].where(pd.notna(df_copy['z_score']), None)

    columns = ['run_id', 'region_level', 'region_name', 'category', 'raw_intensity',
               'normalized_index', 'z_score', 'rank_within_province']
    data = df_copy[columns].values.tolist()

    cursor.executemany("""
        INSERT OR REPLACE INTO semantic_indices
        (run_id, region_level, region_name, category, raw_intensity, normalized_index,
         z_score, rank_within_province)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    logger.info(f"Saved {len(data)} semantic indices records for run_id={run_id}")


def create_clustering_tables(conn: sqlite3.Connection) -> None:
    """
    Create clustering result tables if they don't exist.

    Creates 4 tables:
    - region_vectors: Region feature vectors
    - cluster_assignments: Cluster assignments for regions
    - cluster_profiles: Cluster profiles with distinguishing features
    - clustering_metrics: Clustering evaluation metrics

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Table 1: region_vectors
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS region_vectors (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_id TEXT NOT NULL,
            region_name TEXT NOT NULL,
            N_villages INTEGER NOT NULL,
            feature_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY (run_id, region_level, region_id)
        )
    """)

    # Table 2: cluster_assignments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cluster_assignments (
            run_id TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_id TEXT NOT NULL,
            region_name TEXT NOT NULL,
            cluster_id INTEGER NOT NULL,
            algorithm TEXT NOT NULL,
            k INTEGER,
            silhouette_score REAL,
            distance_to_centroid REAL,
            created_at REAL NOT NULL,
            PRIMARY KEY (run_id, region_level, region_id, algorithm)
        )
    """)

    # Table 3: cluster_profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cluster_profiles (
            run_id TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            cluster_id INTEGER NOT NULL,
            cluster_size INTEGER NOT NULL,
            top_features_json TEXT NOT NULL,
            top_semantic_categories_json TEXT NOT NULL,
            top_suffixes_json TEXT,
            representative_regions_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY (run_id, algorithm, cluster_id)
        )
    """)

    # Table 4: clustering_metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clustering_metrics (
            run_id TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            k INTEGER,
            silhouette_score REAL NOT NULL,
            davies_bouldin_index REAL NOT NULL,
            calinski_harabasz_score REAL,
            n_features INTEGER NOT NULL,
            pca_enabled INTEGER NOT NULL,
            pca_n_components INTEGER,
            created_at REAL NOT NULL,
            PRIMARY KEY (run_id, algorithm, k)
        )
    """)

    conn.commit()
    logger.info("Clustering tables created successfully")


def write_region_vectors(conn: sqlite3.Connection, run_id: str, df: pd.DataFrame, batch_size: int = 10000) -> None:
    """
    Write region feature vectors to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        df: DataFrame with region vectors (must include region_id, region_name, N_villages, and feature columns)
        batch_size: Number of rows to insert per batch
    """
    import time

    cursor = conn.cursor()

    # Extract feature columns (exclude metadata columns)
    metadata_cols = ['region_id', 'region_name', 'N_villages']
    feature_cols = [col for col in df.columns if col not in metadata_cols]

    # Prepare data for insertion
    data = []
    for _, row in df.iterrows():
        features = {col: float(row[col]) for col in feature_cols}
        data.append((
            run_id,
            'county',  # Default to county level
            row['region_id'],
            row['region_name'],
            int(row['N_villages']),
            json.dumps(features, ensure_ascii=False),
            time.time()
        ))

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO region_vectors
            (run_id, region_level, region_id, region_name, N_villages, feature_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} region vectors for run_id={run_id}")


def write_cluster_assignments(
    conn: sqlite3.Connection,
    run_id: str,
    region_df: pd.DataFrame,
    labels: np.ndarray,
    distances: np.ndarray,
    algorithm: str,
    k: int,
    silhouette_score: float,
    batch_size: int = 10000
) -> None:
    """
    Write cluster assignments to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        region_df: DataFrame with region_id and region_name
        labels: Cluster assignments array
        distances: Distance to centroid array
        algorithm: Algorithm name (e.g., 'kmeans')
        k: Number of clusters
        silhouette_score: Overall silhouette score
        batch_size: Number of rows to insert per batch
    """
    import time
    import numpy as np

    cursor = conn.cursor()

    # Prepare data for insertion
    data = []
    for i, (_, row) in enumerate(region_df.iterrows()):
        data.append((
            run_id,
            'county',  # Default to county level
            row['region_id'],
            row['region_name'],
            int(labels[i]),
            algorithm,
            k,
            float(silhouette_score),
            float(distances[i]),
            time.time()
        ))

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO cluster_assignments
            (run_id, region_level, region_id, region_name, cluster_id, algorithm, k,
             silhouette_score, distance_to_centroid, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} cluster assignments for run_id={run_id}")


def write_cluster_profiles(conn: sqlite3.Connection, run_id: str, profiles_df: pd.DataFrame, algorithm: str, batch_size: int = 1000) -> None:
    """
    Write cluster profiles to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        profiles_df: DataFrame with cluster profiles
        algorithm: Algorithm name (e.g., 'kmeans')
        batch_size: Number of rows to insert per batch
    """
    import time

    cursor = conn.cursor()

    # Prepare data for insertion
    data = []
    for _, row in profiles_df.iterrows():
        data.append((
            run_id,
            algorithm,
            int(row['cluster_id']),
            int(row['cluster_size']),
            row['top_features_json'],
            row['top_semantic_categories_json'],
            row.get('top_suffixes_json', '[]'),
            row['representative_regions_json'],
            time.time()
        ))

    # Batch insert
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany("""
            INSERT OR REPLACE INTO cluster_profiles
            (run_id, algorithm, cluster_id, cluster_size, top_features_json,
             top_semantic_categories_json, top_suffixes_json, representative_regions_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    logger.info(f"Saved {len(data)} cluster profiles for run_id={run_id}")


def write_clustering_metrics(conn: sqlite3.Connection, run_id: str, metrics_dict: dict) -> None:
    """
    Write clustering metrics to database.

    Args:
        conn: SQLite database connection
        run_id: Run identifier
        metrics_dict: Dictionary with metrics for each k value
    """
    import time

    cursor = conn.cursor()

    # Prepare data for insertion
    data = []
    for result in metrics_dict['results']:
        data.append((
            run_id,
            metrics_dict['algorithm'],
            result['k'],
            float(result['silhouette_score']),
            float(result['davies_bouldin_index']),
            float(result.get('calinski_harabasz_score', 0)),
            metrics_dict['n_features'],
            1 if metrics_dict['pca_enabled'] else 0,
            metrics_dict.get('pca_n_components'),
            time.time()
        ))

    # Insert
    cursor.executemany("""
        INSERT OR REPLACE INTO clustering_metrics
        (run_id, algorithm, k, silhouette_score, davies_bouldin_index,
         calinski_harabasz_score, n_features, pca_enabled, pca_n_components, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    logger.info(f"Saved {len(data)} clustering metrics for run_id={run_id}")


