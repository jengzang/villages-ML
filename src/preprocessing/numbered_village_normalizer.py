"""Numbered village normalization for statistical aggregation.

This module implements the numbered_village_normalization skill specification.
It normalizes villages with trailing Chinese numeral suffixes for statistical purposes.

IMPORTANT: This is non-destructive and only affects analytical processing.
The database is never modified.

Design Philosophy:
- Statistical-layer normalization, not data-layer correction
- Prevents artificial inflation of village counts
- Improves frequency accuracy and clustering reliability
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def detect_trailing_numeral(village_name: str) -> Tuple[bool, str, str]:
    """
    Detect trailing Chinese numeral in village name.

    Patterns detected:
    - 村名 + 数字 + 村 (e.g., 东村一村)
    - 村名 + 数字 (e.g., 南岭二)

    Args:
        village_name: Village name to check

    Returns:
        Tuple of (has_numeral, base_name, numeral_suffix)
    """
    # Chinese numerals
    numerals = "一二三四五六七八九十"

    # Pattern 1: 村名 + 数字 + 村
    pattern1 = f"^(.+?)([{numerals}]+)村$"
    match = re.match(pattern1, village_name)
    if match and len(match.group(1)) >= 1:
        return (True, match.group(1), match.group(2) + "村")

    # Pattern 2: 村名 + 数字
    pattern2 = f"^(.+?)([{numerals}]+)$"
    match = re.match(pattern2, village_name)
    if match and len(match.group(1)) >= 1:
        return (True, match.group(1), match.group(2))

    return (False, village_name, "")


def normalize_numbered_village(village_name: str) -> str:
    """
    Normalize numbered village for statistical purposes.

    Examples:
    - 东村一村 → 东村
    - 东村二村 → 东村
    - 南岭一 → 南岭
    - 南岭二 → 南岭

    Args:
        village_name: Village name to normalize

    Returns:
        Normalized base name (without numeral suffix)
    """
    has_numeral, base_name, numeral_suffix = detect_trailing_numeral(village_name)

    if has_numeral:
        return base_name
    else:
        return village_name
