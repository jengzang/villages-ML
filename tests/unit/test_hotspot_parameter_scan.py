import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.analysis.scan_hotspot_parameters import enrich_hotspots_with_full_counts


def test_enrich_hotspots_with_full_counts_adds_fixed_radius_counts():
    coords = np.array(
        [
            [23.0000, 113.0000],
            [23.0090, 113.0000],
            [23.0180, 113.0000],
            [23.0360, 113.0000],
            [23.0600, 113.0000],
        ]
    )
    hotspots = [
        {
            "center_lat": 23.0000,
            "center_lon": 113.0000,
            "radius_km": 2.0,
        }
    ]

    enriched = enrich_hotspots_with_full_counts(hotspots, coords)

    assert enriched[0]["sample_candidate_count"] == 0
    assert enriched[0]["full_count_core_radius"] == 3
    assert enriched[0]["full_count_2km"] == 3
    assert enriched[0]["full_count_3km"] == 3
    assert enriched[0]["full_count_5km"] == 4
