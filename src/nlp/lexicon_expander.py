"""
Lexicon Expander

Expands semantic lexicon using LLM-generated labels and embedding validation.
"""

import json
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LexiconExpander:
    """
    Expands semantic lexicon with LLM labels and embedding validation.
    """

    def __init__(
        self,
        existing_lexicon: Dict[str, List[str]],
        embeddings: Optional[Dict[str, np.ndarray]] = None,
    ):
        """
        Initialize lexicon expander.

        Args:
            existing_lexicon: Current lexicon {category: [chars]}
            embeddings: Character embeddings for validation
        """
        self.lexicon = existing_lexicon.copy()
        self.embeddings = embeddings
        self.new_categories = {}
        self.validation_results = {}

    def add_llm_labels(
        self,
        llm_results: List,
        min_confidence: float = 0.7,
        validate_with_embeddings: bool = True,
        similarity_threshold: float = 0.3,
    ) -> Dict[str, List[str]]:
        """
        Add LLM-generated labels to lexicon.

        Args:
            llm_results: List of LabelingResult objects
            min_confidence: Minimum confidence to accept label
            validate_with_embeddings: Use embeddings to validate
            similarity_threshold: Minimum similarity to category

        Returns:
            Updated lexicon
        """
        logger.info(f"Processing {len(llm_results)} LLM labels...")

        accepted = 0
        rejected_confidence = 0
        rejected_similarity = 0
        new_categories_found = 0

        for result in llm_results:
            # Check confidence
            if result.confidence < min_confidence:
                rejected_confidence += 1
                logger.debug(f"Rejected '{result.char}': low confidence ({result.confidence:.2f})")
                continue

            # Validate with embeddings if available
            if validate_with_embeddings and self.embeddings:
                is_valid, avg_similarity = self._validate_with_embeddings(
                    result.char,
                    result.category,
                    similarity_threshold
                )

                if not is_valid:
                    rejected_similarity += 1
                    logger.debug(f"Rejected '{result.char}': low similarity to '{result.category}' ({avg_similarity:.3f})")
                    continue

                self.validation_results[result.char] = {
                    "category": result.category,
                    "avg_similarity": avg_similarity,
                    "confidence": result.confidence,
                }

            # Handle new categories
            if result.is_new_category:
                if result.category not in self.new_categories:
                    self.new_categories[result.category] = []
                    new_categories_found += 1
                self.new_categories[result.category].append(result.char)
                logger.info(f"New category '{result.category}' suggested for '{result.char}'")

            # Add to lexicon
            if result.category not in self.lexicon:
                self.lexicon[result.category] = []

            if result.char not in self.lexicon[result.category]:
                self.lexicon[result.category].append(result.char)
                accepted += 1

        logger.info(f"Added {accepted} characters to lexicon")
        logger.info(f"Rejected: {rejected_confidence} (confidence), {rejected_similarity} (similarity)")
        logger.info(f"New categories found: {new_categories_found}")

        return self.lexicon

    def _validate_with_embeddings(
        self,
        char: str,
        category: str,
        threshold: float,
    ) -> Tuple[bool, float]:
        """
        Validate character-category assignment using embeddings.

        Args:
            char: Character to validate
            category: Assigned category
            threshold: Minimum average similarity

        Returns:
            (is_valid, average_similarity)
        """
        if char not in self.embeddings:
            logger.warning(f"Character '{char}' not in embeddings")
            return True, 0.0  # Accept if no embedding available

        if category not in self.lexicon:
            # New category, can't validate
            return True, 0.0

        category_chars = [c for c in self.lexicon[category] if c in self.embeddings]
        if not category_chars:
            return True, 0.0

        # Compute average similarity to category members
        char_vec = self.embeddings[char]
        similarities = []

        for cat_char in category_chars:
            cat_vec = self.embeddings[cat_char]
            # Cosine similarity
            sim = np.dot(char_vec, cat_vec) / (np.linalg.norm(char_vec) * np.linalg.norm(cat_vec))
            similarities.append(sim)

        avg_similarity = np.mean(similarities)
        is_valid = avg_similarity >= threshold

        return is_valid, float(avg_similarity)

    def merge_categories(
        self,
        category1: str,
        category2: str,
        new_name: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        Merge two categories.

        Args:
            category1: First category
            category2: Second category
            new_name: Name for merged category (default: category1)

        Returns:
            Updated lexicon
        """
        if category1 not in self.lexicon or category2 not in self.lexicon:
            logger.error(f"Cannot merge: category not found")
            return self.lexicon

        merged_name = new_name or category1
        merged_chars = list(set(self.lexicon[category1] + self.lexicon[category2]))

        self.lexicon[merged_name] = merged_chars

        if merged_name != category1:
            del self.lexicon[category1]
        if merged_name != category2:
            del self.lexicon[category2]

        logger.info(f"Merged '{category1}' and '{category2}' into '{merged_name}' ({len(merged_chars)} chars)")

        return self.lexicon

    def split_category(
        self,
        category: str,
        char_groups: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """
        Split a category into multiple categories.

        Args:
            category: Category to split
            char_groups: {new_category_name: [chars]}

        Returns:
            Updated lexicon
        """
        if category not in self.lexicon:
            logger.error(f"Category '{category}' not found")
            return self.lexicon

        # Remove original category
        del self.lexicon[category]

        # Add new categories
        for new_cat, chars in char_groups.items():
            if new_cat not in self.lexicon:
                self.lexicon[new_cat] = []
            self.lexicon[new_cat].extend(chars)

        logger.info(f"Split '{category}' into {len(char_groups)} categories")

        return self.lexicon

    def find_similar_categories(
        self,
        min_similarity: float = 0.5,
        top_k: int = 5,
    ) -> List[Tuple[str, str, float]]:
        """
        Find pairs of similar categories (potential merges).

        Args:
            min_similarity: Minimum average similarity
            top_k: Number of top pairs to return

        Returns:
            List of (category1, category2, similarity) tuples
        """
        if not self.embeddings:
            logger.error("Embeddings required for similarity analysis")
            return []

        category_pairs = []
        categories = list(self.lexicon.keys())

        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                # Get characters with embeddings
                chars1 = [c for c in self.lexicon[cat1] if c in self.embeddings]
                chars2 = [c for c in self.lexicon[cat2] if c in self.embeddings]

                if not chars1 or not chars2:
                    continue

                # Compute average cross-category similarity
                similarities = []
                for c1 in chars1[:20]:  # Sample to avoid O(n^2) explosion
                    for c2 in chars2[:20]:
                        vec1 = self.embeddings[c1]
                        vec2 = self.embeddings[c2]
                        sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                        similarities.append(sim)

                avg_sim = np.mean(similarities)

                if avg_sim >= min_similarity:
                    category_pairs.append((cat1, cat2, float(avg_sim)))

        # Sort by similarity descending
        category_pairs.sort(key=lambda x: x[2], reverse=True)

        return category_pairs[:top_k]

    def get_coverage_stats(self, all_chars: Set[str]) -> Dict:
        """
        Compute coverage statistics.

        Args:
            all_chars: Set of all characters in corpus

        Returns:
            Dictionary of statistics
        """
        lexicon_chars = set()
        for chars in self.lexicon.values():
            lexicon_chars.update(chars)

        covered = lexicon_chars & all_chars
        uncovered = all_chars - lexicon_chars

        stats = {
            "total_chars": len(all_chars),
            "covered_chars": len(covered),
            "uncovered_chars": len(uncovered),
            "coverage_rate": len(covered) / len(all_chars) if all_chars else 0,
            "lexicon_size": len(lexicon_chars),
            "num_categories": len(self.lexicon),
            "avg_category_size": len(lexicon_chars) / len(self.lexicon) if self.lexicon else 0,
        }

        return stats

    def export_lexicon(
        self,
        output_path: str,
        version: str = "2.0.0",
        description: str = "Expanded lexicon with LLM labels",
    ):
        """
        Export lexicon to JSON file.

        Args:
            output_path: Output file path
            version: Version string
            description: Description
        """
        lexicon_data = {
            "version": version,
            "created_at": "2026-02-17",
            "description": description,
            "categories": self.lexicon,
            "new_categories": self.new_categories,
            "validation_results": self.validation_results,
            "statistics": {
                "num_categories": len(self.lexicon),
                "total_characters": sum(len(chars) for chars in self.lexicon.values()),
                "new_categories_count": len(self.new_categories),
            }
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(lexicon_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Lexicon exported to {output_path}")

    def generate_report(self) -> str:
        """
        Generate expansion report.

        Returns:
            Formatted report string
        """
        total_chars = sum(len(chars) for chars in self.lexicon.values())
        new_cat_chars = sum(len(chars) for chars in self.new_categories.values())

        report = f"""
Lexicon Expansion Report
========================

Categories: {len(self.lexicon)}
Total Characters: {total_chars}
New Categories: {len(self.new_categories)}
Characters in New Categories: {new_cat_chars}

Category Sizes:
"""
        for category, chars in sorted(self.lexicon.items(), key=lambda x: len(x[1]), reverse=True):
            report += f"  {category:20s}: {len(chars):4d} characters\n"

        if self.new_categories:
            report += "\nNew Categories:\n"
            for category, chars in self.new_categories.items():
                report += f"  {category:20s}: {chars}\n"

        if self.validation_results:
            validated = len(self.validation_results)
            avg_sim = np.mean([v["avg_similarity"] for v in self.validation_results.values()])
            avg_conf = np.mean([v["confidence"] for v in self.validation_results.values()])
            report += f"\nValidation:\n"
            report += f"  Validated Characters: {validated}\n"
            report += f"  Average Similarity: {avg_sim:.3f}\n"
            report += f"  Average Confidence: {avg_conf:.3f}\n"

        return report
