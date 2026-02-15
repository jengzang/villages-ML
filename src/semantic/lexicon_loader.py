"""
Semantic lexicon loader and manager.

Loads semantic lexicons from JSON files and provides fast character lookup.
"""

import json
from typing import Dict, List, Optional, Set
from pathlib import Path


class SemanticLexicon:
    """Load and manage semantic lexicons for village name analysis."""

    def __init__(self, lexicon_path: str):
        """
        Load lexicon from JSON file.

        Args:
            lexicon_path: Path to semantic lexicon JSON file
        """
        self.lexicon_path = Path(lexicon_path)
        self._load_lexicon()
        self._build_char_to_category_map()

    def _load_lexicon(self):
        """Load lexicon from JSON file."""
        with open(self.lexicon_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.version = data.get('version', 'unknown')
        self.created_at = data.get('created_at', 'unknown')
        self.description = data.get('description', '')
        self.categories = data.get('categories', {})

        # Validate categories
        if not self.categories:
            raise ValueError(f"No categories found in lexicon: {self.lexicon_path}")

    def _build_char_to_category_map(self):
        """Build reverse mapping from character to category for fast lookup."""
        self.char_to_category: Dict[str, str] = {}

        for category, chars in self.categories.items():
            for char in chars:
                # Note: A character can belong to multiple categories
                # We store only the first occurrence for simplicity
                if char not in self.char_to_category:
                    self.char_to_category[char] = category

    def get_category(self, char: str) -> Optional[str]:
        """
        Get semantic category for a character.

        Args:
            char: Chinese character

        Returns:
            Category name or None if not found
        """
        return self.char_to_category.get(char)

    def get_categories(self, chars: List[str]) -> Dict[str, List[str]]:
        """
        Get categories for multiple characters.

        Args:
            chars: List of Chinese characters

        Returns:
            Dict mapping category names to lists of characters
        """
        result: Dict[str, List[str]] = {}

        for char in chars:
            category = self.get_category(char)
            if category:
                if category not in result:
                    result[category] = []
                result[category].append(char)

        return result

    def get_lexicon(self, category: str) -> List[str]:
        """
        Get all characters in a category.

        Args:
            category: Category name

        Returns:
            List of characters in the category
        """
        return self.categories.get(category, [])

    def list_categories(self) -> List[str]:
        """
        List all available categories.

        Returns:
            List of category names
        """
        return list(self.categories.keys())

    def get_category_size(self, category: str) -> int:
        """
        Get number of characters in a category.

        Args:
            category: Category name

        Returns:
            Number of characters
        """
        return len(self.categories.get(category, []))

    def __repr__(self) -> str:
        """String representation."""
        return (f"SemanticLexicon(version={self.version}, "
                f"categories={len(self.categories)}, "
                f"total_chars={len(self.char_to_category)})")
