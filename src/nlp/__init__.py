"""
NLP Module for Advanced Semantic Analysis

Provides character-level embeddings, semantic similarity, and clustering.
"""

from .embedding_trainer import CharacterEmbeddingTrainer
from .embedding_analyzer import EmbeddingAnalyzer
from .embedding_visualizer import EmbeddingVisualizer
from .embedding_storage import EmbeddingStorage

__all__ = [
    "CharacterEmbeddingTrainer",
    "EmbeddingAnalyzer",
    "EmbeddingVisualizer",
    "EmbeddingStorage",
]

__version__ = "0.1.0"
