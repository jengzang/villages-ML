"""Character set extraction with per-village deduplication."""

import json
import logging
from typing import Set
import pandas as pd
from .text_cleaner import normalize_village_name

logger = logging.getLogger(__name__)


def extract_char_set(clean_name: str) -> Set[str]:
    """
    Extract unique character set from cleaned name.

    CRITICAL: Uses set() for per-village deduplication as specified in CLAUDE.md.
    Example: "石石岭岭村" -> {'石', '岭', '村'}

    Args:
        clean_name: Cleaned village name (Chinese chars only)

    Returns:
        Set of unique characters
    """
    return set(clean_name)


def process_village_batch(
    df: pd.DataFrame,
    bracket_mode: str = "remove_content",
    keep_rare_chars: bool = True,
    min_name_length: int = 1
) -> pd.DataFrame:
    """
    Process a batch of villages: clean names and extract character sets.

    Args:
        df: DataFrame with columns [市级, 区县级, 乡镇级, 自然村]
        bracket_mode: Bracket handling mode
        keep_rare_chars: Keep rare CJK Extension chars
        min_name_length: Minimum valid name length

    Returns:
        DataFrame with additional columns:
        - raw_name: Original name
        - clean_name: Cleaned name
        - name_len: Length of cleaned name
        - unique_char_cnt: Number of unique characters
        - had_brackets: Whether brackets were removed
        - had_noise: Whether non-Chinese chars were removed
        - is_valid: Whether name is valid
        - invalid_reason: Reason if invalid
        - char_set_json: JSON array of unique chars (sorted)
    """
    results = []

    for _, row in df.iterrows():
        raw_name = row['自然村']

        # Clean name
        cleaned = normalize_village_name(
            raw_name,
            bracket_mode=bracket_mode,
            keep_rare_chars=keep_rare_chars,
            min_name_length=min_name_length
        )

        # Extract character set
        char_set = extract_char_set(cleaned.clean_name) if cleaned.is_valid else set()

        # Build result row
        result = {
            '市级': row['市级'],
            '区县级': row['区县级'],
            '乡镇级': row['乡镇级'],
            'raw_name': cleaned.raw_name,
            'clean_name': cleaned.clean_name,
            'name_len': len(cleaned.clean_name),
            'unique_char_cnt': len(char_set),
            'had_brackets': cleaned.had_brackets,
            'had_noise': cleaned.had_noise,
            'is_valid': cleaned.is_valid,
            'invalid_reason': cleaned.invalid_reason,
            'char_set_json': json.dumps(sorted(char_set), ensure_ascii=False)
        }

        results.append(result)

    result_df = pd.DataFrame(results)

    # Log statistics
    total = len(result_df)
    valid = result_df['is_valid'].sum()
    invalid = total - valid
    had_brackets = result_df['had_brackets'].sum()
    had_noise = result_df['had_noise'].sum()

    logger.info(f"Processed {total} villages: {valid} valid, {invalid} invalid")
    logger.info(f"  - {had_brackets} had brackets, {had_noise} had noise")

    return result_df
