#!/usr/bin/env python3
"""
Scan hotspot detection parameters without writing results to the database.

The output is a text report for comparing KDE + DBSCAN hotspot settings.
"""

import argparse
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.neighbors import KernelDensity

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.spatial.coordinate_loader import CoordinateLoader
from src.schema import REGION_LEVELS


@dataclass(frozen=True)
class HotspotScanConfig:
    name: str
    description: str
    bandwidth_km: float
    threshold_percentile: float
    dbscan_eps_km: float
    min_samples: int


DEFAULT_CONFIGS = [
    HotspotScanConfig("A", "baseline", 5.0, 90.0, 1.1, 3),
    HotspotScanConfig("B", "merge small fragments", 5.0, 90.0, 2.2, 3),
    HotspotScanConfig("C", "stable cores", 5.0, 90.0, 2.2, 5),
    HotspotScanConfig("D", "middle-scale hotspots", 8.0, 90.0, 3.3, 5),
    HotspotScanConfig("E", "strict high-density hotspots", 5.0, 95.0, 2.2, 3),
]


def load_coordinate_data(db_path: str) -> tuple[pd.DataFrame, np.ndarray]:
    conn = sqlite3.connect(db_path)
    try:
        loader = CoordinateLoader()
        coords_df = loader.load_coordinates(conn)
        coords = loader.get_coordinate_array(coords_df)
        return coords_df, coords
    finally:
        conn.close()


def choose_sample_indices(n_points: int, sample_size: int, seed: int) -> np.ndarray:
    if sample_size <= 0 or n_points <= sample_size:
        return np.arange(n_points)
    rng = np.random.default_rng(seed)
    return rng.choice(n_points, size=sample_size, replace=False)


def evaluate_density(coords: np.ndarray, sample_indices: np.ndarray, bandwidth_km: float) -> np.ndarray:
    kde = KernelDensity(
        bandwidth=bandwidth_km / 111.0,
        algorithm="ball_tree",
        kernel="gaussian",
        metric="euclidean",
    )
    kde.fit(coords)
    log_density = kde.score_samples(coords[sample_indices])
    return np.exp(log_density)


def cluster_hotspots(
    hotspot_coords: np.ndarray,
    hotspot_df: pd.DataFrame,
    dbscan_eps_km: float,
    min_samples: int,
) -> list[dict]:
    if len(hotspot_coords) == 0:
        return []

    labels = DBSCAN(
        eps=dbscan_eps_km / 111.0,
        min_samples=min_samples,
        metric="euclidean",
    ).fit_predict(hotspot_coords)

    hotspots = []
    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue

        mask = labels == cluster_id
        cluster_coords = hotspot_coords[mask]
        cluster_df = hotspot_df.iloc[np.where(mask)[0]]

        center_lat = cluster_coords[:, 0].mean()
        center_lon = cluster_coords[:, 1].mean()
        distances = np.sqrt(
            (cluster_coords[:, 0] - center_lat) ** 2
            + (cluster_coords[:, 1] - center_lon) ** 2
        )
        radius_km = distances.max() * 111.0

        city_mode = cluster_df[REGION_LEVELS[0]].mode()
        county_mode = cluster_df[REGION_LEVELS[1]].mode()

        hotspots.append(
            {
                "hotspot_id": len(hotspots),
                "center_lon": center_lon,
                "center_lat": center_lat,
                "density_score": cluster_df["density_score"].mean(),
                "sample_candidate_count": len(cluster_df),
                "village_count": len(cluster_df),
                "radius_km": radius_km,
                REGION_LEVELS[0]: city_mode.iloc[0] if len(city_mode) else None,
                REGION_LEVELS[1]: county_mode.iloc[0] if len(county_mode) else None,
            }
        )

    return hotspots


def count_points_within_radius(coords: np.ndarray, center_lat: float, center_lon: float, radius_km: float) -> int:
    radius_deg = radius_km / 111.0
    distances = np.sqrt(
        (coords[:, 0] - center_lat) ** 2
        + (coords[:, 1] - center_lon) ** 2
    )
    return int((distances <= radius_deg).sum())


