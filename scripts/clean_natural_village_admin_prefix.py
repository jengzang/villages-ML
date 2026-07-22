"""Clean natural-village-name prefixes derived from administrative-village names.

Two-phase matching:
1. Match against the current row's 行政村 (safe → auto-update).
2. Match against other 行政村 in the same township (potential mis-record → review).

Default is preview mode; pass --apply to write changes.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = Path("data/villages.db")
RAW_TABLE = "广东省自然村"
OUTPUT_DIR = Path("results/admin_prefix_cleanup")

# Ordered longest-first so longer suffixes match before shorter ones.
ADMIN_SUFFIXES = [
    "社区居民委员会",
    "村民委员会",
    "居民委员会",
    "社区居委会",
    "村委会",
    "居委会",
    "行政村",
    "管理区",
    "社区",
    "村",
]

# Secondary removal: after stripping the admin prefix, also strip these if
# they appear immediately at the start of the remainder.
# "镇"/"乡" included because natural-village names often embed a township name
# (e.g. 七迳镇新屋仔 — the prefix should be 七迳镇, not just 七迳).
SECONDARY_STRIP_SUFFIXES = [
    "社区居民委员会",
    "村民委员会",
    "居民委员会",
    "社区居委会",
    "村委会",
    "居委会",
    "行政村",
    "管理区",
    "社区",
    "村",
    "镇",
    "乡",
]

# Bidirectional character variants common in Guangdong place names.
# When an admin name contains either character, also generate a candidate
# with the variant swapped in (e.g. 朗 ↔ 㙟, 涌 ↔ 冲).
DIALECT_VARIANT_MAP = {
    "朗": "㙟", "㙟": "朗",
    "涌": "冲", "冲": "涌",
    "埇": "冲", "冲": "埇",
    "滘": "窖", "窖": "滘",
    "坭": "泥", "泥": "坭",
    "冚": "坎",
    "輋": "畲",
    "磜": "礤",
    "迳": "径", "径": "迳",
    "崀": "良",
}

# If the remaining text starts with any of these characters, skip.
DIGIT_PREFIX_CHARS = frozenset("一二三四五六七八九十")

# If the remaining text starts with any of these chars, it's likely a false
# match where the "prefix" was actually part of a compound village name
# (e.g. 架岭仔村 = 架岭(core) + 仔(diminutive) + 村, NOT 架岭(admin prefix) + 仔村).
INVALID_REMAINING_START_CHARS = frozenset("仔圩围里片社街坡塘尾冲")

# Remaining names that are purely functional/administrative designations,
# never valid as standalone natural-village names.
GENERIC_REMAINING_NAMES = frozenset({
    "农场", "林场", "石场", "渔业", "渔村", "社区",
    "祠堂", "水坝", "茶店", "瑶族", "路口",
})

# Minimum remaining length after stripping.
MIN_REMAINING_CHARS = 2

# Minimum prefix length for ANY matching.  Single-character prefixes are
# never safe — they match too many unrelated village names.
MIN_PREFIX_LEN = 2

# Generic base names that are too common for cross-admin matching.
GENERIC_BASE_NAMES = frozenset({
    "新", "东", "西", "南", "北", "上", "下", "大", "小",
    "中", "前", "后", "左", "右", "头", "尾", "内", "外",
})

# Minimum length for admin_base used in cross-admin matching.
CROSS_ADMIN_MIN_BASE_LEN = 2

CHINESE_RE = re.compile(r"[㐀-䶿一-鿿\U00020000-\U0002EBEF]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(value: object) -> str:
    """Return stripped string or empty string for None."""
    return "" if value is None else str(value).strip()


def chinese_only(value: str) -> str:
    """Extract only Chinese characters."""
    return "".join(CHINESE_RE.findall(value))


def strip_admin_suffix(name: str) -> str:
    """Remove trailing admin suffixes from a name, longest-first.

    Returns the base name without the suffix.  The suffix list is ordered
    longest-first to prevent partial matches (e.g. '村民委员会' before '村').
    """
    for suffix in ADMIN_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def strip_leading_secondary(name: str) -> tuple[str, str]:
    """Strip at most one leading admin/community suffix from *name*.

    Returns ``(stripped, removed_suffix)``.  *removed_suffix* is empty if no
    secondary suffix was found at the start.
    """
    for suffix in SECONDARY_STRIP_SUFFIXES:
        if name.startswith(suffix) and len(name) > len(suffix):
            return name[len(suffix):], suffix
    return name, ""


def starts_with_digit_prefix(name: str) -> bool:
    """True when *name* starts with a Chinese numeral character."""
    return bool(name) and name[0] in DIGIT_PREFIX_CHARS


# ---------------------------------------------------------------------------
# Township admin dictionary
# ---------------------------------------------------------------------------

def build_township_admin_dict(conn: sqlite3.Connection) -> dict[tuple[str, str], dict[str, list[str]]]:
    """Build a dictionary of admin villages keyed by (区县级, 乡镇级).

    Each value is ``{admin_base: [admin_full, ...]}`` mapping a stripped
    admin name to one or more original admin full names.
    """
    rows = conn.execute(
        f"""
        SELECT DISTINCT "区县级", "乡镇级", "行政村"
        FROM "{RAW_TABLE}"
        WHERE "行政村" IS NOT NULL AND "行政村" != ''
        """
    ).fetchall()

    result: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for county, township, admin in rows:
        county = clean(county)
        township = clean(township)
        admin_full = clean(admin)
        if not admin_full:
            continue
        admin_norm = chinese_only(admin_full)
        admin_base = strip_admin_suffix(admin_norm)
        if not admin_base:
            continue
        key = (county, township)
        result[key][admin_base].append(admin_full)

    return dict(result)


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

def make_candidates(admin_full: str) -> list[tuple[str, str, str]]:
    """Return ``[(prefix, label, source), ...]`` for an admin village name.

    Candidates are ordered by priority: raw full name first, then normalized
    full name, then raw base, then normalized base.  Only prefixes >=
    MIN_PREFIX_LEN characters are included.

    *source* is ``"raw"`` or ``"norm"`` — raw prefixes are matched against the
    raw village name; norm prefixes against the chinese_only village name.
    """
    candidates: list[tuple[str, str, str]] = []
    admin_raw = admin_full
    admin_norm = chinese_only(admin_full)

    # Raw full name
    if len(admin_raw) >= MIN_PREFIX_LEN:
        candidates.append((admin_raw, "full", "raw"))
    # Normalized full name
    if admin_norm and admin_norm != admin_raw and len(admin_norm) >= MIN_PREFIX_LEN:
        candidates.append((admin_norm, "full", "norm"))

    # Raw base (strip suffix from raw string)
    admin_raw_base = strip_admin_suffix(admin_raw)
    if admin_raw_base and admin_raw_base != admin_raw and len(admin_raw_base) >= MIN_PREFIX_LEN:
        candidates.append((admin_raw_base, "base", "raw"))
    # Normalized base
    admin_base = strip_admin_suffix(admin_norm)
    if admin_base and admin_base != admin_norm and len(admin_base) >= MIN_PREFIX_LEN:
        # Avoid duplicate if raw base happens to equal norm base
        if admin_base != admin_raw_base:
            candidates.append((admin_base, "base", "norm"))

    # Dialect variant candidates (lower priority).
    # For each unique candidate text, generate variants by swapping dialect chars.
    seen_variants: set[str] = {c[0] for c in candidates}
    extra: list[tuple[str, str, str]] = []
    for cand_text, cand_label, cand_src in candidates:
        if len(cand_text) < MIN_PREFIX_LEN:
            continue
        for i, ch in enumerate(cand_text):
            variant_ch = DIALECT_VARIANT_MAP.get(ch)
            if variant_ch is None:
                continue
            variant_text = cand_text[:i] + variant_ch + cand_text[i + 1:]
            if variant_text not in seen_variants:
                seen_variants.add(variant_text)
                extra.append((variant_text, cand_label, "norm"))
    candidates.extend(extra)

    return candidates


def generate_variants(text: str) -> list[str]:
    """Generate all single-character dialect-variant forms of *text*.

    Returns a list of variant strings (may be empty if no variant chars exist).
    Does NOT include the original text.
    """
    result: list[str] = []
    for i, ch in enumerate(text):
        variant_ch = DIALECT_VARIANT_MAP.get(ch)
        if variant_ch is not None:
            result.append(text[:i] + variant_ch + text[i + 1:])
    return result


def try_match_prefix(target: str, prefix: str) -> str | None:
    """Return the remainder after stripping *prefix* from *target*.

    Returns None if *target* does not start with *prefix*, or if *prefix* is
    too short.
    """
    if not prefix or len(prefix) < MIN_PREFIX_LEN:
        return None
    if target.startswith(prefix) and target != prefix:
        return target[len(prefix):]
    return None


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

def is_safe_to_apply(
    remaining: str,
    match_type: str,
    admin_base: str,
    original_name: str,
    county: str,
    township: str,
) -> tuple[bool, str]:
    """Return ``(safe, reason)`` for whether the result can be auto-applied.

    *safe* is True only when all safety rules pass.
    """
    # Result too short
    if len(chinese_only(remaining)) < MIN_REMAINING_CHARS:
        return False, "删除后不足2个汉字"

    # Starts with Chinese digit
    if starts_with_digit_prefix(remaining):
        return False, "删除后以中文数字开头"

    # Starts with invalid remaining char (仔/圩/围/里/片/社/街)
    if remaining and remaining[0] in INVALID_REMAINING_START_CHARS:
        return False, f"删除后以'{remaining[0]}'开头(疑似复合地名误匹配)"

    # Remaining is a pure functional designation, not a village name
    if remaining in GENERIC_REMAINING_NAMES:
        return False, f"删除后为通用词'{remaining}'(非自然村名)"

    # identical to original — nothing done
    if remaining == original_name:
        return False, "处理后名称与原名称相同"

    return True, ""


def is_cross_admin_candidate(
    admin_base: str,
    county: str,
    township: str,
    candidates: list[tuple[str, str]],
) -> tuple[bool, str]:
    """Check whether a cross-admin match is high-confidence enough to propose."""
    # Missing location context
    if not county or not township:
        return False, "缺少区县或乡镇信息"

    # Admin base too short
    if len(chinese_only(admin_base)) < CROSS_ADMIN_MIN_BASE_LEN:
        return False, f"跨行政村基础名过短(={'、'.join(chinese_only(admin_base))})"

    # Admin base is generic
    if admin_base in GENERIC_BASE_NAMES:
        return False, f"跨行政村基础名过于泛化({admin_base})"

    return True, ""


# ---------------------------------------------------------------------------
# Core matching logic
# ---------------------------------------------------------------------------

def _match_best(
    candidates: list[tuple[str, str, str]],
    target_raw: str,
    target_norm: str,
) -> tuple[str, str, str, str, str] | None:
    """Try all candidates against both raw and norm targets.

    Returns ``(prefix, label, remaining, admin_base, source)`` for the
    best (longest-prefix) match, or None.
    """
    best: tuple[str, str, str, str, str] | None = None
    target_variants = generate_variants(target_norm)

    for prefix, label, source in candidates:
        targets_to_try = [target_raw if source == "raw" else target_norm]
        if source == "norm" and target_variants:
            targets_to_try.extend(target_variants)

        for target in targets_to_try:
            remaining = try_match_prefix(target, prefix)
            if remaining is None:
                continue
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, label, remaining, source)

    return best


def match_record(
    village_name: str,
    current_admin_full: str,
    township_admin_dict: dict[str, list[str]],
    county: str,
    township: str,
) -> dict:
    """Run two-phase matching for a single record.

    Returns a dict with all match fields.
    """
    village_raw = village_name
    village_norm = chinese_only(village_name)

    def _base_result() -> dict:
        return {
            "original_admin": current_admin_full,
            "matched_admin": "",
            "admin_base": "",
            "original_natural_name": village_name,
            "matched_prefix": "",
            "remaining_after_admin": village_norm or village_raw,
            "removed_secondary_suffix": "",
            "new_natural_name": village_name,
            "match_type": "no_match",
            "possible_mismatch": 0,
            "confidence": "",
            "action": "skip",
            "reason": "",
        }

    result = _base_result()

    if not village_norm and not village_raw:
        result["reason"] = "自然村名称为空"
        return result

    # Normalize the remaining to Chinese-only for the final name, but keep
    # the match working against whichever source (raw/norm) was matched.
    def _final_name(remaining: str) -> str:
        """Best-effort normalized final name."""
        norm = chinese_only(remaining)
        return norm if norm else remaining

    # ---- Phase 1: match current admin ----
    current_candidates = make_candidates(current_admin_full)
    best_p1 = _match_best(current_candidates, village_raw, village_norm)

    if best_p1 is not None:
        prefix, label, remaining, source = best_p1
        admin_norm = chinese_only(current_admin_full)
        admin_base = strip_admin_suffix(admin_norm)
        if not admin_base:
            admin_base = admin_norm

        # Apply secondary strip
        remaining2, removed_suffix = strip_leading_secondary(remaining)
        new_name = _final_name(remaining2)
        safe, reason = is_safe_to_apply(new_name, "current_admin", admin_base, village_norm or village_raw, county, township)

        result.update({
            "matched_admin": current_admin_full,
            "admin_base": admin_base,
            "matched_prefix": prefix + (removed_suffix if removed_suffix else ""),
            "remaining_after_admin": remaining,
            "removed_secondary_suffix": removed_suffix,
            "new_natural_name": new_name,
            "match_type": "current_admin",
            "possible_mismatch": 0,
            "confidence": "high",
            "action": "update" if safe else "skip",
            "reason": reason if not safe else "",
        })
        return result

    # ---- Phase 2: match against other admins in same township ----
    key = (county, township)
    other_admins = township_admin_dict.get(key, {})

    if not other_admins:
        result["reason"] = "无同乡镇行政村词典（区县或乡镇缺失）"
        return result

    # Collect all candidates from other admins
    # (prefix, remaining, source, admin_base, admin_full, label)
    phase2_matches: list[tuple[str, str, str, str, str, str]] = []

    for admin_base_cand, admin_full_list in other_admins.items():
        for admin_full_cand in admin_full_list:
            if admin_full_cand == current_admin_full:
                continue
            for prefix, label, source in make_candidates(admin_full_cand):
                targets_to_try = [village_raw if source == "raw" else village_norm]
                if source == "norm":
                    targets_to_try.extend(generate_variants(village_norm))
                for target in targets_to_try:
                    remaining = try_match_prefix(target, prefix)
                    if remaining is None:
                        continue
                    phase2_matches.append((prefix, remaining, source, admin_base_cand, admin_full_cand, label))
                    break  # first match wins for this candidate

    if not phase2_matches:
        result["reason"] = "无匹配的行政村前缀"
        return result

    # Select best: prefer full-name matches, then longest prefix
    full_matches = [m for m in phase2_matches if m[5] == "full"]
    candidates_to_rank = full_matches if full_matches else phase2_matches
    max_len = max(len(m[0]) for m in candidates_to_rank)
    best_matches = [m for m in candidates_to_rank if len(m[0]) == max_len]

    # Detect ambiguity from *different* matched admin bases
    unique_bases: set[str] = set()
    unique_full_admins: set[str] = set()
    for m in best_matches:
        unique_bases.add(m[3])
        unique_full_admins.add(m[4])

    if len(unique_full_admins) > 1:
        result.update({
            "matched_admin": " / ".join(sorted(unique_full_admins)),
            "admin_base": " / ".join(sorted(unique_bases)),
            "matched_prefix": best_matches[0][0],
            "remaining_after_admin": best_matches[0][1],
            "match_type": "ambiguous",
            "possible_mismatch": 0,
            "confidence": "low",
            "action": "skip",
            "reason": f"多候选歧义: {'; '.join(sorted(unique_full_admins))}",
        })
        return result

    # Single unique admin match
    prefix, remaining, source, admin_base, matched_admin_full, label = best_matches[0]

    # Apply secondary strip
    remaining2, removed_suffix = strip_leading_secondary(remaining)
    new_name = _final_name(remaining2)

    # Cross-admin safety checks
    cross_ok, cross_reason = is_cross_admin_candidate(admin_base, county, township, best_matches)
    if not cross_ok:
        result.update({
            "matched_admin": matched_admin_full,
            "admin_base": admin_base,
            "matched_prefix": prefix,
            "remaining_after_admin": remaining,
            "match_type": "township_other_admin",
            "possible_mismatch": 1,
            "confidence": "low",
            "action": "skip",
            "reason": cross_reason,
        })
        return result

    safe, safe_reason = is_safe_to_apply(new_name, "township_other_admin", admin_base, village_norm or village_raw, county, township)

    final_prefix = prefix + (removed_suffix if removed_suffix else "")

    # Validate: does the final prefix correspond to a real admin in the township?
    # Full-name matches (prefix = complete admin name) get higher confidence.
    all_admin_full_names: set[str] = set()
    for admin_list in other_admins.values():
        for a in admin_list:
            all_admin_full_names.add(chinese_only(a))
    prefix_is_admin_name = final_prefix in all_admin_full_names

    # If the secondary strip absorbed a township suffix (镇/乡), the prefix
    # refers to a township, not an admin village — clean the name but don't
    # reassign the admin village.
    update_admin = removed_suffix not in ("镇", "乡")

    result.update({
        "matched_admin": matched_admin_full,
        "admin_base": admin_base,
        "matched_prefix": final_prefix,
        "remaining_after_admin": remaining,
        "removed_secondary_suffix": removed_suffix,
        "new_natural_name": new_name,
        "match_type": "township_other_admin",
        "possible_mismatch": 1,
        "update_admin": update_admin,
        "confidence": "confirmed" if (safe and prefix_is_admin_name) else ("high" if safe else "low"),
        "action": "review" if safe else "skip",
        "reason": safe_reason if not safe else "",
    })
    return result


# ---------------------------------------------------------------------------
# CSV output helpers
# ---------------------------------------------------------------------------

CSV_FIELDNAMES = [
    "row_id", "市级", "区县级", "乡镇级", "original_admin",
    "matched_admin", "admin_base", "original_natural_name",
    "matched_prefix", "remaining_after_admin", "removed_secondary_suffix",
    "new_natural_name", "match_type", "possible_mismatch",
    "update_admin", "confidence", "action", "reason",
]


def classify_row(result: dict) -> str:
    """Classify a result row into an output bucket."""
    if result["action"] == "update":
        return "updates"
    if result["action"] == "skip":
        return "skipped"
    if result["match_type"] in ("township_other_admin", "ambiguous"):
        return "mismatch"
    return "skipped"


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_table(
    conn: sqlite3.Connection,
) -> dict:
    """Run the full prefix-cleaning pipeline."""
    print("Building township admin dictionary ...")
    township_dict = build_township_admin_dict(conn)
    township_keys = len(township_dict)
    total_admins = sum(len(v) for v in township_dict.values())
    print(f"  {township_keys:,} (区县, 乡镇) groups, {total_admins:,} unique admin base names")

    print("Loading rows ...")
    rows = conn.execute(
        f"""
        SELECT rowid, "市级", "区县级", "乡镇级", "行政村", "自然村"
        FROM "{RAW_TABLE}"
        """
    ).fetchall()
    print(f"  {len(rows):,} rows")

    # Results by category
    updates: list[dict] = []
    mismatches: list[dict] = []
    skipped: list[dict] = []
    stats: Counter[str] = Counter()

    print("Processing ...")
    t0 = time.time()
    report_every = 50000

    for i, row in enumerate(rows):
        rowid, city, county, township, admin, village = row
        city = clean(city)
        county = clean(county)
        township = clean(township)
        admin = clean(admin)
        village = clean(village)

        result = match_record(village, admin, township_dict, county, township)
        result["row_id"] = rowid
        result["市级"] = city
        result["区县级"] = county
        result["乡镇级"] = township

        category = classify_row(result)
        if category == "updates":
            updates.append(result)
            stats["current_admin_update"] += 1
        elif category == "mismatch":
            mismatches.append(result)
            if result["match_type"] == "township_other_admin":
                stats["township_other_admin"] += 1
            elif result["match_type"] == "ambiguous":
                stats["ambiguous"] += 1
        else:
            skipped.append(result)
            stats["no_match_or_skip"] += 1

        # Sub-stats
        if result["match_type"] == "no_match":
            stats["no_match"] += 1
        if result["reason"] == "删除后不足2个汉字":
            stats["skip_too_short"] += 1
        if result["reason"] == "删除后以中文数字开头":
            stats["skip_digit_prefix"] += 1
        if "低置信度" in result.get("reason", "") or result.get("confidence") == "low":
            stats["low_confidence"] += 1

        if (i + 1) % report_every == 0:
            elapsed = time.time() - t0
            print(f"  {i + 1:,} / {len(rows):,} rows ({elapsed:.1f}s)")

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Updates (current_admin): {stats['current_admin_update']:,}")
    print(f"  Cross-admin matches:     {stats['township_other_admin']:,}")
    print(f"  Ambiguous:               {stats['ambiguous']:,}")
    print(f"  No match / skipped:      {stats['no_match_or_skip']:,}")

    return {
        "updates": updates,
        "mismatches": mismatches,
        "skipped": skipped,
        "stats": stats,
    }


def write_csvs(results: dict, output_dir: Path) -> None:
    """Write the three CSV output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "admin_prefix_updates.csv": results["updates"],
        "admin_mismatch_candidates.csv": results["mismatches"],
        "admin_prefix_skipped.csv": results["skipped"],
    }

    for filename, rows in files.items():
        path = output_dir / filename
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Wrote {path} ({len(rows):,} rows)")


