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
        """Load lexicon from JSON file.

        Supports three formats:
        - v1/v2/v3: data['categories'] -> {cat: [chars], ...} (flat)
        - v4: data['categories'] -> {cat: {subcat: [chars]}, ...} (hierarchical)
          + data['multi_label'] -> {char: [cats]}
        - v4_hybrid: data['subcategories'] -> {subcat: [chars], ...} (flat)
        """
        with open(self.lexicon_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.version = data.get('version', 'unknown')
        self.created_at = data.get('created_at', 'unknown')
        self.description = data.get('description', '')

        # Load raw categories
        raw_categories = data.get('categories', {})
        if not raw_categories:
            raw_categories = data.get('subcategories', {})

        if not raw_categories:
            raise ValueError(f"No categories found in lexicon: {self.lexicon_path}")

        # Detect format and normalize
        first_val = next(iter(raw_categories.values()), None)
        if isinstance(first_val, dict):
            # v4 hierarchical: categories -> {parent: {subcat: [chars]}}
            self.categories = raw_categories  # keep parent -> subcategories mapping
            self._flat_categories: Dict[str, List[str]] = {}
            for parent, subcats in raw_categories.items():
                chars = []
                for char_list in subcats.values():
                    chars.extend(char_list)
                self._flat_categories[parent] = chars
            self._multi_label = data.get('multi_label', {})
        else:
            # v1/v2/v3 or v4_hybrid: categories/subcategories -> {cat: [chars]}
            self.categories = raw_categories
            self._flat_categories = self.categories  # same structure
            self._multi_label = {}

    def _build_char_to_category_map(self):
        """Build reverse mapping from character to category for fast lookup."""
        self.char_to_category: Dict[str, str] = {}

        for category, chars in self._flat_categories.items():
            for char in chars:
                if char not in self.char_to_category:
                    self.char_to_category[char] = category

        # Apply multi_label overrides (first listed category wins per current convention)
        if self._multi_label:
            for char, cats in self._multi_label.items():
                if char not in self.char_to_category:
                    self.char_to_category[char] = cats[0]

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

    def _is_hierarchical(self) -> bool:
        """Check if lexicon uses nested {parent: {sub: [chars]}} format."""
        return isinstance(next(iter(self.categories.values()), None), dict)

    def get_lexicon(self, category: str) -> List[str]:
        """
        Get all characters in a category. Supports parent_sub format for v4.

        Args:
            category: Category name (e.g. 'terrain' or 'terrain_peak_ridge')

        Returns:
            List of characters in the category
        """
        if self._is_hierarchical() and '_' in category:
            parent, sub = category.split('_', 1)
            parent_data = self.categories.get(parent, {})
            if isinstance(parent_data, dict):
                return parent_data.get(sub, [])
        return self._flat_categories.get(category, [])

    def list_categories(self) -> List[str]:
        """
        List all available categories.

        Returns:
            List of category names
        """
        return list(self.categories.keys())

    def list_subcategories(self) -> List[str]:
        """
        List all subcategories in parent_sub format.

        For v4 hierarchical lexicons, returns names like
        'terrain_peak_ridge', 'water_river', etc.
        For flat lexicons (v1/v3), returns same as list_categories().

        Returns:
            List of category/subcategory names
        """
        if self._is_hierarchical():
            result = []
            for parent, subcats in self.categories.items():
                for sub in subcats:
                    result.append(f'{parent}_{sub}')
            return result
        return list(self.categories.keys())

    def get_column_names(self, prefix: str = "sem_", suffix: str = "") -> List[str]:
        """
        Get derived column names from category names.

        Args:
            prefix: Column prefix (default 'sem_').
            suffix: Column suffix (default ''). Common: '_pct', '_count', '_intensity'.

        Returns:
            List of column names like ['sem_terrain', 'sem_water', ...].
        """
        return [f"{prefix}{cat}{suffix}" for cat in self.list_categories()]

    def get_category_size(self, category: str) -> int:
        """
        Get number of characters in a category. Supports parent_sub format.

        Args:
            category: Category name

        Returns:
            Number of characters
        """
        if self._is_hierarchical() and '_' in category:
            parent, sub = category.split('_', 1)
            parent_data = self.categories.get(parent, {})
            if isinstance(parent_data, dict):
                return len(parent_data.get(sub, []))
        return len(self._flat_categories.get(category, []))

    def __repr__(self) -> str:
        """String representation."""
        return (f"SemanticLexicon(version={self.version}, "
                f"categories={len(self.categories)}, "
                f"total_chars={len(self.char_to_category)})")
