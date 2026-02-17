"""
Character Embedding Trainer

Trains Word2Vec embeddings on village name character sequences.
"""

import time
import logging
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from gensim.models import Word2Vec
from gensim.models.callbacks import CallbackAny2Vec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingCallback(CallbackAny2Vec):
    """Callback to log training progress."""

    def __init__(self):
        self.epoch = 0
        self.start_time = time.time()

    def on_epoch_end(self, model):
        elapsed = time.time() - self.start_time
        self.epoch += 1
        logger.info(f"Epoch {self.epoch} completed in {elapsed:.2f}s")
        self.start_time = time.time()


class CharacterEmbeddingTrainer:
    """
    Trains Word2Vec embeddings on character sequences from village names.

    Treats each village name as a "sentence" of characters, capturing
    co-occurrence patterns to learn distributional semantics.
    """

    def __init__(
        self,
        vector_size: int = 100,
        window: int = 3,
        min_count: int = 2,
        sg: int = 1,  # 1=skip-gram, 0=CBOW
        epochs: int = 15,
        workers: int = 4,
        negative: int = 5,
        seed: int = 42,
    ):
        """
        Initialize trainer with hyperparameters.

        Args:
            vector_size: Dimensionality of embeddings (50-150 recommended)
            window: Context window size (2-5 for short village names)
            min_count: Minimum character frequency to include
            sg: Training algorithm (1=skip-gram, 0=CBOW)
            epochs: Number of training epochs
            workers: Number of parallel workers
            negative: Number of negative samples
            seed: Random seed for reproducibility
        """
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.sg = sg
        self.epochs = epochs
        self.workers = workers
        self.negative = negative
        self.seed = seed

    def is_valid_chinese_char(self, char: str) -> bool:
        """Check if character is a valid Chinese character."""
        if not char:
            return False
        code = ord(char)
        # CJK Unified Ideographs: 4E00-9FFF
        # CJK Extension A: 3400-4DBF
        return (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF)

    def prepare_corpus(
        self, villages_df: pd.DataFrame, village_col: str = "自然村"
    ) -> Tuple[List[List[str]], Dict[str, int]]:
        """
        Convert village names to character sequences.

        Args:
            villages_df: DataFrame with village names
            village_col: Column name containing village names

        Returns:
            Tuple of (corpus, char_frequencies)
            - corpus: List of character sequences
            - char_frequencies: Dict mapping char to village count
        """
        logger.info(f"Preparing corpus from {len(villages_df)} villages...")

        corpus = []
        char_frequencies = {}

        for village_name in villages_df[village_col]:
            if pd.isna(village_name) or not village_name:
                continue

            # Extract valid Chinese characters
            chars = [c for c in village_name if self.is_valid_chinese_char(c)]

            if not chars:
                continue

            # Deduplicate characters within village name (per project rules)
            unique_chars = list(dict.fromkeys(chars))  # Preserves order
            corpus.append(unique_chars)

            # Count character frequencies (number of villages containing char)
            for char in set(unique_chars):
                char_frequencies[char] = char_frequencies.get(char, 0) + 1

        logger.info(f"Corpus prepared: {len(corpus)} sequences, {len(char_frequencies)} unique characters")
        return corpus, char_frequencies

    def train(self, corpus: List[List[str]]) -> Word2Vec:
        """
        Train Word2Vec model on character corpus.

        Args:
            corpus: List of character sequences

        Returns:
            Trained Word2Vec model
        """
        logger.info("Training Word2Vec model...")
        logger.info(f"Hyperparameters: vector_size={self.vector_size}, window={self.window}, "
                   f"min_count={self.min_count}, sg={self.sg}, epochs={self.epochs}")

        start_time = time.time()

        model = Word2Vec(
            sentences=corpus,
            vector_size=self.vector_size,
            window=self.window,
            min_count=self.min_count,
            sg=self.sg,
            workers=self.workers,
            negative=self.negative,
            seed=self.seed,
            epochs=self.epochs,
            callbacks=[TrainingCallback()],
        )

        training_time = time.time() - start_time
        logger.info(f"Training completed in {training_time:.2f}s")
        logger.info(f"Vocabulary size: {len(model.wv)}")

        return model

    def evaluate_model(self, model: Word2Vec) -> Dict:
        """
        Evaluate embedding quality.

        Args:
            model: Trained Word2Vec model

        Returns:
            Dictionary of evaluation metrics
        """
        logger.info("Evaluating model...")

        metrics = {
            "vocabulary_size": len(model.wv),
            "vector_size": model.wv.vector_size,
        }

        # Check for NaN or inf values
        has_nan = np.any(np.isnan(model.wv.vectors))
        has_inf = np.any(np.isinf(model.wv.vectors))
        metrics["has_nan"] = has_nan
        metrics["has_inf"] = has_inf

        if has_nan or has_inf:
            logger.warning("Model contains NaN or inf values!")

        # Sample similarity queries
        test_chars = ["田", "山", "水", "村", "东"]
        available_test_chars = [c for c in test_chars if c in model.wv]

        if available_test_chars:
            logger.info("\nSample similarity queries:")
            for char in available_test_chars[:3]:
                try:
                    similar = model.wv.most_similar(char, topn=5)
                    logger.info(f"  {char}: {', '.join([f'{c}({s:.3f})' for c, s in similar])}")
                except Exception as e:
                    logger.warning(f"  {char}: Error - {e}")

        return metrics

    def save_model(self, model: Word2Vec, path: str):
        """
        Save trained model to disk.

        Args:
            model: Trained Word2Vec model
            path: Output file path
        """
        logger.info(f"Saving model to {path}")
        model.save(path)

        # Also save KeyedVectors for faster loading
        kv_path = path.replace(".model", ".kv")
        model.wv.save(kv_path)
        logger.info(f"KeyedVectors saved to {kv_path}")

    def get_hyperparameters(self) -> Dict:
        """Get hyperparameters as dictionary."""
        return {
            "vector_size": self.vector_size,
            "window": self.window,
            "min_count": self.min_count,
            "sg": self.sg,
            "epochs": self.epochs,
            "workers": self.workers,
            "negative": self.negative,
            "seed": self.seed,
        }