def enrich_hotspots_with_full_counts(hotspots: list[dict], coords: np.ndarray) -> list[dict]:
    enriched = []
    for hotspot in hotspots:
        hotspot = hotspot.copy()
        hotspot.setdefault("sample_candidate_count", hotspot.get("village_count", 0))
        hotspot["full_count_core_radius"] = count_points_within_radius(
            coords,
            hotspot["center_lat"],
            hotspot["center_lon"],
            hotspot["radius_km"],
        )
        hotspot["full_count_2km"] = count_points_within_radius(
            coords,
            hotspot["center_lat"],
            hotspot["center_lon"],
            2.0,
        )
        hotspot["full_count_3km"] = count_points_within_radius(
            coords,
            hotspot["center_lat"],
            hotspot["center_lon"],
            3.0,
        )
        hotspot["full_count_5km"] = count_points_within_radius(
            coords,
            hotspot["center_lat"],
            hotspot["center_lon"],
            5.0,
        )
        enriched.append(hotspot)
    return enriched


def summarize_hotspots(config: HotspotScanConfig, density: np.ndarray, sample_indices: np.ndarray, coords: np.ndarray, coords_df: pd.DataFrame) -> dict:
    threshold = np.percentile(density, config.threshold_percentile)
    hotspot_mask = density >= threshold
    hotspot_indices = sample_indices[hotspot_mask]
    hotspot_coords = coords[hotspot_indices]
    hotspot_df = coords_df.iloc[hotspot_indices].copy()
    hotspot_df["density_score"] = density[hotspot_mask]

    hotspots = cluster_hotspots(
        hotspot_coords,
        hotspot_df,
        config.dbscan_eps_km,
        config.min_samples,
    )

    hotspots = enrich_hotspots_with_full_counts(hotspots, coords)

    counts = [h["sample_candidate_count"] for h in hotspots]
    full_core_counts = [h["full_count_core_radius"] for h in hotspots]
    full_3km_counts = [h["full_count_3km"] for h in hotspots]
    radii = [h["radius_km"] for h in hotspots]
    scores = [h["density_score"] for h in hotspots]

    city_counts = Counter(h[REGION_LEVELS[0]] for h in hotspots if h[REGION_LEVELS[0]])
    county_counts = Counter(
        f"{h[REGION_LEVELS[0]]} > {h[REGION_LEVELS[1]]}" for h in hotspots if h[REGION_LEVELS[0]] and h[REGION_LEVELS[1]]
    )

    return {
        "config": config,
        "density_threshold": threshold,
        "candidate_points": int(hotspot_mask.sum()),
        "noise_points": int(hotspot_mask.sum() - sum(counts)),
        "hotspots": hotspots,
        "summary": {
            "hotspot_count": len(hotspots),
            "covered_candidate_points": sum(counts),
            "avg_sample_candidate_count": float(np.mean(counts)) if counts else 0.0,
            "median_sample_candidate_count": float(np.median(counts)) if counts else 0.0,
            "max_sample_candidate_count": max(counts) if counts else 0,
            "avg_full_count_core_radius": float(np.mean(full_core_counts)) if full_core_counts else 0.0,
            "max_full_count_core_radius": max(full_core_counts) if full_core_counts else 0,
            "avg_full_count_3km": float(np.mean(full_3km_counts)) if full_3km_counts else 0.0,
            "max_full_count_3km": max(full_3km_counts) if full_3km_counts else 0,
            "avg_radius_km": float(np.mean(radii)) if radii else 0.0,
            "max_radius_km": max(radii) if radii else 0.0,
            "avg_density_score": float(np.mean(scores)) if scores else 0.0,
            "max_density_score": max(scores) if scores else 0.0,
            "village_count_distribution": sorted(Counter(counts).items()),
            "top_cities": city_counts.most_common(15),
            "top_counties": county_counts.most_common(15),
        },
    }


