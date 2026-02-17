"""
N-gram Structure Analysis for Village Names

This module provides functionality for extracting and analyzing character n-grams
(bigrams and trigrams) from village names. It supports:
- N-gram extraction with position awareness
- Frequency statistics (global and regional)
- Tendency analysis (lift, z-score)
- Structural pattern identification (prefix, suffix, templates)

All analysis follows the offline-heavy, accuracy-focused approach:
- Full dataset (no sampling)
- Exact algorithms
- Statistical significance testing
"""

import sqlite3
import re
from typing import List, Tuple, Dict, Set
from collections import Counter, defaultdict
import numpy as np
from scipy import stats


class NgramExtractor:
    """Extract n-grams from village names with position awareness."""

    def __init__(self, db_path: str = 'data/villages.db'):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    @staticmethod
    def is_valid_chinese(char: str) -> bool:
        """Check if character is valid Chinese."""
        return '\u4e00' <= char <= '\u9fff'

    @staticmethod
    def extract_ngrams(text: str, n: int) -> List[str]:
        """
        Extract n-grams from text.

        Args:
            text: Input text (village name)
            n: N-gram size (2 for bigram, 3 for trigram)

        Returns:
            List of n-grams
        """
        # Filter to valid Chinese characters only
        chars = [c for c in text if NgramExtractor.is_valid_chinese(c)]

        if len(chars) < n:
            return []

        return [''.join(chars[i:i+n]) for i in range(len(chars) - n + 1)]

    @staticmethod
    def extract_positional_ngrams(text: str, n: int) -> Dict[str, List[str]]:
        """
        Extract n-grams with position information.

        Args:
            text: Input text (village name)
            n: N-gram size

        Returns:
            Dictionary with keys: 'prefix', 'suffix', 'middle', 'all'
        """
        chars = [c for c in text if NgramExtractor.is_valid_chinese(c)]

        if len(chars) < n:
            return {'prefix': [], 'suffix': [], 'middle': [], 'all': []}

        all_ngrams = [''.join(chars[i:i+n]) for i in range(len(chars) - n + 1)]

        result = {
            'all': all_ngrams,
            'prefix': [all_ngrams[0]] if all_ngrams else [],
            'suffix': [all_ngrams[-1]] if all_ngrams else [],
            'middle': all_ngrams[1:-1] if len(all_ngrams) > 2 else []
        }

        return result

    def extract_all_ngrams(self, n: int = 2) -> Dict[str, Counter]:
        """
        Extract all n-grams from the database.

        Args:
            n: N-gram size (2 for bigram, 3 for trigram)

        Returns:
            Dictionary with counters for different positions
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT 自然村 FROM 广东省自然村")

        all_counter = Counter()
        prefix_counter = Counter()
        suffix_counter = Counter()
        middle_counter = Counter()

        for (village_name,) in cursor:
            if not village_name:
                continue

            positional = self.extract_positional_ngrams(village_name, n)

            all_counter.update(positional['all'])
            prefix_counter.update(positional['prefix'])
            suffix_counter.update(positional['suffix'])
            middle_counter.update(positional['middle'])

        return {
            'all': all_counter,
            'prefix': prefix_counter,
            'suffix': suffix_counter,
            'middle': middle_counter
        }

    def extract_regional_ngrams(self, n: int = 2, level: str = '市级') -> Dict[str, Dict[str, Counter]]:
        """
        Extract n-grams by region.

        Args:
            n: N-gram size
            level: Regional level ('市级', '县区级', '乡镇')

        Returns:
            Dictionary mapping region -> position -> Counter
        """
        cursor = self.conn.cursor()

        # Map level to column index to avoid encoding issues
        level_to_index = {
            '市级': 0,
            '县区级': 1,
            '乡镇': 2
        }

        col_index = level_to_index.get(level, 0)

        # Query using column index
        cursor.execute("SELECT * FROM 广东省自然村")

        regional_data = defaultdict(lambda: {
            'all': Counter(),
            'prefix': Counter(),
            'suffix': Counter(),
            'middle': Counter()
        })

        for row in cursor:
            region = row[col_index]  # Get region by index
            village_name = row[4]     # 自然村 is at index 4

            if not region or not village_name:
                continue

            positional = self.extract_positional_ngrams(village_name, n)

            regional_data[region]['all'].update(positional['all'])
            regional_data[region]['prefix'].update(positional['prefix'])
            regional_data[region]['suffix'].update(positional['suffix'])
            regional_data[region]['middle'].update(positional['middle'])

        return dict(regional_data)


class NgramAnalyzer:
    """Analyze n-gram frequencies and tendencies."""

    def __init__(self, db_path: str = 'data/villages.db'):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def calculate_tendency(
        self,
        regional_count: int,
        regional_total: int,
        global_count: int,
        global_total: int
    ) -> Dict[str, float]:
        """
        Calculate tendency scores for an n-gram in a region.

        Args:
            regional_count: Count in specific region
            regional_total: Total n-grams in region
            global_count: Count globally
            global_total: Total n-grams globally

        Returns:
            Dictionary with lift, log_odds, z_score
        """
        # Avoid division by zero
        if regional_total == 0 or global_total == 0 or global_count == 0:
            return {'lift': 0.0, 'log_odds': 0.0, 'z_score': 0.0}

        # Lift (observed / expected)
        regional_freq = regional_count / regional_total
        global_freq = global_count / global_total
        lift = regional_freq / global_freq if global_freq > 0 else 0.0

        # Log-odds ratio
        regional_odds = regional_count / (regional_total - regional_count + 1)
        global_odds = global_count / (global_total - global_count + 1)
        log_odds = np.log(regional_odds / global_odds) if global_odds > 0 else 0.0

        # Z-score
        expected = regional_total * global_freq
        if expected > 0:
            variance = expected * (1 - global_freq)
            z_score = (regional_count - expected) / np.sqrt(variance) if variance > 0 else 0.0
        else:
            z_score = 0.0

        return {
            'lift': float(lift),
            'log_odds': float(log_odds),
            'z_score': float(z_score)
        }

    def calculate_significance(
        self,
        regional_count: int,
        regional_total: int,
        global_count: int,
        global_total: int
    ) -> Dict[str, float]:
        """
        Calculate statistical significance using chi-square test.

        Returns:
            Dictionary with chi2, p_value, cramers_v
        """
        # Contingency table
        # [[regional_count, regional_other],
        #  [other_regions_count, other_regions_other]]
        regional_other = regional_total - regional_count
        other_regions_count = global_count - regional_count
        other_regions_total = global_total - regional_total
        other_regions_other = other_regions_total - other_regions_count

        contingency = np.array([
            [regional_count, regional_other],
            [other_regions_count, other_regions_other]
        ])

        # Chi-square test
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

        # Cramer's V (effect size)
        n = contingency.sum()
        cramers_v = np.sqrt(chi2 / n) if n > 0 else 0.0

        return {
            'chi2': float(chi2),
            'p_value': float(p_value),
            'cramers_v': float(cramers_v)
        }


class StructuralPatternDetector:
    """Detect structural patterns in village names."""

    def __init__(self, db_path: str = 'data/villages.db'):
        self.db_path = db_path

    def detect_templates(self, ngrams: Counter, min_freq: int = 100) -> List[Dict]:
        """
        Detect common templates (e.g., "XX村", "大XX").

        Args:
            ngrams: Counter of n-grams
            min_freq: Minimum frequency threshold

        Returns:
            List of template patterns with frequencies
        """
        templates = []

        for ngram, count in ngrams.most_common():
            if count < min_freq:
                break

            # Check if it's a potential template
            # For bigrams: check if first or last char is very common
            if len(ngram) == 2:
                first_char, second_char = ngram[0], ngram[1]

                # Suffix template (e.g., "X村", "X坑")
                if self._is_common_suffix(second_char, ngrams):
                    templates.append({
                        'pattern': f'X{second_char}',
                        'type': 'suffix',
                        'example': ngram,
                        'frequency': count
                    })

                # Prefix template (e.g., "大X", "新X")
                if self._is_common_prefix(first_char, ngrams):
                    templates.append({
                        'pattern': f'{first_char}X',
                        'type': 'prefix',
                        'example': ngram,
                        'frequency': count
                    })

        return templates

    def _is_common_suffix(self, char: str, ngrams: Counter, threshold: int = 50) -> bool:
        """Check if character is a common suffix."""
        # Count how many different n-grams end with this character
        count = sum(1 for ngram in ngrams if ngram.endswith(char))
        return count >= threshold

    def _is_common_prefix(self, char: str, ngrams: Counter, threshold: int = 50) -> bool:
        """Check if character is a common prefix."""
        # Count how many different n-grams start with this character
        count = sum(1 for ngram in ngrams if ngram.startswith(char))
        return count >= threshold
