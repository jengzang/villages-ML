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

from src.config.semantic_roles import (
    MODIFIER_CATEGORIES,
    HEAD_CATEGORIES,
    INCOMPATIBLE_PAIRS,
)


class SemanticCompositionAnalyzer:
    """Analyze semantic composition patterns in village names.

    Pattern-detection role classification is defined in the shared config
    ``src/config/semantic_roles.py`` — the single source of truth for
    :attr:`MODIFIER_CATEGORIES`, :attr:`HEAD_CATEGORIES`, and
    :attr:`INCOMPATIBLE_PAIRS`.  Both this module and any other worker
    that needs semantic role knowledge import from that file.

    When you change a lexicon, update the config; no code changes needed.
    """

    def __init__(self, db_path: str = 'data/villages.db', lexicon_path: str = 'data/semantic_lexicon_v4.json'):
        """
        Initialize SemanticCompositionAnalyzer.

        Defaults to v4 lexicon (53 subcategories) for fine-grained analysis.
        """
        self.db_path = db_path
        self.lexicon_path = lexicon_path
        self.conn = None

        # Note: categories will be loaded from lexicon file
        # v3_expanded has 78 subcategories instead of 9 main categories
        self.categories = None  # Will be loaded from lexicon

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def get_character_labels(self) -> Dict[str, str]:
        """Load character semantic labels from lexicon file.

        Supports three formats:
        - v1/v2/v3: ``lexicon['categories']`` → flat ``{parent: [chars]}``
        - v4: ``lexicon['categories']`` → nested ``{parent: {sub: [chars]}}``
          Characters get ``parent_sub`` labels (e.g. ``water_ditch``).
        - v4_hybrid: ``lexicon['subcategories']`` → flat ``{parent_sub: [chars]}``

        Returns:
            Dictionary mapping character → category label
        """
        import json

        with open(self.lexicon_path, 'r', encoding='utf-8') as f:
            lexicon = json.load(f)

        labels = {}

        categories = lexicon.get('categories', {})
        if not categories:
            categories = lexicon.get('subcategories', {})

        for parent, children in categories.items():
            if isinstance(children, dict):
                # v4 nested format: {parent: {sub: [chars]}}
                for sub, chars in children.items():
                    label = f'{parent}_{sub}'
                    for char in chars:
                        labels[char] = label
            else:
                # v1/v2/v3/v4_hybrid flat format: {category: [chars]}
                for char in children:
                    labels[char] = parent

        return labels

    def get_character_labels_multi(self) -> Dict[str, List[str]]:
        """Load multi-label character mappings from lexicon.

        Reads ``multi_label`` field (v1.3+).  Characters with only one
        category are NOT included — callers fall back to
        :meth:`get_character_labels`.
        """
        import json
        from collections import defaultdict

        with open(self.lexicon_path, 'r', encoding='utf-8') as f:
            lexicon = json.load(f)

        multi = lexicon.get('multi_label')
        if multi is not None:
            return {ch: list(cats) for ch, cats in multi.items()}

        # Fallback: scan for cross-category duplicates
        char_cats: Dict[str, List[str]] = defaultdict(list)

        categories = lexicon.get('categories', {})
        if not categories:
            categories = lexicon.get('subcategories', {})

        for parent, children in categories.items():
            if isinstance(children, dict):
                for sub, chars in children.items():
                    label = f'{parent}_{sub}'
                    for char in chars:
                        char_cats[char].append(label)
            else:
                for char in children:
                    char_cats[char].append(parent)

        return {ch: cats for ch, cats in char_cats.items() if len(cats) > 1}

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

    @staticmethod
    def _parent_of(cat: str) -> str:
        """Extract parent category from subcategory name.

        For 'water_river' returns 'water', for plain 'water' returns 'water'.
        """
        return cat.split('_', 1)[0]

    def detect_modifier_head_patterns(self, bigrams: Counter) -> List[Dict]:
        """Detect modifier-head patterns in semantic bigrams.

        Uses :attr:`MODIFIER_CATEGORIES` and :attr:`HEAD_CATEGORIES` for role
        classification, with :meth:`_parent_of` to resolve subcategory names.
        Works unchanged for both 9-category and 76-subcategory lexicons.

        When adding a new parent category to the lexicon, assign it to
        ``MODIFIER_CATEGORIES`` or ``HEAD_CATEGORIES`` — no code changes needed.
        """
        patterns: List[Dict] = []
        seen_keys: Set[Tuple[str, str]] = set()

        for (cat1, cat2), count in bigrams.most_common():
            p1 = self._parent_of(cat1)
            p2 = self._parent_of(cat2)

            if p1 == 'other' or p2 == 'other':
                continue

            key = (cat1, cat2)
            if key in seen_keys:
                continue

            is_mod1 = p1 in MODIFIER_CATEGORIES
            is_head2 = p2 in HEAD_CATEGORIES
            is_head1 = p1 in HEAD_CATEGORIES

            # Priority 1: Clan + Settlement (culturally significant in Guangdong)
            if p1 == 'clan' and p2 == 'settlement':
                patterns.append({
                    'pattern': f'{cat1} + {cat2}',
                    'type': 'clan_settlement',
                    'modifier': cat1, 'head': cat2,
                    'frequency': count,
                })
                seen_keys.add(key)
                continue

            # Priority 2: Clan + Head
            if p1 == 'clan' and is_head2:
                patterns.append({
                    'pattern': f'{cat1} + {cat2}',
                    'type': 'clan_head',
                    'modifier': cat1, 'head': cat2,
                    'frequency': count,
                })
                seen_keys.add(key)
                continue

            # Priority 3: Symbolic + Head
            if p1 == 'symbolic' and is_head2:
                patterns.append({
                    'pattern': f'{cat1} + {cat2}',
                    'type': 'symbolic_head',
                    'modifier': cat1, 'head': cat2,
                    'frequency': count,
                })
                seen_keys.add(key)
                continue

            # Priority 4: Generic Modifier + Head
            if is_mod1 and is_head2:
                patterns.append({
                    'pattern': f'{cat1} + {cat2}',
                    'type': 'modifier_head',
                    'modifier': cat1, 'head': cat2,
                    'frequency': count,
                })
                seen_keys.add(key)
                continue

            # Priority 5: Head + Settlement
            if is_head1 and p2 == 'settlement':
                patterns.append({
                    'pattern': f'{cat1} + {cat2}',
                    'type': 'head_settlement',
                    'head': cat1, 'modifier': cat2,
                    'frequency': count,
                })
                seen_keys.add(key)
                continue

            # Priority 6: Head + Direction
            if is_head1 and p2 == 'direction':
                patterns.append({
                    'pattern': f'{cat1} + {cat2}',
                    'type': 'head_direction',
                    'head': cat1, 'modifier': cat2,
                    'frequency': count,
                })
                seen_keys.add(key)
                continue

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

        for sequence, count in sequences.items():
            if count >= threshold:
                continue

            parents = {self._parent_of(cat) for cat in sequence}

            for cat1, cat2 in INCOMPATIBLE_PAIRS:
                if cat1 in parents and cat2 in parents:
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