def write_summary(results: dict, output_dir: Path) -> None:
    """Write a summary report."""
    stats = results["stats"]
    mismatches = results["mismatches"]

    # Cross-admin → frequency
    cross_admin_pairs: Counter[tuple[str, str]] = Counter()
    for m in mismatches:
        if m["match_type"] == "township_other_admin":
            orig = m["original_admin"]
            matched = m["matched_admin"]
            cross_admin_pairs[(orig, matched)] += 1

    lines = [
        "# Admin Prefix Cleanup — Summary",
        "",
        "## Statistics",
        "",
        "| metric | count |",
        "|---|---:|",
        f"| 本行政村成功匹配 (current_admin update) | {stats.get('current_admin_update', 0):,} |",
        f"| 同乡镇其他行政村唯一匹配 (cross-admin) | {stats.get('township_other_admin', 0):,} |",
        f"| 同乡镇多候选歧义 (ambiguous) | {stats.get('ambiguous', 0):,} |",
        f"| 无匹配 (no_match) | {stats.get('no_match', 0):,} |",
        f"| 删除后不足2字 | {stats.get('skip_too_short', 0):,} |",
        f"| 删除后数字开头 | {stats.get('skip_digit_prefix', 0):,} |",
        f"| 低置信度 | {stats.get('low_confidence', 0):,} |",
        "",
    ]

    if cross_admin_pairs:
        lines.extend([
            "## Cross-Admin Mapping Frequency (Top 50)",
            "",
            "| original_admin → matched_admin | count |",
            "|---|---:|",
        ])
        for (orig, matched), count in cross_admin_pairs.most_common(50):
            lines.append(f"| {orig} → {matched} | {count:,} |")
        lines.append("")

    path = output_dir / "SUMMARY.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {path}")


