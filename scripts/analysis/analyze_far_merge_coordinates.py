"""Analyze whether far merge proposals can be explained by coordinate systems."""

from __future__ import annotations

import csv
import math
from pathlib import Path


PROPOSAL_PATH = Path("results/intra_admin_near_duplicates/merge_proposals.csv")
OUTPUT_PATH = Path("results/intra_admin_near_duplicates/far_coordinate_system_analysis.csv")

PI = math.pi
X_PI = PI * 3000.0 / 180.0
A = 6378245.0
EE = 0.00669342162296594323


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    return ret


def wgs_to_gcj(lon: float, lat: float) -> tuple[float, float]:
    dlat = transform_lat(lon - 105.0, lat - 35.0)
    dlon = transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlon = (dlon * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    return lon + dlon, lat + dlat


def gcj_to_wgs(lon: float, lat: float) -> tuple[float, float]:
    glon, glat = wgs_to_gcj(lon, lat)
    return lon * 2 - glon, lat * 2 - glat


def gcj_to_bd(lon: float, lat: float) -> tuple[float, float]:
    z = math.sqrt(lon * lon + lat * lat) + 0.00002 * math.sin(lat * X_PI)
    theta = math.atan2(lat, lon) + 0.000003 * math.cos(lon * X_PI)
    return z * math.cos(theta) + 0.0065, z * math.sin(theta) + 0.006


def bd_to_gcj(lon: float, lat: float) -> tuple[float, float]:
    x = lon - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * X_PI)
    return z * math.cos(theta), z * math.sin(theta)


def interpretations_to_wgs(lon: float, lat: float) -> dict[str, tuple[float, float]]:
    bd_gcj = bd_to_gcj(lon, lat)
    return {
        "raw_as_wgs": (lon, lat),
        "raw_as_gcj_to_wgs": gcj_to_wgs(lon, lat),
        "raw_as_bd_to_wgs": gcj_to_wgs(*bd_gcj),
    }


def main() -> int:
    rows = []
    with PROPOSAL_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["distance_m"] or float(row["distance_m"]) <= 500:
                continue
            keep_lon = float(row["keep_lon"]) if "keep_lon" in row and row["keep_lon"] else None
            rows.append(row)

    # merge_proposals.csv does not carry lon/lat. Join from pair file columns by
    # reusing the original proposal distance only is insufficient, so read the
    # richer merge-review pair file.
    pair_by_delete = {}
    pair_path = Path("results/intra_admin_near_duplicates/merge_review_pairs.csv")
    with pair_path.open(encoding="utf-8") as f:
        for pair in csv.DictReader(f):
            pair_by_delete[pair["rowid_b"]] = pair
            pair_by_delete[pair["rowid_a"]] = pair

    out_rows = []
    for row in rows:
        pair = pair_by_delete.get(row["delete_rowid"])
        if pair is None:
            continue
        if pair["rowid_a"] == row["keep_rowid"]:
            keep_lon, keep_lat = float(pair["lon_a"]), float(pair["lat_a"])
            delete_lon, delete_lat = float(pair["lon_b"]), float(pair["lat_b"])
        else:
            keep_lon, keep_lat = float(pair["lon_b"]), float(pair["lat_b"])
            delete_lon, delete_lat = float(pair["lon_a"]), float(pair["lat_a"])

        keep_options = interpretations_to_wgs(keep_lon, keep_lat)
        delete_options = interpretations_to_wgs(delete_lon, delete_lat)
        best = None
        for keep_system, keep_coord in keep_options.items():
            for delete_system, delete_coord in delete_options.items():
                dist = haversine_m(*keep_coord, *delete_coord)
                if best is None or dist < best[2]:
                    best = (keep_system, delete_system, dist)
        assert best is not None
        raw_distance = float(row["distance_m"])
        out_rows.append({
            **row,
            "raw_distance_m": f"{raw_distance:.2f}",
            "best_system_keep": best[0],
            "best_system_delete": best[1],
            "best_distance_after_system_test_m": f"{best[2]:.2f}",
            "distance_reduction_m": f"{raw_distance - best[2]:.2f}",
            "system_mismatch_explains": "yes" if best[2] <= 500 else "no",
        })

    fieldnames = list(out_rows[0].keys()) if out_rows else []
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    for row in out_rows:
        print(
            row["keep_自然村"], "/", row["delete_自然村"],
            "raw", row["raw_distance_m"],
            "best", row["best_distance_after_system_test_m"],
            row["best_system_keep"], row["best_system_delete"],
            "explains", row["system_mismatch_explains"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
