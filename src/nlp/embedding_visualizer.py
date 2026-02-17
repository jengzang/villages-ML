"""
Embedding Visualizer

Creates interactive visualizations of character embeddings.
"""

import logging
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import plotly.graph_objects as go
import plotly.express as px

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    logging.warning("UMAP not available. Install with: pip install umap-learn")

from .embedding_storage import EmbeddingStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingVisualizer:
    """
    Creates visualizations of character embeddings.
    """

    def __init__(self, run_id: str, db_path: str):
        """
        Initialize visualizer.

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

    def plot_tsne(
        self,
        output_path: str,
        color_by: str = "lexicon",
        lexicon: Optional[Dict[str, List[str]]] = None,
        char_frequencies: Optional[Dict[str, int]] = None,
        perplexity: int = 30,
        n_iter: int = 1000,
        random_state: int = 42,
    ):
        """
        Create t-SNE visualization.

        Args:
            output_path: Output HTML file path
            color_by: Color scheme ('lexicon' or 'frequency')
            lexicon: Lexicon dictionary (required if color_by='lexicon')
            char_frequencies: Character frequencies (required if color_by='frequency')
            perplexity: t-SNE perplexity parameter
            n_iter: Number of iterations
            random_state: Random seed
        """
        self.load_embeddings()

        logger.info(f"Computing t-SNE projection (perplexity={perplexity})...")

        # Prepare data matrix
        X = np.array([self.embeddings[char] for char in self.char_list])

        # Apply t-SNE
        tsne = TSNE(
            n_components=2,
            perplexity=perplexity,
            n_iter=n_iter,
            random_state=random_state,
            verbose=1,
        )
        X_2d = tsne.fit_transform(X)

        # Prepare DataFrame for plotting
        df = pd.DataFrame({
            "char": self.char_list,
            "x": X_2d[:, 0],
            "y": X_2d[:, 1],
        })

        # Add color information
        if color_by == "lexicon" and lexicon:
            # Map characters to categories
            char_to_category = {}
            for category, chars in lexicon.items():
                for char in chars:
                    char_to_category[char] = category

            df["category"] = df["char"].map(lambda c: char_to_category.get(c, "未分类"))

        elif color_by == "frequency" and char_frequencies:
            df["frequency"] = df["char"].map(lambda c: char_frequencies.get(c, 0))

        # Create interactive plot
        if color_by == "lexicon" and lexicon:
            fig = px.scatter(
                df,
                x="x",
                y="y",
                color="category",
                hover_data=["char"],
                title=f"Character Embeddings t-SNE Visualization (run: {self.run_id})",
                labels={"x": "t-SNE 1", "y": "t-SNE 2"},
            )
        elif color_by == "frequency" and char_frequencies:
            fig = px.scatter(
                df,
                x="x",
                y="y",
                color="frequency",
                hover_data=["char"],
                title=f"Character Embeddings t-SNE Visualization (run: {self.run_id})",
                labels={"x": "t-SNE 1", "y": "t-SNE 2"},
                color_continuous_scale="Viridis",
            )
        else:
            fig = px.scatter(
                df,
                x="x",
                y="y",
                hover_data=["char"],
                title=f"Character Embeddings t-SNE Visualization (run: {self.run_id})",
                labels={"x": "t-SNE 1", "y": "t-SNE 2"},
            )

        fig.update_traces(marker=dict(size=8, opacity=0.7))
        fig.update_layout(width=1200, height=800)

        fig.write_html(output_path)
        logger.info(f"t-SNE visualization saved to {output_path}")

    def plot_umap(
        self,
        output_path: str,
        color_by: str = "lexicon",
        lexicon: Optional[Dict[str, List[str]]] = None,
        char_frequencies: Optional[Dict[str, int]] = None,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        random_state: int = 42,
    ):
        """
        Create UMAP visualization.

        Args:
            output_path: Output HTML file path
            color_by: Color scheme ('lexicon' or 'frequency')
            lexicon: Lexicon dictionary
            char_frequencies: Character frequencies
            n_neighbors: UMAP n_neighbors parameter
            min_dist: UMAP min_dist parameter
            random_state: Random seed
        """
        if not UMAP_AVAILABLE:
            logger.error("UMAP not available. Install with: pip install umap-learn")
            return

        self.load_embeddings()

        logger.info(f"Computing UMAP projection (n_neighbors={n_neighbors})...")

        # Prepare data matrix
        X = np.array([self.embeddings[char] for char in self.char_list])

        # Apply UMAP
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            random_state=random_state,
            verbose=True,
        )
        X_2d = reducer.fit_transform(X)

        # Prepare DataFrame
        df = pd.DataFrame({
            "char": self.char_list,
            "x": X_2d[:, 0],
            "y": X_2d[:, 1],
        })

        # Add color information
        if color_by == "lexicon" and lexicon:
            char_to_category = {}
            for category, chars in lexicon.items():
                for char in chars:
                    char_to_category[char] = category
            df["category"] = df["char"].map(lambda c: char_to_category.get(c, "未分类"))

        elif color_by == "frequency" and char_frequencies:
            df["frequency"] = df["char"].map(lambda c: char_frequencies.get(c, 0))

        # Create plot
        if color_by == "lexicon" and lexicon:
            fig = px.scatter(
                df,
                x="x",
                y="y",
                color="category",
                hover_data=["char"],
                title=f"Character Embeddings UMAP Visualization (run: {self.run_id})",
                labels={"x": "UMAP 1", "y": "UMAP 2"},
            )
        elif color_by == "frequency" and char_frequencies:
            fig = px.scatter(
                df,
                x="x",
                y="y",
                color="frequency",
                hover_data=["char"],
                title=f"Character Embeddings UMAP Visualization (run: {self.run_id})",
                labels={"x": "UMAP 1", "y": "UMAP 2"},
                color_continuous_scale="Viridis",
            )
        else:
            fig = px.scatter(
                df,
                x="x",
                y="y",
                hover_data=["char"],
                title=f"Character Embeddings UMAP Visualization (run: {self.run_id})",
                labels={"x": "UMAP 1", "y": "UMAP 2"},
            )

        fig.update_traces(marker=dict(size=8, opacity=0.7))
        fig.update_layout(width=1200, height=800)

        fig.write_html(output_path)
        logger.info(f"UMAP visualization saved to {output_path}")

    def plot_similarity_heatmap(
        self, characters: List[str], output_path: str
    ):
        """
        Create similarity heatmap for selected characters.

        Args:
            characters: List of characters to compare
            output_path: Output HTML file path
        """
        self.load_embeddings()

        # Filter to available characters
        available_chars = [c for c in characters if c in self.embeddings]
        if not available_chars:
            logger.error("No characters found in vocabulary")
            return

        logger.info(f"Creating similarity heatmap for {len(available_chars)} characters...")

        # Compute similarity matrix
        n = len(available_chars)
        similarity_matrix = np.zeros((n, n))

        for i, char1 in enumerate(available_chars):
            for j, char2 in enumerate(available_chars):
                vec1 = self.embeddings[char1].reshape(1, -1)
                vec2 = self.embeddings[char2].reshape(1, -1)
                from sklearn.metrics.pairwise import cosine_similarity
                sim = cosine_similarity(vec1, vec2)[0][0]
                similarity_matrix[i, j] = sim

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=similarity_matrix,
            x=available_chars,
            y=available_chars,
            colorscale="RdBu",
            zmid=0,
            text=similarity_matrix,
            texttemplate="%{text:.2f}",
            textfont={"size": 10},
        ))

        fig.update_layout(
            title=f"Character Similarity Heatmap (run: {self.run_id})",
            xaxis_title="Character",
            yaxis_title="Character",
            width=800,
            height=800,
        )

        fig.write_html(output_path)
        logger.info(f"Heatmap saved to {output_path}")

    def plot_category_distribution(
        self, lexicon: Dict[str, List[str]], output_path: str
    ):
        """
        Visualize lexicon categories in embedding space.

        Args:
            lexicon: Lexicon dictionary
            output_path: Output HTML file path
        """
        self.load_embeddings()

        logger.info("Computing category centroids...")

        # Compute category centroids
        category_centroids = {}
        for category, chars in lexicon.items():
            chars_in_vocab = [c for c in chars if c in self.embeddings]
            if not chars_in_vocab:
                continue

            vectors = [self.embeddings[c] for c in chars_in_vocab]
            centroid = np.mean(vectors, axis=0)
            category_centroids[category] = centroid

        if not category_centroids:
            logger.error("No categories found in vocabulary")
            return

        # Apply t-SNE to centroids
        centroid_matrix = np.array(list(category_centroids.values()))
        category_names = list(category_centroids.keys())

        if len(category_names) < 2:
            logger.error("Need at least 2 categories for visualization")
            return

        # Use PCA for small number of categories
        from sklearn.decomposition import PCA
        pca = PCA(n_components=2)
        centroids_2d = pca.fit_transform(centroid_matrix)

        # Create DataFrame
        df = pd.DataFrame({
            "category": category_names,
            "x": centroids_2d[:, 0],
            "y": centroids_2d[:, 1],
        })

        # Create plot
        fig = px.scatter(
            df,
            x="x",
            y="y",
            text="category",
            title=f"Semantic Category Distribution (run: {self.run_id})",
            labels={"x": "PC 1", "y": "PC 2"},
        )

        fig.update_traces(marker=dict(size=15), textposition="top center")
        fig.update_layout(width=1000, height=800)

        fig.write_html(output_path)
        logger.info(f"Category distribution saved to {output_path}")