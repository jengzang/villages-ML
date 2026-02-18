"""Administrative prefix cleaning for village names.

This module implements the administrative_prefix_cleaning skill specification.
It detects and removes redundant administrative-village prefixes from natural village names.

Design Philosophy:
- Split-first parsing: Parse natural village name before matching
- Conservative behavior: Prefer false negatives over false positives
- Explainable edits: All edits must be reproducible and auditable
"""

import re
import sqlite3
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PrefixCleanedName:
    """Result of prefix cleaning operation."""
    raw_name: str
    clean_name: str  # After basic cleaning (brackets, noise)
    prefix_removed_name: str  # After prefix removal
    had_prefix: bool
    removed_prefix: str
    match_source: str  # "same_row_exact" | "same_row_partial" | "same_township" | "same_county" | "none"
    confidence: float  # 0.0-1.0
    needs_review: bool  # True if confidence < threshold


def generate_prefix_candidates(natural_village: str) -> List[Tuple[str, str]]:
    """
    Generate prefix candidates from natural village name.

    Strategy (Split-First Parsing):
    1. Try fixed-length prefixes (2-3 characters)
    2. Try delimiter-based prefixes (村, 寨, 坊, etc.)

    Args:
        natural_village: Natural village name

    Returns:
        List of (prefix, suffix) tuples
    """
    candidates = []

    # Strategy 1: Fixed-length prefixes (2-3 characters)
    for length in [2, 3]:
        if len(natural_village) > length:
            prefix = natural_village[:length]
            suffix = natural_village[length:]
            candidates.append((prefix, suffix))

    # Strategy 2: Delimiter-based prefixes
    delimiters = ["村", "寨", "坊", "圩", "墟", "围", "片", "组"]
    for delimiter in delimiters:
        # Find first delimiter (not including first character)
        if delimiter in natural_village[1:]:
            idx = natural_village.index(delimiter, 1)

            # Include delimiter in prefix
            prefix_with_delim = natural_village[:idx+1]
            suffix_after_delim = natural_village[idx+1:]
            if suffix_after_delim:  # Must have something after delimiter
                candidates.append((prefix_with_delim, suffix_after_delim))

            # Also try without delimiter
            prefix_no_delim = natural_village[:idx]
            suffix_with_delim = natural_village[idx:]
            if len(prefix_no_delim) >= 2:  # Prefix must be at least 2 chars
                candidates.append((prefix_no_delim, suffix_with_delim))

    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)

    return unique_candidates


def flexible_match(prefix_candidate: str, admin_village: str) -> Tuple[bool, float, str]:
    """
    Flexible matching between prefix candidate and administrative village.

    Handles cases where admin village may or may not have "村" suffix.

    Args:
        prefix_candidate: Candidate prefix from natural village
        admin_village: Administrative village name (can be None)

    Returns:
        Tuple of (is_match, confidence, match_type)
    """
    # Handle None/empty admin village
    if not admin_village or not prefix_candidate:
        return (False, 0.0, "none")

    # Normalize: remove trailing delimiters
    admin_normalized = admin_village.rstrip("村寨坊圩墟围")
    prefix_normalized = prefix_candidate.rstrip("村寨坊圩墟围")

    # Priority 1: Exact match (highest confidence)
    if prefix_candidate == admin_village:
        return (True, 1.0, "exact")
    if prefix_normalized == admin_normalized and len(prefix_normalized) >= 2:
        return (True, 0.95, "exact_normalized")

    # Priority 2: Prefix match (admin is prefix of candidate)
    if prefix_normalized.startswith(admin_normalized) and len(admin_normalized) >= 2:
        return (True, 0.85, "admin_prefix")

    # Priority 3: Suffix match (candidate is prefix of admin)
    if admin_normalized.startswith(prefix_normalized) and len(prefix_normalized) >= 2:
        return (True, 0.80, "candidate_prefix")

    # Priority 4: Partial match (first 2 characters)
    if len(prefix_normalized) >= 2 and len(admin_normalized) >= 2:
        if prefix_normalized[:2] == admin_normalized[:2]:
            return (True, 0.70, "partial_2char")

    return (False, 0.0, "none")


