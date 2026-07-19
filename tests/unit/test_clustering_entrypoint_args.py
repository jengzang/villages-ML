import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.core.run_clustering_analysis import _parse_k_range


def test_parse_k_range_accepts_comma_and_space_separated_values():
    assert _parse_k_range(["8,12,16,20"]) == [8, 12, 16, 20]
    assert _parse_k_range(["8", "12", "16", "20"]) == [8, 12, 16, 20]
