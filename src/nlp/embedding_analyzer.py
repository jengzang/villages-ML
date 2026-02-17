"""
Embedding Analyzer

Provides similarity queries, semantic arithmetic, and clustering analysis.
"""

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from .embedding_storage import EmbeddingStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingAnalyzer:
    """
    Analyzes character embeddings with similarity queries and clustering.
    """

    def __init__(self, run_id: str, db_path: str):
        """
        Initialize analyzer with embedding run.

        Args:
            run_id: Embedding run identifier
            db_path: Path to database
        """
        self.run_id = run_id
        self.db_path = db_path
        self.storage = EmbeddingStorage(db_path)
        self.embeddings = None
        self.char_list = None

    def load_embeddings(self):
        """Load all embeddings from database."""
        if self.embeddings is None:
            with self.storage:
                self.embeddings = self.storage.load_all_embeddings(self.run_id)
                self.char_list = list(self.embeddings.keys())
            logger.info(f"Loaded {len(self.embeddings)} embeddings")

    def find_similar(
        self,
        char: str,
        top_k: int = 20,
        use_precomputed: bool = True,
    ) -> List[Tuple[str, float]]:
        """
        Find K most similar characters.

        Args:
            char: Query character
            top_k: Number of results
            use_precomputed: Use precomputed similarities if available

        Returns:
            List of (character, similarity) tuples
        """
        # Try precomputed first
        if use_precomputed:
            with self.storage:
                similar = self.storage.get_similar_characters(
                    self.run_id, char, top_k
                )
                if similar:
                    return similar

        # Compute on-the-fly
        self.load_embeddings()

        if char not in self.embeddings:
            logger.warning(f"Character '{char}' not in vocabulary")
            return []

        query_vec = self.embeddings[char].reshape(1, -1)
        similarities = []

        for other_char, other_vec in self.embeddings.items():
            if other_char == char:
                continue
            sim = cosine_similarity(query_vec, other_vec.reshape(1, -1))[0][0]
            similarities.append((other_char, float(sim)))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def semantic_arithmetic(
        self,
        positive: List[str],
        negative: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Perform vector arithmetic.

        Args:
            positive: Characters to add
            negative: Characters to subtract
            top_k: Number of results

        Returns:
            List of (character, similarity) tuples

        Example:
            semantic_arithmetic(["山", "水"], ["石"])
            # Returns characters similar to "山+水-石"
        """
        self.load_embeddings()

        if negative is None:
            negative = []

        # Check all characters exist
        missing = [c for c in positive + negative if c not in self.embeddings]
        if missing:
            logger.warning(f"Characters not in vocabulary: {missing}")
            return []

        # Compute result vector
        result_vec = np.zeros_like(self.embeddings[positive[0]])

        for char in positive:
            result_vec += self.embeddings[char]

        for char in negative:
            result_vec -= self.embeddings[char]

        # Normalize
        result_vec = result_vec / np.linalg.norm(result_vec)

        # Find most similar
        similarities = []
        exclude_set = set(positive + negative)

        for char, vec in self.embeddings.items():
            if char in exclude_set:
                continue
            sim = cosine_similarity(result_vec.reshape(1, -1), vec.reshape(1, -1))[0][0]
            similarities.append((char, float(sim)))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def analogy(
        self, a: str, b: str, c: str, top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Solve analogy: a:b :: c:?

        Args:
            a, b, c: Characters for analogy
            top_k: Number of results

        Returns:
            List of (character, similarity) tuples

        Example:
            analogy("东", "西", "南")  # Should return "北"
        """
        self.load_embeddings()

        missing = [x for x in [a, b, c] if x not in self.embeddings]
        if missing:
            logger.warning(f"Characters not in vocabulary: {missing}")
            return []

        # d = b - a + c
        result_vec = (
            self.embeddings[b] - self.embeddings[a] + self.embeddings[c]
        )
        result_vec = result_vec / np.linalg.norm(result_vec)

        # Find most similar (excluding a, b, c)
        similarities = []
        exclude_set = {a, b, c}

        for char, vec in self.embeddings.items():
            if char in exclude_set:
                continue
            sim = cosine_similarity(result_vec.reshape(1, -1), vec.reshape(1, -1))[0][0]
            similarities.append((char, float(sim)))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def cluster_embeddings(
        self, n_clusters: int = 20, method: str = "kmeans", random_state: int = 42
    ) -> Dict[int, List[str]]:
        """
        Cluster characters by embedding similarity.

        Args:
            n_clusters: Number of clusters
            method: Clustering method ('kmeans' only for now)
            random_state: Random seed

        Returns:
            Dictionary mapping cluster_id to list of characters
        """
        self.load_embeddings()

        logger.info(f"Clustering {len(self.embeddings)} characters into {n_clusters} clusters...")

        # Prepare data matrix
        X = np.array([self.embeddings[char] for char in self.char_list])

        if method == "kmeans":
            clusterer = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
            labels = clusterer.fit_predict(X)
        else:
            raise ValueError(f"Unknown clustering method: {method}")

        # Group by cluster
        clusters = {}
        for char, label in zip(self.char_list, labels):
            label = int(label)
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(char)

        logger.info(f"Clustering complete: {len(clusters)} clusters")
        return clusters

    def compare_with_lexicon(self, lexicon: Dict[str, List[str]]) -> Dict:
        """
        Compare embedding clusters with lexicon categories.

        Args:
            lexicon: Dictionary mapping category to list of characters

        Returns:
            Evaluation metrics
        """
        self.load_embeddings()

        logger.info("Comparing embeddings with lexicon categories...")

        metrics = {
            "intra_category_similarity": {},
            "inter_category_similarity": {},
            "category_coverage": {},
        }

        # Compute intra-category similarity
        for category, chars in lexicon.items():
            chars_in_vocab = [c for c in chars if c in self.embeddings]
            if len(chars_in_vocab) < 2:
                continue

            # Compute pairwise similarities within category
            similarities = []
            for i, char1 in enumerate(chars_in_vocab):
                for char2 in chars_in_vocab[i + 1 :]:
                    vec1 = self.embeddings[char1].reshape(1, -1)
                    vec2 = self.embeddings[char2].reshape(1, -1)
                    sim = cosine_similarity(vec1, vec2)[0][0]
                    similarities.append(sim)

            avg_sim = np.mean(similarities) if similarities else 0.0
            metrics["intra_category_similarity"][category] = float(avg_sim)
            metrics["category_coverage"][category] = len(chars_in_vocab) / len(chars)

        # Compute inter-category similarity
        categories = list(lexicon.keys())
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i + 1 :]:
                chars1 = [c for c in lexicon[cat1] if c in self.embeddings]
                chars2 = [c for c in lexicon[cat2] if c in self.embeddings]

                if not chars1 or not chars2:
                    continue

                # Sample-based comparison (to avoid O(n^2) explosion)
                sample_size = min(20, len(chars1), len(chars2))
                chars1_sample = np.random.choice(chars1, sample_size, replace=False)
                chars2_sample = np.random.choice(chars2, sample_size, replace=False)

                similarities = []
                for char1 in chars1_sample:
                    for char2 in chars2_sample:
                        vec1 = self.embeddings[char1].reshape(1, -1)
                        vec2 = self.embeddings[char2].reshape(1, -1)
                        sim = cosine_similarity(vec1, vec2)[0][0]
                        similarities.append(sim)

                avg_sim = np.mean(similarities) if similarities else 0.0
                key = f"{cat1}_{cat2}"
                metrics["inter_category_similarity"][key] = float(avg_sim)

        # Summary statistics
        intra_sims = list(metrics["intra_category_similarity"].values())
        inter_sims = list(metrics["inter_category_similarity"].values())

        metrics["summary"] = {
            "avg_intra_category_similarity": float(np.mean(intra_sims)) if intra_sims else 0.0,
            "avg_inter_category_similarity": float(np.mean(inter_sims)) if inter_sims else 0.0,
            "avg_coverage": float(np.mean(list(metrics["category_coverage"].values()))),
        }

        logger.info(f"Intra-category similarity: {metrics['summary']['avg_intra_category_similarity']:.3f}")
        logger.info(f"Inter-category similarity: {metrics['summary']['avg_inter_category_similarity']:.3f}")

        return metrics

    def find_outliers(
        self, category: str, lexicon: Dict[str, List[str]], threshold: float = 0.5
    ) -> List[Tuple[str, float]]:
        """
        Find characters that don't fit their lexicon category.

        Args:
            category: Category name
            lexicon: Full lexicon dictionary
            threshold: Similarity threshold

        Returns:
            List of (character, avg_similarity) tuples for outliers
        """
        self.load_embeddings()

        if category not in lexicon:
            logger.warning(f"Category '{category}' not in lexicon")
            return []

        chars = [c for c in lexicon[category] if c in self.embeddings]
        if len(chars) < 2:
            logger.warning(f"Not enough characters in category '{category}'")
            return []

        outliers = []

        for char in chars:
            # Compute average similarity to other chars in category
            similarities = []
            for other_char in chars:
                if other_char == char:
                    continue
                vec1 = self.embeddings[char].reshape(1, -1)
                vec2 = self.embeddings[other_char].reshape(1, -1)
                sim = cosine_similarity(vec1, vec2)[0][0]
                similarities.append(sim)

            avg_sim = np.mean(similarities) if similarities else 0.0

            if avg_sim < threshold:
                outliers.append((char, float(avg_sim)))

        outliers.sort(key=lambda x: x[1])
        return outliers