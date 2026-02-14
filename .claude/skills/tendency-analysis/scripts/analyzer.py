"""
Basic Tendency Analyzer for Village Name Character Analysis

This module provides the TendencyAnalyzer class for analyzing character usage
tendencies in Chinese village names across different administrative regions.
"""

import re
from collections import Counter
from typing import Dict, List, Tuple, Optional


class TendencyAnalyzer:
    """
    Analyzes character usage tendencies in village names.

    This analyzer identifies which characters are preferentially used or avoided
    in specific regions compared to the overall dataset using relative frequency
    analysis.

    Attributes:
        data: Hierarchical village data structure
        char_town_counts: Character counts by town
        town_total_counts: Total character counts by town
        char_total_counts: Overall character counts
        total_chars: Total characters across all villages
    """

    def __init__(self, data: Dict):
        """
        Initialize the analyzer with village data.

        Args:
            data: Hierarchical dictionary with structure:
                {
                    "Town Name": {
                        "村民委员会": [...],
                        "居民委员会": [...],
                        "社区": [...],
                        "自然村": {
                            "Committee": ["Village1", "Village2", ...]
                        }
                    }
                }

        Raises:
            ValueError: If data structure is invalid or has fewer than 2 towns
        """
        if not isinstance(data, dict) or len(data) < 2:
            raise ValueError("Data must be a dictionary with at least 2 towns")

        self.data = data
        self.char_town_counts: Dict[str, Dict[str, int]] = {}
        self.town_total_counts: Dict[str, int] = {}
        self.char_total_counts: Dict[str, int] = {}
        self.total_chars: int = 0

        self._calculate_frequencies()

    def _filter_chars(self, text: str) -> str:
        """
        Filter parentheses and their content from text.

        Args:
            text: Input text

        Returns:
            Filtered text with parentheses removed
        """
        return re.sub(r'[（）()]', '', text)

    def _calculate_frequencies(self) -> None:
        """
        Calculate character frequencies for all towns.

        Populates:
            - char_town_counts: Character counts by town
            - town_total_counts: Total village counts by town
            - char_total_counts: Overall character counts
            - total_chars: Total characters across all villages
        """
        for town, town_data in self.data.items():
            town_char_counter = Counter()

            # Count characters from all administrative categories
            for committee_name in town_data.get('村民委员会', []):
                town_char_counter.update(self._filter_chars(committee_name))

            for committee_name in town_data.get('居民委员会', []):
                town_char_counter.update(self._filter_chars(committee_name))

            for community_name in town_data.get('社区', []):
                town_char_counter.update(self._filter_chars(community_name))

            # Count characters from natural villages
            for villages in town_data.get('自然村', {}).values():
                for village in villages:
                    town_char_counter.update(self._filter_chars(village))

            # Store village count for this town
            natural_village_count = sum(
                len(villages) for villages in town_data.get('自然村', {}).values()
            )
            self.town_total_counts[town] = natural_village_count

            # Update character counts
            for char, count in town_char_counter.items():
                if char not in self.char_town_counts:
                    self.char_town_counts[char] = {}
                self.char_town_counts[char][town] = count
                self.char_total_counts[char] = self.char_total_counts.get(char, 0) + count

        self.total_chars = sum(self.char_total_counts.values())

    def analyze_tendencies(
        self,
        n: int = 1,
        target_town: Optional[str] = None,
        high_threshold: float = 10,
        low_threshold: float = 20,
        display_threshold: float = 5
    ) -> Dict:
        """
        Analyze character usage tendencies across towns.

        Args:
            n: Number of top/bottom towns to include in tendency groups
            target_town: Specific town to analyze, or None for all towns
            high_threshold: Minimum tendency value (%) to display high-tendency chars
            low_threshold: Minimum absolute tendency value (%) to display low-tendency chars
            display_threshold: Minimum overall frequency (%) to analyze a character

        Returns:
            Dictionary with structure:
            {
                "Town Name": {
                    "high_tendency": [(char, tendency_value, [towns]), ...],
                    "low_tendency": [(char, tendency_value, [towns]), ...]
                }
            }
        """
        # Determine which towns to analyze
        if target_town and target_town != '全部':
            target_town_names = [target_town, target_town + "镇", target_town + "街道"]
            towns_to_analyze = [t for t in self.town_total_counts.keys() if t in target_town_names]
        else:
            towns_to_analyze = list(self.town_total_counts.keys())

        results = {}

        # Calculate overall average frequency for filtering
        total_villages = sum(self.town_total_counts.values())

        for town in towns_to_analyze:
            high_tendency_list = []
            low_tendency_list = []

            for char, counts in self.char_town_counts.items():
                # Calculate overall frequency
                overall_frequency = self.char_total_counts[char] / total_villages * 100

                # Skip rare characters
                if overall_frequency < display_threshold:
                    continue

                # Calculate frequencies for all towns
                frequencies = {t: 0.0 for t in self.town_total_counts}
                frequencies.update({
                    t: count / self.town_total_counts[t]
                    for t, count in counts.items()
                })

                # Sort towns by frequency
                sorted_towns = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)

                # Get top-n towns (with tie handling)
                top_towns = self._get_top_n_with_ties(sorted_towns, n, reverse=True)

                # Get bottom-n towns (with tie handling)
                bottom_towns = self._get_top_n_with_ties(sorted_towns, n, reverse=False)

                # Calculate overall average frequency
                overall_avg = sum(frequencies.values()) / len(frequencies)

                # Calculate high tendency value
                if top_towns and town in [t[0] for t in top_towns]:
                    top_avg = sum(freq for _, freq in top_towns) / len(top_towns)
                    high_tendency_value = (top_avg - overall_avg) / overall_avg * 100

                    if high_tendency_value >= high_threshold:
                        high_tendency_list.append((
                            char,
                            high_tendency_value,
                            [t[0] for t in top_towns]
                        ))

                # Calculate low tendency value
                if bottom_towns and town in [t[0] for t in bottom_towns]:
                    bottom_avg = sum(freq for _, freq in bottom_towns) / len(bottom_towns)
                    low_tendency_value = (bottom_avg - overall_avg) / overall_avg * 100

                    if abs(low_tendency_value) >= low_threshold:
                        low_tendency_list.append((
                            char,
                            low_tendency_value,
                            [t[0] for t in bottom_towns]
                        ))

            # Sort results by tendency value
            high_tendency_list.sort(key=lambda x: x[1], reverse=True)
            low_tendency_list.sort(key=lambda x: x[1])

            results[town] = {
                "high_tendency": high_tendency_list,
                "low_tendency": low_tendency_list
            }

        return results

    def _get_top_n_with_ties(
        self,
        sorted_items: List[Tuple],
        n: int,
        reverse: bool = True
    ) -> List[Tuple]:
        """
        Get top-n items with tie handling.

        Args:
            sorted_items: Sorted list of (town, frequency) tuples
            n: Number of items to select
            reverse: If True, select highest values; if False, select lowest

        Returns:
            List of selected items including ties
        """
        if not sorted_items:
            return []

        if not reverse:
            sorted_items = sorted_items[::-1]

        selected = sorted_items[:n]

        if len(sorted_items) > n:
            threshold_value = selected[-1][1]
            for item in sorted_items[n:]:
                if item[1] == threshold_value:
                    selected.append(item)
                else:
                    break

        return selected

    def print_results(self, results: Dict) -> None:
        """
        Print formatted analysis results to console.

        Args:
            results: Results dictionary from analyze_tendencies()
        """
        for town, town_results in results.items():
            print(f"\n{'='*50}")
            print(f"=== {town} ===")
            print(f"{'='*50}\n")

            # Print high tendency characters
            if town_results["high_tendency"]:
                print("高倾向字 (在以下镇使用频率最高):")
                for char, tendency_value, towns in town_results["high_tendency"]:
                    town_list = ", ".join(towns)
                    print(f"  {char} (倾向值: +{tendency_value:.1f}%) - 在 [{town_list}] 中使用频率最高")
            else:
                print("高倾向字: 无符合条件的字符")

            print()

            # Print low tendency characters
            if town_results["low_tendency"]:
                print("低倾向字 (在以下镇使用频率最低):")
                for char, tendency_value, towns in town_results["low_tendency"]:
                    town_list = ", ".join(towns)
                    print(f"  {char} (倾向值: {tendency_value:.1f}%) - 在 [{town_list}] 中使用频率最低")
            else:
                print("低倾向字: 无符合条件的字符")


if __name__ == "__main__":
    # Example usage
    sample_data = {
        "Town1": {
            "村民委员会": ["Committee1"],
            "自然村": {
                "Committee1": ["田心村", "田边村", "田垌村"]
            }
        },
        "Town2": {
            "村民委员会": ["Committee2"],
            "自然村": {
                "Committee2": ["城东村", "城西村", "城南村"]
            }
        }
    }

    analyzer = TendencyAnalyzer(sample_data)
    results = analyzer.analyze_tendencies(n=1, high_threshold=10, low_threshold=20)
    analyzer.print_results(results)