def format_result(result: dict) -> str:
    config = result["config"]
    summary = result["summary"]
    hotspots = sorted(
        result["hotspots"],
        key=lambda h: (h["full_count_3km"], h["sample_candidate_count"], h["density_score"]),
        reverse=True,
    )

    lines = []
    lines.append("=" * 80)
    lines.append(f"Mode {config.name}: {config.description}")
    lines.append("=" * 80)
    lines.append(
        "Parameters: "
        f"bandwidth={config.bandwidth_km:.1f}km, "
        f"threshold=p{config.threshold_percentile:.0f}, "
        f"dbscan_eps={config.dbscan_eps_km:.1f}km, "
        f"min_samples={config.min_samples}"
    )
    lines.append(f"Density threshold: {result['density_threshold']:.6f}")
    lines.append(f"Candidate sample points above threshold: {result['candidate_points']:,}")
    lines.append(f"Candidate points discarded as DBSCAN noise: {result['noise_points']:,}")
    lines.append("")
    lines.append("Summary:")
    for key, value in summary.items():
        if key in {"village_count_distribution", "top_cities", "top_counties"}:
            continue
        if isinstance(value, float):
            lines.append(f"  {key}: {value:.4f}")
        else:
            lines.append(f"  {key}: {value:,}")
    lines.append(f"  village_count_distribution: {summary['village_count_distribution']}")
    lines.append(f"  top_cities: {summary['top_cities']}")
    lines.append(f"  top_counties: {summary['top_counties']}")
    lines.append("")
    lines.append("Top hotspots by full_count_3km:")
    lines.append("  rank | sample | core_full | full_2km | full_3km | full_5km | radius_km | density | city | county | lon | lat")
    for rank, hotspot in enumerate(hotspots[:20], start=1):
        lines.append(
            f"  {rank:>4} | "
            f"{hotspot['sample_candidate_count']:>6} | "
            f"{hotspot['full_count_core_radius']:>9} | "
            f"{hotspot['full_count_2km']:>8} | "
            f"{hotspot['full_count_3km']:>8} | "
            f"{hotspot['full_count_5km']:>8} | "
            f"{hotspot['radius_km']:>9.3f} | "
            f"{hotspot['density_score']:>7.4f} | "
            f"{hotspot[REGION_LEVELS[0]]} | "
            f"{hotspot[REGION_LEVELS[1]]} | "
            f"{hotspot['center_lon']:.6f} | "
            f"{hotspot['center_lat']:.6f}"
        )
    lines.append("")
    return "\n".join(lines)


def build_report(results: List[dict], db_path: str, sample_size: int, seed: int, total_points: int) -> str:
    lines = []
    lines.append("Hotspot Parameter Scan")
    lines.append("=" * 80)
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Database: {db_path}")
    lines.append(f"Total valid coordinate points: {total_points:,}")
    lines.append(f"Sample size for KDE evaluation: {sample_size:,}")
    lines.append(f"Random seed: {seed}")
    lines.append("")
    lines.append("Note: sample_candidate_count is counted from sampled KDE candidate points.")
    lines.append("Full-count fields are computed against all valid coordinate points.")
    lines.append("No rows are written to spatial_hotspots or any other database table.")
    lines.append("")
    lines.append("Comparison table:")
    lines.append("mode | hotspots | candidates | covered | noise | avg_sample | max_sample | avg_full_3km | max_full_3km | avg_radius | max_radius")
    for result in results:
        config = result["config"]
        summary = result["summary"]
        lines.append(
            f"{config.name} | "
            f"{summary['hotspot_count']} | "
            f"{result['candidate_points']} | "
            f"{summary['covered_candidate_points']} | "
            f"{result['noise_points']} | "
            f"{summary['avg_sample_candidate_count']:.2f} | "
            f"{summary['max_sample_candidate_count']} | "
            f"{summary['avg_full_count_3km']:.2f} | "
            f"{summary['max_full_count_3km']} | "
            f"{summary['avg_radius_km']:.2f} | "
            f"{summary['max_radius_km']:.2f}"
        )
    lines.append("")
    lines.extend(format_result(result) for result in results)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan hotspot parameters without database writes")
    parser.add_argument("--db-path", default="data/villages.db")
    parser.add_argument("--output", default=None)
    parser.add_argument("--sample-size", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument(
        "--modes",
        default=",".join(config.name for config in DEFAULT_CONFIGS),
        help="Comma-separated scan modes to run, e.g. A,C,E",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_modes = {mode.strip().upper() for mode in args.modes.split(",") if mode.strip()}
    configs = [config for config in DEFAULT_CONFIGS if config.name in selected_modes]
    if not configs:
        valid_modes = ", ".join(config.name for config in DEFAULT_CONFIGS)
        raise ValueError(f"No valid modes selected. Valid modes: {valid_modes}")

    coords_df, coords = load_coordinate_data(args.db_path)
    sample_indices = choose_sample_indices(len(coords), args.sample_size, args.seed)

    density_by_bandwidth: Dict[float, np.ndarray] = {}
    for bandwidth in sorted({config.bandwidth_km for config in configs}):
        print(f"Computing KDE density for bandwidth={bandwidth:.1f}km...")
        density_by_bandwidth[bandwidth] = evaluate_density(coords, sample_indices, bandwidth)

    results = []
    for config in configs:
        print(f"Running mode {config.name}: {config.description}...")
        results.append(
            summarize_hotspots(
                config,
                density_by_bandwidth[config.bandwidth_km],
                sample_indices,
                coords,
                coords_df,
            )
        )

    output_path = Path(args.output) if args.output else Path("results") / f"hotspot_parameter_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_report(results, args.db_path, len(sample_indices), args.seed, len(coords)),
        encoding="utf-8",
    )
    print(f"Report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
