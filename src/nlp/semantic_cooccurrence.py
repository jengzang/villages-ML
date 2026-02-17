"""
Semantic Co-occurrence Analysis

Analyzes how semantic categories co-occur in village names.
"""

import logging
import sqlite3
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticCooccurrence:
    """
    Analyzes semantic category co-occurrence patterns in village names.
    """

    def __init__(self, db_path: str, lexicon: Dict[str, List[str]]):
        """
        Initialize with database path and semantic lexicon.

        Args:
            db_path: Path to SQLite database
            lexicon: Dictionary mapping category to list of characters
        """
        self.db_path = db_path
        self.lexicon = lexicon
        self.char_to_category = {}
        for category, chars in lexicon.items():
            for char in chars:
                self.char_to_category[char] = category

        self.cooccurrence_matrix = None
        self.pmi_matrix = None
        self.category_counts = None
        self.total_villages = 0

    def analyze_villages(self, villages_df: pd.DataFrame, village_col: str = "自然村"):
        """
        Analyze semantic co-occurrence in village names.

        Args:
            villages_df: DataFrame with village names
            village_col: Column name containing village names
        """
        logger.info(f"Analyzing {len(villages_df)} villages for semantic co-occurrence...")

        # Initialize counters
        categories = list(self.lexicon.keys())
        n_categories = len(categories)

        # Category counts (how many villages contain each category)
        category_counts = Counter()

        # Co-occurrence counts (how many villages contain both categories)
        cooccurrence_counts = defaultdict(int)

        # Process each village
        for village_name in villages_df[village_col]:
            if pd.isna(village_name) or not village_name:
                continue

            # Find categories present in this village
            categories_in_village = set()
            for char in village_name:
                if char in self.char_to_category:
                    categories_in_village.add(self.char_to_category[char])

            # Update category counts
            for cat in categories_in_village:
                category_counts[cat] += 1

            # Update co-occurrence counts
            cats_list = list(categories_in_village)
            for i, cat1 in enumerate(cats_list):
                for cat2 in cats_list[i:]:  # Include self-cooccurrence
                    pair = tuple(sorted([cat1, cat2]))
                    cooccurrence_counts[pair] += 1

        self.total_villages = len(villages_df)
        self.category_counts = category_counts

        # Build co-occurrence matrix
        self.cooccurrence_matrix = pd.DataFrame(
            0, index=categories, columns=categories, dtype=int
        )

        for (cat1, cat2), count in cooccurrence_counts.items():
            self.cooccurrence_matrix.loc[cat1, cat2] = count
            if cat1 != cat2:
                self.cooccurrence_matrix.loc[cat2, cat1] = count

        logger.info(f"Processed {self.total_villages} villages")
        logger.info(f"Found {len(category_counts)} categories with occurrences")

        return self.cooccurrence_matrix

    def compute_pmi(self) -> pd.DataFrame:
        """
        Compute Pointwise Mutual Information (PMI) for category pairs.

        PMI(cat1, cat2) = log(P(cat1, cat2) / (P(cat1) * P(cat2)))

        Returns:
            DataFrame with PMI values
        """
        if self.cooccurrence_matrix is None:
            raise ValueError("Must call analyze_villages() first")

        logger.info("Computing PMI for category pairs...")

        categories = self.cooccurrence_matrix.index
        pmi_matrix = pd.DataFrame(
            0.0, index=categories, columns=categories, dtype=float
        )

        for cat1 in categories:
            for cat2 in categories:
                # Get counts
                cooccur_count = self.cooccurrence_matrix.loc[cat1, cat2]
                cat1_count = self.category_counts.get(cat1, 0)
                cat2_count = self.category_counts.get(cat2, 0)

                if cooccur_count == 0 or cat1_count == 0 or cat2_count == 0:
                    pmi_matrix.loc[cat1, cat2] = 0.0
                    continue

                # Compute probabilities
                p_cat1_cat2 = cooccur_count / self.total_villages
                p_cat1 = cat1_count / self.total_villages
                p_cat2 = cat2_count / self.total_villages

                # Compute PMI
                pmi = np.log2(p_cat1_cat2 / (p_cat1 * p_cat2))
                pmi_matrix.loc[cat1, cat2] = pmi

        self.pmi_matrix = pmi_matrix
        logger.info("PMI computation complete")

        return pmi_matrix

    def compute_chi_square(self) -> pd.DataFrame:
        """
        Compute chi-square test for independence of category pairs.

        Returns:
            DataFrame with p-values
        """
        if self.cooccurrence_matrix is None:
            raise ValueError("Must call analyze_villages() first")

        logger.info("Computing chi-square tests...")

        categories = self.cooccurrence_matrix.index
        pvalue_matrix = pd.DataFrame(
            1.0, index=categories, columns=categories, dtype=float
        )

        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                # Build contingency table
                both = self.cooccurrence_matrix.loc[cat1, cat2]
                cat1_only = self.category_counts[cat1] - both
                cat2_only = self.category_counts[cat2] - both
                neither = self.total_villages - cat1_only - cat2_only - both

                contingency = np.array([
                    [both, cat1_only],
                    [cat2_only, neither]
                ])

                # Chi-square test
                try:
                    chi2, pvalue, dof, expected = chi2_contingency(contingency)
                    pvalue_matrix.loc[cat1, cat2] = pvalue
                    pvalue_matrix.loc[cat2, cat1] = pvalue
                except:
                    pvalue_matrix.loc[cat1, cat2] = 1.0
                    pvalue_matrix.loc[cat2, cat1] = 1.0

        logger.info("Chi-square tests complete")

        return pvalue_matrix

    def extract_composition_rules(
        self, top_k: int = 20, min_support: int = 0
    ) -> List[Dict]:
        """
        Extract common semantic composition patterns.

        Args:
            top_k: Number of rules to return
            min_support: Minimum number of villages

        Returns:
            List of composition rules
        """
        logger.info("Extracting composition rules...")

        rules = []

        # Find pairs with high co-occurrence
        if self.pmi_matrix is None:
            self.compute_pmi()

        categories = self.cooccurrence_matrix.index
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                count = self.cooccurrence_matrix.loc[cat1, cat2]
                pmi = self.pmi_matrix.loc[cat1, cat2]

                if count >= min_support:
                    # Compute conditional probabilities
                    p_cat2_given_cat1 = count / self.category_counts[cat1]
                    p_cat1_given_cat2 = count / self.category_counts[cat2]

                    rules.append({
                        "categories": [cat1, cat2],
                        "count": int(count),
                        "frequency": float(count / self.total_villages),
                        "pmi": float(pmi),
                        "p_cat2_given_cat1": float(p_cat2_given_cat1),
                        "p_cat1_given_cat2": float(p_cat1_given_cat2),
                        "lift": float(count / (self.category_counts[cat1] * self.category_counts[cat2] / self.total_villages)),
                    })

        # Sort by count descending
        rules.sort(key=lambda x: x["count"], reverse=True)

        logger.info(f"Extracted {len(rules)} composition rules")

        return rules[:top_k]

    def compute_category_entropy(self) -> pd.DataFrame:
        """
        Compute entropy for each category's co-occurrence distribution.

        High entropy = category co-occurs with many different categories
        Low entropy = category co-occurs with few specific categories

        Returns:
            DataFrame with entropy values
        """
        if self.cooccurrence_matrix is None:
            raise ValueError("Must call analyze_villages() first")

        logger.info("Computing category entropy...")

        entropy_data = []

        for category in self.cooccurrence_matrix.index:
            # Get co-occurrence distribution
            cooccur_counts = self.cooccurrence_matrix.loc[category]

            # Exclude self-cooccurrence
            cooccur_counts = cooccur_counts.drop(category)

            # Compute probabilities
            total = cooccur_counts.sum()
            if total == 0:
                entropy = 0.0
            else:
                probs = cooccur_counts / total
                # Compute entropy
                entropy = -np.sum(probs * np.log2(probs + 1e-10))

            # Count unique co-occurrences
            unique_cooccurrences = (cooccur_counts > 0).sum()

            entropy_data.append({
                'category': category,
                'entropy': float(entropy),
                'unique_cooccurrences': int(unique_cooccurrences)
            })

        logger.info("Entropy computation complete")

        return pd.DataFrame(entropy_data)

    def get_summary_statistics(self) -> Dict:
        """
        Get summary statistics of co-occurrence analysis.

        Returns:
            Dictionary of statistics
        """
        if self.cooccurrence_matrix is None:
            raise ValueError("Must call analyze_villages() first")

        stats = {
            "total_villages": self.total_villages,
            "num_categories": len(self.category_counts),
            "category_counts": dict(self.category_counts),
            "total_cooccurrences": int(self.cooccurrence_matrix.sum().sum()),
            "avg_categories_per_village": sum(self.category_counts.values()) / self.total_villages,
        }

        if self.pmi_matrix is not None:
            # Get non-diagonal PMI values
            pmi_values = []
            for i, cat1 in enumerate(self.pmi_matrix.index):
                for cat2 in self.pmi_matrix.columns[i+1:]:
                    pmi_values.append(self.pmi_matrix.loc[cat1, cat2])

            stats["avg_pmi"] = float(np.mean(pmi_values))
            stats["max_pmi"] = float(np.max(pmi_values))
            stats["min_pmi"] = float(np.min(pmi_values))

        return stats

    def find_significant_pairs(
        self, min_cooccurrence: int = 5, alpha: float = 0.05
    ) -> pd.DataFrame:
        """
        Find statistically significant category pairs using chi-square test.

        Args:
            min_cooccurrence: Minimum co-occurrence count
            alpha: Significance level

        Returns:
            DataFrame with significant pairs
        """
        if self.cooccurrence_matrix is None:
            raise ValueError("Must call analyze_villages() first")

        if self.pmi_matrix is None:
            self.compute_pmi()

        # Compute chi-square tests
        pvalue_matrix = self.compute_chi_square()

        # Extract significant pairs
        significant_pairs = []
        categories = self.cooccurrence_matrix.index

        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                count = self.cooccurrence_matrix.loc[cat1, cat2]
                pmi = self.pmi_matrix.loc[cat1, cat2]
                pvalue = pvalue_matrix.loc[cat1, cat2]

                if count >= min_cooccurrence and pvalue < alpha:
                    significant_pairs.append({
                        'category1': cat1,
                        'category2': cat2,
                        'cooccurrence_count': int(count),
                        'pmi': float(pmi),
                        'pvalue': float(pvalue),
                        'is_significant': 1
                    })

        return pd.DataFrame(significant_pairs)

    def save_to_database(self, run_id: str):
        """
        Save co-occurrence analysis results to database.

        Args:
            run_id: Analysis run ID
        """
        if self.cooccurrence_matrix is None:
            raise ValueError("Must call analyze_villages() first")

        logger.info(f"Saving results to database (run_id={run_id})...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cooccurrence (
            run_id TEXT NOT NULL,
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            cooccurrence_count INTEGER NOT NULL,
            pmi REAL NOT NULL,
            is_significant INTEGER NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY (run_id, category1, category2)
        )
        """)

        # Compute PMI if not done
        if self.pmi_matrix is None:
            self.compute_pmi()

        # Find significant pairs
        significant_pairs = self.find_significant_pairs()

        # Save all pairs
        categories = self.cooccurrence_matrix.index
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                count = self.cooccurrence_matrix.loc[cat1, cat2]
                pmi = self.pmi_matrix.loc[cat1, cat2]

                # Check if significant
                is_significant = 0
                if not significant_pairs.empty:
                    mask = ((significant_pairs['category1'] == cat1) &
                           (significant_pairs['category2'] == cat2))
                    if mask.any():
                        is_significant = 1

                cursor.execute("""
                INSERT OR REPLACE INTO semantic_cooccurrence
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    cat1,
                    cat2,
                    int(count),
                    float(pmi),
                    is_significant,
                    pd.Timestamp.now().timestamp()
                ))

        conn.commit()
        conn.close()

        logger.info(f"Saved {len(categories) * (len(categories) - 1) // 2} pairs to database")
