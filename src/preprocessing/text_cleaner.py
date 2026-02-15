"""Text cleaning and normalization for village names."""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CleanedName:
    """Result of cleaning a village name."""
    raw_name: str
    clean_name: str
    had_brackets: bool
    had_noise: bool
    is_valid: bool
    invalid_reason: Optional[str] = None


def is_valid_chinese_char(char: str) -> bool:
    """
    Check if character is a valid Chinese character.

    Includes:
    - CJK Unified Ideographs (U+4E00-U+9FFF)
    - CJK Extension A (U+3400-U+4DBF)
    - CJK Extension B-F (U+20000-U+2EBEF)

    Args:
        char: Single character

    Returns:
        True if valid Chinese character
    """
    if len(char) != 1:
        return False

    code = ord(char)

    # Main CJK block
    if 0x4E00 <= code <= 0x9FFF:
        return True

    # CJK Extension A
    if 0x3400 <= code <= 0x4DBF:
        return True

    # CJK Extensions B-F (rare, but keep per config)
    if 0x20000 <= code <= 0x2EBEF:
        return True

    return False


def remove_parenthetical_notes(name: str) -> Tuple[str, bool]:
    """
    Remove content in parentheses from village name.

    Examples:
        "大(土布)" -> ("大", True)
        "石头村" -> ("石头村", False)

    Args:
        name: Raw village name

    Returns:
        Tuple of (cleaned_name, had_brackets)
    """
    # Pattern matches various bracket types
    pattern = r'[（(].*?[）)]'
    cleaned = re.sub(pattern, '', name)
    had_brackets = cleaned != name

    return cleaned, had_brackets


def extract_chinese_chars(name: str, keep_rare: bool = True) -> str:
    """
    Extract only valid Chinese characters from name.

    Args:
        name: Input name
        keep_rare: Whether to keep rare CJK Extension chars

    Returns:
        String with only Chinese characters
    """
    chars = []
    for char in name:
        if is_valid_chinese_char(char):
            chars.append(char)

    return ''.join(chars)


def normalize_village_name(raw_name: str, bracket_mode: str = "remove_content",
                          keep_rare_chars: bool = True,
                          min_name_length: int = 1) -> CleanedName:
    """
    Normalize and clean a village name.

    Processing steps:
    1. Handle null/empty names
    2. Remove parenthetical notes (if configured)
    3. Extract only Chinese characters
    4. Validate result

    Args:
        raw_name: Raw village name from database
        bracket_mode: "remove_content" or "keep_all"
        keep_rare_chars: Keep rare CJK Extension characters
        min_name_length: Minimum valid length after cleaning

    Returns:
        CleanedName object with processing results
    """
    # Handle null/empty
    if raw_name is None or (isinstance(raw_name, str) and not raw_name.strip()):
        return CleanedName(
            raw_name=str(raw_name) if raw_name else "",
            clean_name="",
            had_brackets=False,
            had_noise=False,
            is_valid=False,
            invalid_reason="null_or_empty"
        )

    name = str(raw_name).strip()

    # Remove parenthetical notes
    had_brackets = False
    if bracket_mode == "remove_content":
        name, had_brackets = remove_parenthetical_notes(name)

    # Extract Chinese characters
    clean_name = extract_chinese_chars(name, keep_rare=keep_rare_chars)
    had_noise = (clean_name != name)

    # Validate
    is_valid = True
    invalid_reason = None

    if not clean_name:
        is_valid = False
        invalid_reason = "no_chinese_chars"
    elif len(clean_name) < min_name_length:
        is_valid = False
        invalid_reason = f"too_short_{len(clean_name)}"

    return CleanedName(
        raw_name=raw_name,
        clean_name=clean_name,
        had_brackets=had_brackets,
        had_noise=had_noise,
        is_valid=is_valid,
        invalid_reason=invalid_reason
    )
