"""
Formatting utilities for export module.
"""

import re
from datetime import datetime
from typing import Any, Optional


def format_number(value: float, precision: int = 0, thousands_sep: str = ',') -> str:
    """
    Format a number with thousands separator.

    Args:
        value: Number to format
        precision: Decimal places
        thousands_sep: Thousands separator character

    Returns:
        Formatted number string
    """
    if precision == 0:
        return f"{int(value):,}".replace(',', thousands_sep)
    else:
        return f"{value:,.{precision}f}".replace(',', thousands_sep)


def format_percentage(value: float, precision: int = 2) -> str:
    """
    Format a value as percentage.

    Args:
        value: Value between 0 and 1
        precision: Decimal places

    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{precision}f}%"


def format_timestamp(timestamp: float, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format Unix timestamp to string.

    Args:
        timestamp: Unix timestamp
        fmt: strftime format string

    Returns:
        Formatted timestamp string
    """
    return datetime.fromtimestamp(timestamp).strftime(fmt)


def sanitize_latex(text: str) -> str:
    """
    Escape special LaTeX characters.

    Args:
        text: Text to sanitize

    Returns:
        LaTeX-safe text
    """
    # LaTeX special characters
    special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}',
    }

    for char, escaped in special_chars.items():
        text = text.replace(char, escaped)

    return text


def truncate_text(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to append if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
