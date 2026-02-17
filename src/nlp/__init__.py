"""
NLP Module for Advanced Semantic Analysis

Provides character-level embeddings, semantic similarity, clustering,
LLM-assisted lexicon expansion, and semantic network analysis.
"""

from .embedding_trainer import CharacterEmbeddingTrainer
from .embedding_analyzer import EmbeddingAnalyzer
from .embedding_visualizer import EmbeddingVisualizer
from .embedding_storage import EmbeddingStorage
from .llm_labeler import LLMLabeler, LabelingResult
from .lexicon_expander import LexiconExpander
from .semantic_cooccurrence import SemanticCooccurrence
from .semantic_network import SemanticNetwork

__all__ = [
    "CharacterEmbeddingTrainer",
    "EmbeddingAnalyzer",
    "EmbeddingVisualizer",
    "EmbeddingStorage",
    "LLMLabeler",
    "LabelingResult",
    "LexiconExpander",
    "SemanticCooccurrence",
    "SemanticNetwork",
]

__version__ = "0.3.0"
