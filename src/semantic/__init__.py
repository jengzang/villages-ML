"""
Semantic analysis module for village name analysis.

This module provides tools for semantic categorization and analysis:
- Lexicon loading and management
- Virtual Term Frequency (VTF) calculation
- Semantic intensity indices
- Regional semantic tendency analysis
"""

from .lexicon_loader import SemanticLexicon
from .vtf_calculator import VTFCalculator
from .semantic_index import SemanticIndexCalculator

__all__ = [
    'SemanticLexicon',
    'VTFCalculator',
    'SemanticIndexCalculator',
]
