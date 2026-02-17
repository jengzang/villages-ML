"""
NLP Module for Advanced Semantic Analysis

Provides character-level embeddings, semantic similarity, clustering,
and LLM-assisted lexicon expansion.
"""

from .embedding_trainer import CharacterEmbeddingTrainer
from .embedding_analyzer import EmbeddingAnalyzer
from .embedding_visualizer import EmbeddingVisualizer
from .embedding_storage import EmbeddingStorage
from .llm_labeler import LLMLabeler, LabelingResult
from .lexicon_expander import LexiconExpander

__all__ = [
    "CharacterEmbeddingTrainer",
    "EmbeddingAnalyzer",
    "EmbeddingVisualizer",
    "EmbeddingStorage",
    "LLMLabeler",
    "LabelingResult",
    "LexiconExpander",
]

__version__ = "0.2.0"
