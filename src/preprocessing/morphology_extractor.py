"""Morphology pattern extraction (suffix/prefix) from village names."""

import json
import logging
from typing import Optional, List
import pandas as pd
from .text_cleaner import normalize_village_name

logger = logging.getLogger(__name__)


def extract_suffix(name: str, n: int = 1) -> Optional[str]:
    """
    Extract n-character suffix from village name.

    Args:
        name: Cleaned village name
        n: Number of characters to extract

    Returns:
        Suffix string or None if name is too short
    """
    if len(name) < n:
        return None
    return name[-n:]


def extract_prefix(name: str, n: int = 1) -> Optional[str]:
    """
    Extract n-character prefix from village name.

    Args:
        name: Cleaned village name
        n: Number of characters to extract

    Returns:
        Prefix string or None if name is too short
    """
    if len(name) < n:
        return None
    return name[:n]


def extract_morphology_features(
    villages_df: pd.DataFrame,
    suffix_lengths: List[int] = None,
    prefix_lengths: List[int] = None,
    bracket_mode: str = "remove_content",
    keep_rare_chars: bool = True,
    min_name_length: int = 2
) -> pd.DataFrame:
    """
    Extract morphology features (suffix/prefix patterns) from villages.

    Args:
        villages_df: DataFrame with columns [市级, 区县级, 乡镇级, 自然村]
        suffix_lengths: List of suffix n-gram lengths (default: [1, 2, 3])
        prefix_lengths: List of prefix n-gram lengths (default: [2, 3])
        bracket_mode: Bracket handling mode
        keep_rare_chars: Keep rare CJK Extension chars
        min_name_length: Minimum valid name length

    Returns:
        DataFrame with columns:
        - 市级, 区县级, 乡镇级
        - raw_name, clean_name
        - name_len, is_valid, invalid_reason
        - suffix_1, suffix_2, suffix_3 (if requested)
        - prefix_2, prefix_3 (if requested)
    """
    if suffix_lengths is None:
        suffix_lengths = [1, 2, 3]
    if prefix_lengths is None:
        prefix_lengths = [2, 3]

    logger.info(f"Extracting morphology: suffix_lengths={suffix_lengths}, prefix_lengths={prefix_lengths}")

    results = []

    for _, row in villages_df.iterrows():
        raw_name = row['自然村']

        # Clean name
        cleaned = normalize_village_name(
            raw_name,
            bracket_mode=bracket_mode,
            keep_rare_chars=keep_rare_chars,
            min_name_length=min_name_length
        )

        # Build result row
        result = {
            '市级': row['市级'],
            '区县级': row['区县级'],
            '乡镇级': row['乡镇级'],
            'raw_name': cleaned.raw_name,
            'clean_name': cleaned.clean_name,
            'name_len': len(cleaned.clean_name),
            'is_valid': cleaned.is_valid,
            'invalid_reason': cleaned.invalid_reason
        }

        # Extract suffix patterns
        if cleaned.is_valid:
            for n in suffix_lengths:
                suffix = extract_suffix(cleaned.clean_name, n)
                result[f'suffix_{n}'] = suffix

            # Extract prefix patterns
            for n in prefix_lengths:
                prefix = extract_prefix(cleaned.clean_name, n)
                result[f'prefix_{n}'] = prefix
        else:
            # Set all patterns to None for invalid names
            for n in suffix_lengths:
                result[f'suffix_{n}'] = None
            for n in prefix_lengths:
                result[f'prefix_{n}'] = None

        results.append(result)

    result_df = pd.DataFrame(results)

    # Log statistics
    total = len(result_df)
    valid = result_df['is_valid'].sum()
    invalid = total - valid

    logger.info(f"Processed {total} villages: {valid} valid, {invalid} invalid")

    # Log sample patterns
    if valid > 0:
        valid_subset = result_df[result_df['is_valid']].head(5)
        logger.info(f"Sample patterns:")
        for _, row in valid_subset.iterrows():
            patterns = []
            for n in suffix_lengths:
                if f'suffix_{n}' in row and row[f'suffix_{n}']:
                    patterns.append(f"s{n}={row[f'suffix_{n}']}")
            for n in prefix_lengths:
                if f'prefix_{n}' in row and row[f'prefix_{n}']:
                    patterns.append(f"p{n}={row[f'prefix_{n}']}")
            logger.info(f"  {row['clean_name']}: {', '.join(patterns)}")

    return result_df
