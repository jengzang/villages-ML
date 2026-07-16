"""List homophone/variant candidates for manual review in chat."""

from __future__ import annotations

import csv
from pathlib import Path


PAIR_PATH = Path("results/intra_admin_near_duplicates/merge_review_pairs.csv")
OUTPUT_PATH = Path("results/intra_admin_near_duplicates/homophone_variant_candidates.csv")


def is_simple_village_suffix_pair(a: str, b: str) -> bool:
    return a + "村" == b or b + "村" == a


def main() -> int:
    selected = []
    with PAIR_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if "same_pinyin_different_chars" not in row["rules"]:
                continue
            if not row["distance_m"] or float(row["distance_m"]) > 200:
                continue
            if is_simple_village_suffix_pair(row["自然村_a"], row["自然村_b"]):
                continue
            selected.append(row)

    selected.sort(key=lambda r: (float(r["distance_m"]), r["市级"], r["区县级"], r["乡镇级"], r["行政村"]))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=selected[0].keys() if selected else [])
        writer.writeheader()
        writer.writerows(selected)

    print(f"selected={len(selected)}")
    for idx, row in enumerate(selected[:120], 1):
        print(
            f"{idx}. {row['市级']} {row['区县级']} {row['乡镇级']} {row['行政村']} | "
            f"{row['自然村_a']}({row['拼音_a']}) vs {row['自然村_b']}({row['拼音_b']}) | "
            f"{row['distance_m']}m"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