def search_admin_villages_in_region(
    prefix_candidate: str,
    city: str,
    county: str,
    township: str,
    conn: sqlite3.Connection
) -> List[Tuple[str, str, str, str, float]]:
    """
    Search for matching administrative villages in the same region.

    Priority order: same township > same county > same city

    Args:
        prefix_candidate: Candidate prefix to search for
        city: City name
        county: County name
        township: Township name
        conn: Database connection

    Returns:
        List of (admin_village, township, county, city, confidence) tuples
    """
    results = []
    cursor = conn.cursor()

    # Priority 1: Same township (confidence 0.7)
    if township:
        query = """
        SELECT DISTINCT 行政村, 乡镇级, 区县级, 市级
        FROM 广东省自然村
        WHERE 市级 = ? AND 区县级 = ? AND 乡镇级 = ?
          AND (行政村 LIKE ? OR REPLACE(行政村, '村', '') LIKE ?)
        LIMIT 10
        """
        cursor.execute(query, (city, county, township, f"{prefix_candidate}%", f"{prefix_candidate}%"))
        for row in cursor.fetchall():
            results.append((row[0], row[1], row[2], row[3], 0.7))

    if results:
        return results

    # Priority 2: Same county (confidence 0.5)
    if county:
        query = """
        SELECT DISTINCT 行政村, 乡镇级, 区县级, 市级
        FROM 广东省自然村
        WHERE 市级 = ? AND 区县级 = ?
          AND (行政村 LIKE ? OR REPLACE(行政村, '村', '') LIKE ?)
        LIMIT 10
        """
        cursor.execute(query, (city, county, f"{prefix_candidate}%", f"{prefix_candidate}%"))
        for row in cursor.fetchall():
            results.append((row[0], row[1], row[2], row[3], 0.5))

    return results


def remove_prefix_conservative(natural_village: str, prefix: str) -> str:
    """
    Conservatively remove prefix from natural village name.

    Rules:
    1. Only remove prefix (at beginning), never internal substrings
    2. Remaining length must be >= 1 character
    3. Only remove one prefix segment per pass

    Args:
        natural_village: Natural village name
        prefix: Prefix to remove

    Returns:
        Name with prefix removed, or original if removal not safe
    """
    # Check if it's actually a prefix (at beginning)
    if not natural_village.startswith(prefix):
        return natural_village

    # Remove prefix
    remaining = natural_village[len(prefix):]

    # Check remaining length
    if len(remaining) < 1:
        return natural_village  # Don't remove if nothing left

    return remaining


def remove_administrative_prefix(
    natural_village: str,
    administrative_village: str,
    township: str = None,
    county: str = None,
    city: str = None,
    conn: sqlite3.Connection = None,
    min_length: int = 3,
    confidence_threshold: float = 0.7
) -> PrefixCleanedName:
    """
    Remove administrative prefix from natural village name.

    Implements the administrative_prefix_cleaning skill specification.

    Args:
        natural_village: Natural village name (after basic cleaning)
        administrative_village: Administrative village name from same row
        township: Township name (for fallback search)
        county: County name (for fallback search)
        city: City name (for fallback search)
        conn: Database connection (for fallback search)
        min_length: Minimum length to attempt prefix removal
        confidence_threshold: Minimum confidence to auto-remove (default 0.7)

    Returns:
        PrefixCleanedName with results and metadata
    """
    # Step 0: Length guard (conservative entry filter)
    if len(natural_village) <= min_length:
        return PrefixCleanedName(
            raw_name=natural_village,
            clean_name=natural_village,
            prefix_removed_name=natural_village,
            had_prefix=False,
            removed_prefix="",
            match_source="too_short",
            confidence=0.0,
            needs_review=False
        )

    # Handle None/empty administrative village
    if not administrative_village:
        return PrefixCleanedName(
            raw_name=natural_village,
            clean_name=natural_village,
            prefix_removed_name=natural_village,
            had_prefix=False,
            removed_prefix="",
            match_source="no_admin_village",
            confidence=0.0,
            needs_review=False
        )

    # Handle identical names
    if natural_village == administrative_village:
        return PrefixCleanedName(
            raw_name=natural_village,
            clean_name=natural_village,
            prefix_removed_name=natural_village,
            had_prefix=False,
            removed_prefix="",
            match_source="identical",
            confidence=0.0,
            needs_review=False
        )

    # Step 1: Generate prefix candidates (split-first parsing)
    prefix_candidates = generate_prefix_candidates(natural_village)

    if not prefix_candidates:
        return PrefixCleanedName(
            raw_name=natural_village,
            clean_name=natural_village,
            prefix_removed_name=natural_village,
            had_prefix=False,
            removed_prefix="",
            match_source="no_candidates",
            confidence=0.0,
            needs_review=False
        )

    # Step 2: Match and validate prefix candidates
    best_match = None
    best_confidence = 0.0
    best_match_source = "none"

    # 2.1 Row-level match (primary)
    for prefix, suffix in prefix_candidates:
        is_match, conf, match_type = flexible_match(prefix, administrative_village)
        if is_match and conf > best_confidence:
            best_match = prefix
            best_confidence = conf
            best_match_source = f"same_row_{match_type}"

    # 2.2 Local search match (fallback)
    if best_confidence < 0.7 and conn and city:
        for prefix, suffix in prefix_candidates:
            # Only search if prefix is reasonable length
            if len(prefix) >= 2:
                matches = search_admin_villages_in_region(
                    prefix, city, county, township, conn
                )
                for admin_v, twn, cnt, cty, search_conf in matches:
                    is_match, match_conf, match_type = flexible_match(prefix, admin_v)
                    if is_match:
                        # Combine search confidence with match confidence
                        combined_conf = min(search_conf, match_conf)
                        if combined_conf > best_confidence:
                            best_match = prefix
                            best_confidence = combined_conf
                            if twn == township:
                                best_match_source = "same_township"
                            elif cnt == county:
                                best_match_source = "same_county"
                            else:
                                best_match_source = "same_city"

    # Step 3: Apply editing rule (conservative removal)
    if best_match and best_confidence >= confidence_threshold:
        final_name = remove_prefix_conservative(natural_village, best_match)
        had_prefix = (final_name != natural_village)
        needs_review = False
    elif best_match and best_confidence > 0:
        # Low confidence: keep original but mark for review
        final_name = natural_village
        had_prefix = False
        needs_review = True
    else:
        # No match found
        final_name = natural_village
        had_prefix = False
        needs_review = False

    return PrefixCleanedName(
        raw_name=natural_village,
        clean_name=natural_village,
        prefix_removed_name=final_name,
        had_prefix=had_prefix,
        removed_prefix=best_match if had_prefix else "",
        match_source=best_match_source,
        confidence=best_confidence,
        needs_review=needs_review
    )


