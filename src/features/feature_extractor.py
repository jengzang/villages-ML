"""
Village feature extraction module.

Extracts semantic tags, morphology patterns, and data quality flags from village names.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class VillageFeatureExtractor:
    """Extract features from village names for materialization."""

    def __init__(self, lexicon_path: str):
        """
        Initialize feature extractor.

        Args:
            lexicon_path: Path to semantic lexicon JSON file
        """
        self.lexicon_path = Path(lexicon_path)
        self._load_lexicon()

    def _load_lexicon(self):
        """Load semantic lexicon."""
        from src.semantic.lexicon_loader import SemanticLexicon
        self.lexicon = SemanticLexicon(str(self.lexicon_path))
        self.categories = self.lexicon.list_categories()
        logger.info(f"Loaded lexicon with {len(self.categories)} categories")

    def extract_semantic_tags(self, village_name: str) -> Dict[str, int]:
        """
        Extract semantic tags from village name.

        Args:
            village_name: Village name string

        Returns:
            Dict mapping category names to binary flags (0 or 1)
        """
        # Initialize all categories to 0
        tags = {f"sem_{cat}": 0 for cat in self.categories}

        # Handle None or empty names
        if not village_name:
            return tags

        # Check each character in village name
        for char in village_name:
            category = self.lexicon.get_category(char)
            if category:
                tags[f"sem_{category}"] = 1

        return tags

    def extract_morphology_features(self, village_name: str) -> Dict[str, Optional[str]]:
        """
        Extract morphology features (suffixes and prefixes).

        Args:
            village_name: Village name string

        Returns:
            Dict with suffix_1, suffix_2, suffix_3, prefix_1, prefix_2, prefix_3
        """
        features = {
            'suffix_1': None,
            'suffix_2': None,
            'suffix_3': None,
            'prefix_1': None,
            'prefix_2': None,
            'prefix_3': None
        }

        if not village_name:
            return features

        name_len = len(village_name)

        # Extract suffixes
        if name_len >= 1:
            features['suffix_1'] = village_name[-1]
        if name_len >= 2:
            features['suffix_2'] = village_name[-2:]
        if name_len >= 3:
            features['suffix_3'] = village_name[-3:]

        # Extract prefixes
        if name_len >= 1:
            features['prefix_1'] = village_name[0]
        if name_len >= 2:
            features['prefix_2'] = village_name[:2]
        if name_len >= 3:
            features['prefix_3'] = village_name[:3]

        return features

    def extract_data_quality_flags(self, village_name: str) -> Dict[str, int]:
        """
        Extract data quality flags.

        Args:
            village_name: Village name string

        Returns:
            Dict with quality flags
        """
        flags = {
            'name_length': len(village_name) if village_name else 0,
            'has_valid_chars': 1 if village_name and len(village_name) > 0 else 0
        }

        return flags

    def extract_all_features(self, village_name: str) -> Dict[str, any]:
        """
        Extract all features from village name.

        Args:
            village_name: Village name string

        Returns:
            Dict with all features combined
        """
        features = {}

        # Semantic tags
        features.update(self.extract_semantic_tags(village_name))

        # Morphology features
        features.update(self.extract_morphology_features(village_name))

        # Data quality flags
        features.update(self.extract_data_quality_flags(village_name))

        return features

    def extract_batch(self, villages_df: pd.DataFrame, village_name_col: str = '自然村') -> pd.DataFrame:
        """
        Extract features for a batch of villages.

        Args:
            villages_df: DataFrame with village data
            village_name_col: Column name containing village names

        Returns:
            DataFrame with extracted features
        """
        logger.info(f"Extracting features for {len(villages_df)} villages")

        # Extract features for each village
        features_list = []
        for idx, row in villages_df.iterrows():
            village_name = row[village_name_col]
            features = self.extract_all_features(village_name)
            features_list.append(features)

        # Convert to DataFrame
        features_df = pd.DataFrame(features_list)

        logger.info(f"Extracted {len(features_df.columns)} features")

        return features_df

