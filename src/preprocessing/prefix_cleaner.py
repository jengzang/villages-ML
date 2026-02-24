"""Administrative prefix cleaning for village names.

This module implements a 5-rule priority system for removing administrative
prefixes from natural village names.

Rule Priority Order:
1. Greedy delimiter-based removal (HIGHEST PRIORITY)
2. Admin village comparison (only if Rule 1 doesn't apply)
3. Size/direction modifier handling (during Rule 2)
4. Minimum 2 Chinese characters validation
5. Identical names early exit

Design Philosophy:
- Strict priority order: Rules are applied in sequence
- Conservative behavior: Prefer false negatives over false positives
- Explainable edits: All edits must be reproducible and auditable
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from .constants import (
    DELIMITERS,
    DELIMITERS_SUBSET,
    MODIFIERS,
    HOMOPHONE_PAIRS,
    MIN_LENGTH_DEFAULT,
    CONFIDENCE_THRESHOLD_DEFAULT,
    CONFIDENCE_SCORES
)

logger = logging.getLogger(__name__)


@dataclass
class PrefixCleanedName:
    """Result of prefix cleaning operation."""
    raw_name: str
    clean_name: str  # After basic cleaning (brackets, noise)
    prefix_removed_name: str  # After prefix removal
    had_prefix: bool
    removed_prefix: str
    match_source: str  # "rule1_delimiter" | "rule2_admin_match" | "rule3_modifier" | "none"
    confidence: float  # 0.0-1.0
    needs_review: bool  # True if confidence < threshold


def count_chinese_chars(text: str) -> int:
    """Count only Chinese characters (not numbers, punctuation).

    Args:
        text: Input text

    Returns:
        Number of Chinese characters
    """
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    return len(chinese_chars)


def remove_delimiters(text: str) -> str:
    """Remove administrative delimiters from text.

    Args:
        text: Input text

    Returns:
        Text with delimiters removed
    """
    for delimiter in DELIMITERS:
        text = text.replace(delimiter, "")
    return text


def try_rule1_delimiter_removal(natural_village: str) -> str:
    """Rule 1: Find the LAST delimiter and remove everything up to and including it.

    Delimiters: 村, 社区, 寨, 片 (checked in this order for longer matches first)

    Args:
        natural_village: Natural village name

    Returns:
        Prefix to remove (empty string if no delimiter found)

    Examples:
        霞露村尾厝 → 霞露村 (remove up to and including last 村)
        陈家村石桥社区郑厝 → 陈家村石桥社区 (greedy to last delimiter!)
    """
    delimiters = DELIMITERS  # Use constants from config

    last_delimiter_pos = -1
    last_delimiter_len = 0

    # Find the LAST occurrence of any delimiter
    for delimiter in delimiters:
        pos = natural_village.rfind(delimiter)
        if pos > last_delimiter_pos:
            last_delimiter_pos = pos
            last_delimiter_len = len(delimiter)

    if last_delimiter_pos > 0:  # Found a delimiter (not at start)
        # Remove everything up to and including the delimiter
        prefix = natural_village[:last_delimiter_pos + last_delimiter_len]
        return prefix

    return ""  # No delimiter found


def try_homophone_match(natural_village: str, normalized_admin: str) -> str:
    """Try to match with homophone variants.

    Start with simple common pairs, can expand later.

    Args:
        natural_village: Natural village name
        normalized_admin: Normalized admin village name

    Returns:
        Matched prefix (empty string if no match)
    """
    for standard, variants in HOMOPHONE_PAIRS.items():
        if normalized_admin == standard:
            for variant in variants:
                # Check if natural village starts with variant
                if natural_village.startswith(variant):
                    # Find the delimiter after variant
                    for delimiter in DELIMITERS_SUBSET:
                        candidate = variant + delimiter
                        if natural_village.startswith(candidate):
                            return candidate
                    return variant

    return ""


def try_rule2_admin_comparison(natural_village: str, admin_village: str, min_length: int = 2) -> tuple[str, bool]:
    """Rule 2: Compare with admin village name (with homophone support).

    Steps:
    1. Normalize admin village (remove delimiters)
    2. Check for modifiers (Rule 3)
    3. Match with 70% threshold
    4. Support homophone variants
    5. IMPORTANT: If natural contains full admin name (with delimiter),
       try that first. If it fails Rule 4, don't try normalized version.

    Args:
        natural_village: Natural village name
        admin_village: Admin village name
        min_length: Minimum Chinese characters required after removal

    Returns:
        Tuple of (prefix to remove, should_try_alternatives)
        - If should_try_alternatives is False, don't try other matches

    Examples:
        Admin=凤北村, Natural=凤北超苟村 → 凤北
        Admin=湖下村, Natural=湖厦村祠堂前片 → 湖厦村 (homophone)
        Admin=松水村, Natural=大松水路头 → 大松水 (modifier)
        Admin=王家村, Natural=王家村东 → "" (would leave only 东, abort)
    """
    if not admin_village:
        return "", True

    # Normalize admin village: remove delimiters
    normalized_admin = remove_delimiters(admin_village)

    # Rule 3: Check for modifiers
    for modifier in MODIFIERS:
        # Check with delimiter first
        for delimiter in DELIMITERS_SUBSET:
            candidate_with_delim = modifier + normalized_admin + delimiter
            if natural_village.startswith(candidate_with_delim):
                remaining = natural_village[len(candidate_with_delim):]
                if count_chinese_chars(remaining) >= min_length:
                    return candidate_with_delim, True
                # If fails Rule 4, don't try without delimiter
                return "", False

        # Then check without delimiter
        candidate = modifier + normalized_admin
        if natural_village.startswith(candidate):
            remaining = natural_village[len(candidate):]
            if count_chinese_chars(remaining) >= min_length:
                return candidate, True

    # Check with delimiter FIRST (priority over normalized)
    for delimiter in DELIMITERS_SUBSET:
        candidate = normalized_admin + delimiter
        if natural_village.startswith(candidate):
            remaining = natural_village[len(candidate):]
            if count_chinese_chars(remaining) >= min_length:
                return candidate, True
            # If natural contains full admin name but removal fails Rule 4,
            # don't try to remove just the normalized part
            return "", False

    # Direct match (no modifier, no delimiter)
    if natural_village.startswith(normalized_admin):
        # Check 70% threshold (at least 2 chars)
        if len(normalized_admin) >= 2:
            remaining = natural_village[len(normalized_admin):]
            if count_chinese_chars(remaining) >= min_length:
                return normalized_admin, True

    # Homophone matching
    homophone_match = try_homophone_match(natural_village, normalized_admin)
    if homophone_match:
        remaining = natural_village[len(homophone_match):]
        if count_chinese_chars(remaining) >= min_length:
            return homophone_match, True

    return "", True  # No match found


def remove_administrative_prefix(
    natural_village: str,
    administrative_village: str,
    min_length: int = MIN_LENGTH_DEFAULT,
    confidence_threshold: float = CONFIDENCE_THRESHOLD_DEFAULT
) -> PrefixCleanedName:
    """Remove administrative prefix from natural village name.

    Applies 5 rules in strict priority order:
    1. Rule 1: Greedy delimiter-based removal (HIGHEST PRIORITY)
    2. Rule 2: Admin village comparison (only if Rule 1 doesn't apply)
    3. Rule 3: Modifier handling (during Rule 2)
    4. Rule 4: Minimum 2 Chinese characters validation
    5. Rule 5: Identical names early exit

    Args:
        natural_village: Natural village name (after basic cleaning)
        administrative_village: Administrative village name from same row
        min_length: Minimum Chinese characters required after removal (default: 2)
        confidence_threshold: Minimum confidence to auto-remove (default 0.7)

    Returns:
        PrefixCleanedName with results and metadata

    Examples:
        Rule 1: 霞露村尾厝 + 霞露村 → 尾厝 (remove 霞露村)
        Rule 2: 凤北超苟村 + 凤北村 → 超苟村 (remove 凤北)
        Rule 3: 大松水路头 + 松水村 → 路头 (remove 大松水)
        Rule 4: 王家村东 + 王家村 → 王家村东 (would leave only 东, abort)
        Rule 5: 凤北村 + 凤北村 → 凤北村 (identical, no removal)
    """
    # Rule 5: Early exit for identical names
    if natural_village == administrative_village:
        return PrefixCleanedName(
            raw_name=natural_village,
            clean_name=natural_village,
            prefix_removed_name=natural_village,
            had_prefix=False,
            removed_prefix="",
            match_source="rule5_identical",
            confidence=1.0,
            needs_review=False
        )

    # Handle empty/None cases
    if not natural_village:
        return PrefixCleanedName(
            raw_name=natural_village or "",
            clean_name=natural_village or "",
            prefix_removed_name=natural_village or "",
            had_prefix=False,
            removed_prefix="",
            match_source="empty_name",
            confidence=0.0,
            needs_review=False
        )

    # Rule 1: Check for explicit delimiters (HIGHEST PRIORITY)
    prefix = try_rule1_delimiter_removal(natural_village)
    if prefix:
        remaining = natural_village[len(prefix):]
        # Rule 4: Validate minimum length
        if count_chinese_chars(remaining) >= min_length:
            return PrefixCleanedName(
                raw_name=natural_village,
                clean_name=natural_village,
                prefix_removed_name=remaining,
                had_prefix=True,
                removed_prefix=prefix,
                match_source="rule1_delimiter",
                confidence=CONFIDENCE_SCORES["rule1_delimiter"],
                needs_review=False
            )

    # Rule 2: Compare with admin village (only if Rule 1 didn't match)
    prefix, _ = try_rule2_admin_comparison(natural_village, administrative_village, min_length)
    if prefix:
        remaining = natural_village[len(prefix):]\
        # Rule 4 validation already done in try_rule2_admin_comparison
        # Determine if this was a modifier match (Rule 3)
        match_source = "rule3_modifier" if any(prefix.startswith(m) for m in MODIFIERS) else "rule2_admin_match"

        return PrefixCleanedName(
            raw_name=natural_village,
            clean_name=natural_village,
            prefix_removed_name=remaining,
            had_prefix=True,
            removed_prefix=prefix,
            match_source=match_source,
            confidence=CONFIDENCE_SCORES.get(match_source, 0.9),
            needs_review=False
        )

    # No match found
    return PrefixCleanedName(
        raw_name=natural_village,
        clean_name=natural_village,
        prefix_removed_name=natural_village,
        had_prefix=False,
        removed_prefix="",
        match_source="none",
        confidence=0.0,
        needs_review=False
    )


def batch_clean_prefixes(
    villages_df: pd.DataFrame,
    min_length: int = MIN_LENGTH_DEFAULT,
    confidence_threshold: float = CONFIDENCE_THRESHOLD_DEFAULT
) -> pd.DataFrame:
    """Batch clean prefixes for all villages.

    Args:
        villages_df: DataFrame with columns: 自然村, 村委会
        min_length: Minimum Chinese characters required after removal
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
            administrative_village=row.get('村委会', row.get('行政村', '')),
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
