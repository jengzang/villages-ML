"""
Embedding Storage

Manages database persistence for character embeddings and similarity data.
"""

import sqlite3
import json
import time
import logging
from typing import Dict, List, Tuple, Optional
import numpy as np
import msgpack
from gensim.models import Word2Vec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingStorage:
    """
    Manages storage and retrieval of character embeddings in SQLite database.
    """

    def __init__(self, db_path: str):
        """
        Initialize storage with database path.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Establish database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_tables(self):
        """Create embedding tables if they don't exist."""
        self.connect()
        cursor = self.conn.cursor()

        # Table 1: Embedding runs metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embedding_runs (
                run_id TEXT PRIMARY KEY,
                model_type TEXT NOT NULL,
                vector_size INTEGER NOT NULL,
                window_size INTEGER NOT NULL,
                min_count INTEGER NOT NULL,
                epochs INTEGER NOT NULL,
                vocabulary_size INTEGER NOT NULL,
                corpus_size INTEGER NOT NULL,
                training_time_seconds REAL NOT NULL,
                created_at REAL NOT NULL,
                hyperparameters_json TEXT NOT NULL,
                notes TEXT
            )
        """)

        # Table 2: Character embeddings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS char_embeddings (
                run_id TEXT NOT NULL,
                char TEXT NOT NULL,
                embedding_vector BLOB NOT NULL,
                char_frequency INTEGER NOT NULL,
                PRIMARY KEY (run_id, char),
                FOREIGN KEY (run_id) REFERENCES embedding_runs(run_id)
            )
        """)

        # Table 3: Precomputed similarity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS char_similarity (
                run_id TEXT NOT NULL,
                char1 TEXT NOT NULL,
                char2 TEXT NOT NULL,
                cosine_similarity REAL NOT NULL,
                rank INTEGER NOT NULL,
                PRIMARY KEY (run_id, char1, char2),
                FOREIGN KEY (run_id) REFERENCES embedding_runs(run_id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_char_embeddings_char
            ON char_embeddings(char)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_char_similarity_char1
            ON char_similarity(char1)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_char_similarity_similarity
            ON char_similarity(cosine_similarity DESC)
        """)

        self.conn.commit()
        logger.info("Embedding tables created successfully")

    def save_run_metadata(
        self,
        run_id: str,
        model: Word2Vec,
        training_time: float,
        corpus_size: int,
        hyperparameters: Dict,
        notes: Optional[str] = None,
    ):
        """
        Save embedding run metadata.

        Args:
            run_id: Unique identifier for this run
            model: Trained Word2Vec model
            training_time: Training time in seconds
            corpus_size: Number of villages in corpus
            hyperparameters: Full hyperparameter dictionary
            notes: Optional notes about this run
        """
        self.connect()
        cursor = self.conn.cursor()

        model_type = "word2vec_skipgram" if model.sg == 1 else "word2vec_cbow"

        cursor.execute(
            """
            INSERT OR REPLACE INTO embedding_runs
            (run_id, model_type, vector_size, window_size, min_count, epochs,
             vocabulary_size, corpus_size, training_time_seconds, created_at,
             hyperparameters_json, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                model_type,
                model.wv.vector_size,
                model.window,
                model.min_count,
                model.epochs,
                len(model.wv),
                corpus_size,
                training_time,
                time.time(),
                json.dumps(hyperparameters),
                notes,
            ),
        )

        self.conn.commit()
        logger.info(f"Run metadata saved: {run_id}")

    def save_embeddings(
        self, run_id: str, model: Word2Vec, char_frequencies: Dict[str, int]
    ):
        """
        Save all character embeddings to database.

        Args:
            run_id: Run identifier
            model: Trained Word2Vec model
            char_frequencies: Dictionary mapping char to village count
        """
        self.connect()
        cursor = self.conn.cursor()

        logger.info(f"Saving {len(model.wv)} embeddings...")

        # Prepare batch insert data
        batch_data = []
        for char in model.wv.index_to_key:
            vector = model.wv[char]
            # Serialize vector with msgpack
            vector_blob = msgpack.packb(vector.tolist(), use_bin_type=True)
            frequency = char_frequencies.get(char, 0)
            batch_data.append((run_id, char, vector_blob, frequency))

        # Batch insert
        cursor.executemany(
            """
            INSERT OR REPLACE INTO char_embeddings
            (run_id, char, embedding_vector, char_frequency)
            VALUES (?, ?, ?, ?)
            """,
            batch_data,
        )

        self.conn.commit()
        logger.info(f"Saved {len(batch_data)} embeddings")

    def precompute_similarities(
        self, run_id: str, model: Word2Vec, top_k: int = 50
    ):
        """
        Precompute top-K similar characters for each character.

        Args:
            run_id: Run identifier
            model: Trained Word2Vec model
            top_k: Number of top similar characters to store
        """
        self.connect()
        cursor = self.conn.cursor()

        logger.info(f"Precomputing top-{top_k} similarities for {len(model.wv)} characters...")

        batch_data = []
        batch_size = 1000

        for i, char in enumerate(model.wv.index_to_key):
            try:
                # Get top-K most similar characters
                similar = model.wv.most_similar(char, topn=top_k)

                for rank, (similar_char, similarity) in enumerate(similar, 1):
                    batch_data.append((run_id, char, similar_char, similarity, rank))

                # Batch insert every batch_size records
                if len(batch_data) >= batch_size:
                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO char_similarity
                        (run_id, char1, char2, cosine_similarity, rank)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        batch_data,
                    )
                    self.conn.commit()
                    batch_data = []

                if (i + 1) % 100 == 0:
                    logger.info(f"  Processed {i + 1}/{len(model.wv)} characters")

            except Exception as e:
                logger.warning(f"Error computing similarity for '{char}': {e}")

        # Insert remaining data
        if batch_data:
            cursor.executemany(
                """
                INSERT OR REPLACE INTO char_similarity
                (run_id, char1, char2, cosine_similarity, rank)
                VALUES (?, ?, ?, ?, ?)
                """,
                batch_data,
            )
            self.conn.commit()

        logger.info("Similarity precomputation completed")

    def load_embedding(self, run_id: str, char: str) -> Optional[np.ndarray]:
        """
        Load embedding vector for a specific character.

        Args:
            run_id: Run identifier
            char: Character to load

        Returns:
            Embedding vector or None if not found
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT embedding_vector FROM char_embeddings
            WHERE run_id = ? AND char = ?
            """,
            (run_id, char),
        )

        row = cursor.fetchone()
        if row:
            vector_blob = row[0]
            vector = np.array(msgpack.unpackb(vector_blob, raw=False))
            return vector
        return None

    def load_all_embeddings(self, run_id: str) -> Dict[str, np.ndarray]:
        """
        Load all embeddings for a run.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary mapping char to vector
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT char, embedding_vector FROM char_embeddings
            WHERE run_id = ?
            """,
            (run_id,),
        )

        embeddings = {}
        for row in cursor.fetchall():
            char = row[0]
            vector_blob = row[1]
            vector = np.array(msgpack.unpackb(vector_blob, raw=False))
            embeddings[char] = vector

        logger.info(f"Loaded {len(embeddings)} embeddings for run {run_id}")
        return embeddings

    def get_similar_characters(
        self, run_id: str, char: str, top_k: int = 20
    ) -> List[Tuple[str, float]]:
        """
        Get precomputed similar characters.

        Args:
            run_id: Run identifier
            char: Query character
            top_k: Number of results to return

        Returns:
            List of (character, similarity) tuples
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT char2, cosine_similarity FROM char_similarity
            WHERE run_id = ? AND char1 = ?
            ORDER BY rank
            LIMIT ?
            """,
            (run_id, char, top_k),
        )

        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_run_info(self, run_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific run.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary of run metadata or None if not found
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT * FROM embedding_runs WHERE run_id = ?
            """,
            (run_id,),
        )

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def list_runs(self) -> List[Dict]:
        """
        List all embedding runs.

        Returns:
            List of run metadata dictionaries
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT run_id, model_type, vector_size, vocabulary_size,
                   corpus_size, created_at
            FROM embedding_runs
            ORDER BY created_at DESC
            """
        )

        return [dict(row) for row in cursor.fetchall()]