def apply_updates(conn: sqlite3.Connection, updates: list[dict]) -> int:
    """Apply prefix changes to the database. Returns count of rows updated."""
    count = 0
    for row in updates:
        if row["action"] != "update":
            continue
        if row.get("update_admin", True):
            conn.execute(
                f'UPDATE "{RAW_TABLE}" SET "自然村" = ?, "行政村" = ? WHERE rowid = ?',
                (row["new_natural_name"], row["matched_admin"], row["row_id"]),
            )
        else:
            conn.execute(
                f'UPDATE "{RAW_TABLE}" SET "自然村" = ? WHERE rowid = ?',
                (row["new_natural_name"], row["row_id"]),
            )
        count += 1
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to villages.db")
    parser.add_argument("--table", default=RAW_TABLE, help="Table name")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Preview mode (default)")
    parser.add_argument("--apply", dest="dry_run", action="store_false",
                       help="Actually write Phase-1 current-admin changes to the database")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                       help="Output directory for CSV reports")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.dry_run:
        # Backup
        backup_path = args.db.with_suffix(args.db.suffix + ".backup_" + time.strftime("%Y%m%d_%H%M%S"))
        print(f"Creating backup: {backup_path}")
        shutil.copy2(args.db, backup_path)
        print(f"  Backup complete ({os.path.getsize(backup_path) / 1024 / 1024:.1f} MB)")

    conn = sqlite3.connect(args.db)

    try:
        results = process_table(conn)

        # Write CSVs
        write_csvs(results, args.output_dir)
        write_summary(results, args.output_dir)

        if not args.dry_run:
            to_apply = list(results["updates"])
            print(f"\nApplying {len(to_apply):,} Phase-1 current-admin updates ...")
            conn.execute("BEGIN")
            try:
                updated = apply_updates(conn, to_apply)
                conn.commit()
                print(f"  {updated:,} rows updated successfully")
            except Exception:
                conn.rollback()
                print("ERROR: transaction rolled back", file=sys.stderr)
                raise
        else:
            print("\nDry-run complete. Use --apply to write Phase-1 changes.")
            print(f"  {len(results['updates']):,} rows would be updated (current-admin)")
            cross = sum(1 for m in results["mismatches"] if m["match_type"] == "township_other_admin")
            high_cross = sum(1 for m in results["mismatches"]
                           if m["match_type"] == "township_other_admin" and m["confidence"] == "high")
            print(f"  {cross:,} cross-admin matches in report ({high_cross:,} high-confidence)")

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
