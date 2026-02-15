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
