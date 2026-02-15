"""
Reproducibility framework for tracking and verifying analysis runs.
"""

import sqlite3
import json
import hashlib
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class RunSnapshot:
    """Capture and store complete run configuration for reproducibility."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize run snapshot manager.

        Args:
            conn: Database connection
        """
        self.conn = conn
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create run_snapshots table if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_snapshots (
                run_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                git_commit_hash TEXT,
                parameters_json TEXT NOT NULL,
                random_state INTEGER,
                environment_json TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                is_reproducible INTEGER DEFAULT 1,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
            )
        """)
        self.conn.commit()

    def capture_snapshot(self, run_id: str, parameters: Dict[str, Any],
                        random_state: Optional[int] = None,
                        data_hash: Optional[str] = None) -> None:
        """
        Capture a snapshot of the current run configuration.

        Args:
            run_id: Run identifier
            parameters: Run parameters
            random_state: Random seed used
            data_hash: Hash of input data
        """
        # Get git commit hash
        git_commit = self._get_git_commit()

        # Capture environment
        environment = {
            'python_version': sys.version,
            'platform': sys.platform,
            'timestamp': datetime.now().isoformat()
        }

        # Calculate data hash if not provided
        if data_hash is None:
            data_hash = self._calculate_data_hash()

        # Store snapshot
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO run_snapshots
            (run_id, created_at, git_commit_hash, parameters_json, random_state,
             environment_json, data_hash, is_reproducible)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            run_id,
            datetime.now().timestamp(),
            git_commit,
            json.dumps(parameters, ensure_ascii=False),
            random_state,
            json.dumps(environment, ensure_ascii=False),
            data_hash
        ))
        self.conn.commit()

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return None

    def _calculate_data_hash(self) -> str:
        """Calculate MD5 hash of the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM 广东省自然村")
        count = cursor.fetchone()[0]
        
        # Use count as a simple hash (for performance)
        # In production, could hash actual data
        return hashlib.md5(str(count).encode()).hexdigest()

    def get_snapshot(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve snapshot for a run.

        Args:
            run_id: Run identifier

        Returns:
            Snapshot data or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT created_at, git_commit_hash, parameters_json, random_state,
                   environment_json, data_hash, is_reproducible
            FROM run_snapshots
            WHERE run_id = ?
        """, (run_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return {
            'run_id': run_id,
            'created_at': row[0],
            'git_commit_hash': row[1],
            'parameters': json.loads(row[2]),
            'random_state': row[3],
            'environment': json.loads(row[4]),
            'data_hash': row[5],
            'is_reproducible': bool(row[6])
        }


class ResultVersioning:
    """Manage semantic versioning of analysis results."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize result versioning manager.

        Args:
            conn: Database connection
        """
        self.conn = conn

    def compare_runs(self, run_id1: str, run_id2: str) -> Dict[str, Any]:
        """
        Compare two runs and identify differences.

        Args:
            run_id1: First run identifier
            run_id2: Second run identifier

        Returns:
            Comparison results
        """
        snapshot_mgr = RunSnapshot(self.conn)
        snap1 = snapshot_mgr.get_snapshot(run_id1)
        snap2 = snapshot_mgr.get_snapshot(run_id2)

        if not snap1 or not snap2:
            raise ValueError("One or both runs not found")

        # Compare parameters
        param_diff = self._compare_dicts(snap1['parameters'], snap2['parameters'])

        # Compare data hashes
        data_changed = snap1['data_hash'] != snap2['data_hash']

        # Compare top results
        cursor = self.conn.cursor()
        
        # Get top 100 characters from each run
        cursor.execute("""
            SELECT char FROM global_frequency
            WHERE run_id = ?
            ORDER BY rank
            LIMIT 100
        """, (run_id1,))
        chars1 = set(row[0] for row in cursor.fetchall())

        cursor.execute("""
            SELECT char FROM global_frequency
            WHERE run_id = ?
            ORDER BY rank
            LIMIT 100
        """, (run_id2,))
        chars2 = set(row[0] for row in cursor.fetchall())

        overlap = len(chars1 & chars2) / 100.0

        return {
            'run_id1': run_id1,
            'run_id2': run_id2,
            'parameter_differences': param_diff,
            'data_changed': data_changed,
            'top100_overlap': overlap,
            'git_commit_same': snap1['git_commit_hash'] == snap2['git_commit_hash']
        }

    def _compare_dicts(self, dict1: Dict, dict2: Dict) -> Dict[str, Any]:
        """Compare two dictionaries and return differences."""
        diff = {}
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in all_keys:
            val1 = dict1.get(key)
            val2 = dict2.get(key)
            if val1 != val2:
                diff[key] = {'run1': val1, 'run2': val2}
        
        return diff


class DeterminismValidator:
    """Validate reproducibility and determinism of analysis runs."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize determinism validator.

        Args:
            conn: Database connection
        """
        self.conn = conn

    def validate_run(self, run_id: str) -> bool:
        """
        Validate that a run is reproducible.

        Args:
            run_id: Run identifier

        Returns:
            True if run is reproducible
        """
        snapshot_mgr = RunSnapshot(self.conn)
        snapshot = snapshot_mgr.get_snapshot(run_id)

        if not snapshot:
            return False

        # Check if all required fields are present
        required_fields = ['parameters', 'data_hash', 'environment']
        for field in required_fields:
            if field not in snapshot or snapshot[field] is None:
                return False

        # Check if random_state is set (for deterministic operations)
        if snapshot.get('random_state') is None:
            # Mark as potentially non-reproducible
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE run_snapshots
                SET is_reproducible = 0
                WHERE run_id = ?
            """, (run_id,))
            self.conn.commit()
            return False

        return True

    def calculate_result_checksum(self, run_id: str) -> str:
        """
        Calculate checksum of run results for verification.

        Args:
            run_id: Run identifier

        Returns:
            MD5 checksum of results
        """
        cursor = self.conn.cursor()
        
        # Get top 1000 characters and their counts
        cursor.execute("""
            SELECT char, village_count
            FROM global_frequency
            WHERE run_id = ?
            ORDER BY rank
            LIMIT 1000
        """, (run_id,))
        
        results = cursor.fetchall()
        result_str = ''.join(f"{char}:{count}" for char, count in results)
        
        return hashlib.md5(result_str.encode('utf-8')).hexdigest()
