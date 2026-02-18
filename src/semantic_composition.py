"""
Semantic Composition Analysis for Village Names

This module analyzes how semantic categories combine in multi-character village names.
It builds on Phase 2 (LLM-assisted semantic labeling) to understand:
- Semantic category sequences and patterns
- Modifier-head relationships
- Common semantic compositions
- Semantic conflicts and unusual combinations

Approach: Offline-heavy, accuracy-focused, full dataset
"""

import sqlite3
import json
from typing import List, Dict, Tuple, Set
from collections import Counter, defaultdict
import numpy as np
from scipy import stats


class SemanticCompositionAnalyzer:
    """Analyze semantic composition patterns in village names."""

    def __init__(self, db_path: str = 'data/villages.db', lexicon_path: str = 'data/semantic_lexicon_v2_demo.json'):
        self.db_path = db_path
        self.lexicon_path = lexicon_path
        self.conn = None

        # Semantic categories from lexicon
        self.categories = [
            'water', 'mountain', 'settlement', 'direction',
            'clan', 'symbolic', 'agriculture', 'vegetation', 'infrastructure'
        ]

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def get_character_labels(self) -> Dict[str, str]:
        """
        Load character semantic labels from lexicon file.

        Returns:
            Dictionary mapping character -> category
        """
        import json

        with open(self.lexicon_path, 'r', encoding='utf-8') as f:
            lexicon = json.load(f)

        labels = {}
        categories = lexicon.get('categories', {})

        for category, characters in categories.items():
            for char in characters:
                labels[char] = category

        return labels

    def extract_semantic_sequence(self, village_name: str, char_labels: Dict[str, str]) -> List[str]:
        """
        Extract semantic category sequence from village name.

        For unlabeled characters, use 'other' category.

        Args:
            village_name: Village name
            char_labels: Character -> category mapping

        Returns:
            List of semantic categories in order
        """
        sequence = []

        for char in village_name:
            if '\u4e00' <= char <= '\u9fff':  # Valid Chinese character
                category = char_labels.get(char, 'other')  # Use 'other' for unlabeled
                sequence.append(category)

        return sequence

    def extract_semantic_ngrams(self, sequence: List[str], n: int) -> List[Tuple[str, ...]]:
        """
        Extract semantic n-grams from category sequence.

        Args:
            sequence: List of semantic categories
            n: N-gram size

        Returns:
            List of semantic n-grams (tuples)
        """
        if len(sequence) < n:
            return []

        return [tuple(sequence[i:i+n]) for i in range(len(sequence) - n + 1)]

    def analyze_all_compositions(self) -> Dict[str, Counter]:
        """
        Analyze all semantic compositions in the dataset.

        Returns:
            Dictionary with counters for different n-gram sizes
        """
        char_labels = self.get_character_labels()

        cursor = self.conn.cursor()
        cursor.execute("SELECT 自然村 FROM 广东省自然村")

        bigram_counter = Counter()
        trigram_counter = Counter()
        sequence_counter = Counter()  # Full sequences

        for (village_name,) in cursor:
            if not village_name:
                continue

            sequence = self.extract_semantic_sequence(village_name, char_labels)

            if len(sequence) == 0:
                continue

            # Count full sequence
            sequence_counter[tuple(sequence)] += 1

            # Count bigrams
            bigrams = self.extract_semantic_ngrams(sequence, 2)
            bigram_counter.update(bigrams)

            # Count trigrams
            trigrams = self.extract_semantic_ngrams(sequence, 3)
            trigram_counter.update(trigrams)

        return {
            'bigrams': bigram_counter,
            'trigrams': trigram_counter,
            'sequences': sequence_counter
        }

    def detect_modifier_head_patterns(self, bigrams: Counter) -> List[Dict]:
        """
        Detect modifier-head patterns in semantic bigrams.

        Common patterns:
        - size + X (e.g., 大水, 小山)
        - direction + X (e.g., 东村, 南坑)
        - number + X (e.g., 三水, 五里)
        - X + settlement (e.g., 水村, 山村)

        Args:
            bigrams: Counter of semantic bigrams

        Returns:
            List of modifier-head patterns
        """
        modifier_categories = ['size', 'direction', 'number']
        head_categories = ['water', 'mountain', 'landform', 'vegetation', 'settlement']

        patterns = []

        for (cat1, cat2), count in bigrams.most_common():
            # Modifier + Head pattern
            if cat1 in modifier_categories and cat2 in head_categories:
                patterns.append({
                    'pattern': f'{cat1} + {cat2}',
                    'type': 'modifier_head',
                    'modifier': cat1,
                    'head': cat2,
                    'frequency': count
                })

            # Head + Settlement pattern
            if cat1 in head_categories and cat2 == 'settlement':
                patterns.append({
                    'pattern': f'{cat1} + settlement',
                    'type': 'head_settlement',
                    'head': cat1,
                    'frequency': count
                })

        return patterns

    def detect_semantic_conflicts(self, sequences: Counter, threshold: int = 5) -> List[Dict]:
        """
        Detect unusual or conflicting semantic combinations.

        A combination is considered unusual if:
        - It appears very rarely (< threshold)
        - It contains semantically incompatible categories

        Args:
            sequences: Counter of full semantic sequences
            threshold: Minimum frequency for "normal" combinations

        Returns:
            List of unusual combinations
        """
        conflicts = []

        # Incompatible pairs (heuristic)
        incompatible_pairs = [
            ('water', 'mountain'),  # Water and mountain together is unusual
            ('size', 'number'),     # Size and number together is redundant
        ]

        for sequence, count in sequences.items():
            if count >= threshold:
                continue  # Not unusual

            # Check for incompatible pairs
            for cat1, cat2 in incompatible_pairs:
                if cat1 in sequence and cat2 in sequence:
                    conflicts.append({
                        'sequence': sequence,
                        'frequency': count,
                        'conflict_type': f'{cat1}_vs_{cat2}',
                        'description': f'Contains both {cat1} and {cat2}'
                    })

        return conflicts

    def calculate_pmi(self, bigrams: Counter) -> Dict[Tuple[str, str], float]:
        """
        Calculate Pointwise Mutual Information for semantic bigrams.

        PMI(x, y) = log(P(x, y) / (P(x) * P(y)))

        Args:
            bigrams: Counter of semantic bigrams

        Returns:
            Dictionary mapping bigram -> PMI score
        """
        # Calculate total count
        total = sum(bigrams.values())

        # Calculate unigram frequencies
        unigram_counts = Counter()
        for (cat1, cat2), count in bigrams.items():
            unigram_counts[cat1] += count
            unigram_counts[cat2] += count

        # Calculate PMI
        pmi_scores = {}

        for (cat1, cat2), count in bigrams.items():
            p_xy = count / total
            p_x = unigram_counts[cat1] / (total * 2)  # *2 because each bigram contributes 2 unigrams
            p_y = unigram_counts[cat2] / (total * 2)

            if p_x > 0 and p_y > 0:
                pmi = np.log(p_xy / (p_x * p_y))
                pmi_scores[(cat1, cat2)] = float(pmi)

        return pmi_scores