def batch_clean_prefixes(
    villages_df: pd.DataFrame,
    conn: sqlite3.Connection,
    min_length: int = 3,
    confidence_threshold: float = 0.7
) -> pd.DataFrame:
    """
    Batch clean prefixes for all villages.

    Args:
        villages_df: DataFrame with columns: 自然村, 行政村, 乡镇级, 区县级, 市级
        conn: Database connection for fallback searches
        min_length: Minimum length to attempt prefix removal
        confidence_threshold: Minimum confidence to auto-remove

    Returns:
        DataFrame with additional columns:
        - 自然村_去前缀: Name after prefix removal
        - 有前缀: Boolean (0/1)
        - 去除的前缀: Removed prefix
        - 前缀匹配来源: Match source
        - 前缀置信度: Confidence score
        - 需要审核: Needs review flag
    """
    results = []

    total = len(villages_df)
    logger.info(f"Processing {total} villages...")

    for idx, row in villages_df.iterrows():
        if idx % 10000 == 0:
            logger.info(f"Progress: {idx}/{total} ({100*idx/total:.1f}%)")

        result = remove_administrative_prefix(
            natural_village=row['自然村'],
            administrative_village=row['行政村'],
            township=row.get('乡镇级'),
            county=row.get('区县级'),
            city=row.get('市级'),
            conn=conn,
            min_length=min_length,
            confidence_threshold=confidence_threshold
        )

        results.append({
            '自然村_去前缀': result.prefix_removed_name,
            '有前缀': 1 if result.had_prefix else 0,
            '去除的前缀': result.removed_prefix,
            '前缀匹配来源': result.match_source,
            '前缀置信度': result.confidence,
            '需要审核': 1 if result.needs_review else 0
        })

    # Combine with original dataframe
    results_df = pd.DataFrame(results)
    output_df = pd.concat([villages_df.reset_index(drop=True), results_df], axis=1)

    # Log statistics
    prefix_removed_count = results_df['有前缀'].sum()
    needs_review_count = results_df['需要审核'].sum()
    logger.info(f"\nPrefix cleaning complete:")
    logger.info(f"  Total villages: {total}")
    logger.info(f"  Prefixes removed: {prefix_removed_count} ({100*prefix_removed_count/total:.1f}%)")
    logger.info(f"  Needs review: {needs_review_count} ({100*needs_review_count/total:.1f}%)")

    return output_df

