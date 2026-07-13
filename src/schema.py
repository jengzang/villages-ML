"""Centralized schema configuration for village database tables and columns.

This module is the single source of truth for all table/column names used
across the villages-ML project. All code should reference table and column
names through a schema instance rather than hardcoding Chinese strings.

Usage:
    from src.schema import DEFAULT_SCHEMA as S

    cursor.execute(f"SELECT {S.city_col} FROM {S.preprocessed_table}")

Design:
    - Frozen dataclass: IDE autocomplete, type checking, immutability
    - Default singleton: GUANGDONG_SCHEMA for zero-effort backward compatibility
    - Parameter override: functions accept optional schema param for multi-dialect support
    - Logical keys (e.g. 'city') are the public API; physical names (e.g. '市级') are internal
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class VillageTableSchema:
    """Schema for one village database source (raw + preprocessed tables).

    Two table variants:
    - raw: original imported table
    - preprocessed: cleaned/processed table with prefix removal, char extraction, etc.
    """

    # ---- Table names ----
    raw_table: str
    preprocessed_table: str

    # ---- Administrative hierarchy columns ----
    city_col: str
    county_col: str
    township_col: str
    committee_col_raw: str
    committee_col_preprocessed: str

    # ---- Village name columns ----
    village_name_col_raw: str
    village_name_col_normalized: str
    village_name_col_prefix_removed: str

    # ---- Metadata columns ----
    char_set_col: str
    char_count_col: str
    village_id_col: str
    longitude_col: str
    latitude_col: str
    language_col_raw: str
    language_col_preprocessed: str
    pinyin_col: str

    # ---- Derived convenience mappings ----

    @property
    def level_map(self) -> Dict[str, str]:
        """Logical region keys -> physical column names."""
        return {
            'city': self.city_col,
            'county': self.county_col,
            'township': self.township_col,
        }

    @property
    def level_order(self) -> List[str]:
        """Administrative levels in hierarchical order."""
        return ['city', 'county', 'township']

    @property
    def admin_columns(self) -> List[str]:
        """All three administrative hierarchy column names."""
        return [self.city_col, self.county_col, self.township_col]

    def committee_col(self, preprocessed: bool = True) -> str:
        """Get committee column for the given table variant."""
        return self.committee_col_preprocessed if preprocessed else self.committee_col_raw

    def village_name_col(self, preprocessed: bool = True) -> str:
        """Get village name column for the given table variant."""
        if preprocessed:
            return self.village_name_col_prefix_removed
        return self.village_name_col_raw

    def language_col(self, preprocessed: bool = True) -> str:
        """Get language column for the given table variant."""
        return self.language_col_preprocessed if preprocessed else self.language_col_raw


# ---- Pre-defined Schemas ----

GUANGDONG_SCHEMA = VillageTableSchema(
    raw_table='广东省自然村',
    preprocessed_table='广东省自然村_预处理',
    city_col='市级',
    county_col='区县级',
    township_col='乡镇级',
    committee_col_raw='行政村',
    committee_col_preprocessed='村委会',
    village_name_col_raw='自然村',
    village_name_col_normalized='自然村_规范名',
    village_name_col_prefix_removed='自然村_去前缀',
    char_set_col='字符集',
    char_count_col='字符数量',
    village_id_col='village_id',
    longitude_col='longitude',
    latitude_col='latitude',
    language_col_raw='方言分布',
    language_col_preprocessed='语言分布',
    pinyin_col='拼音',
)

NATIONAL_SCHEMA = VillageTableSchema(
    raw_table='全国自然村',
    preprocessed_table='全国自然村_预处理',
    city_col='省级',
    county_col='地级',
    township_col='县级',
    committee_col_raw='行政村',
    committee_col_preprocessed='村委会',
    village_name_col_raw='自然村',
    village_name_col_normalized='自然村_规范名',
    village_name_col_prefix_removed='自然村_去前缀',
    char_set_col='字符集',
    char_count_col='字符数量',
    village_id_col='village_id',
    longitude_col='longitude',
    latitude_col='latitude',
    language_col_raw='方言分布',
    language_col_preprocessed='语言分布',
    pinyin_col='拼音',
)

DEFAULT_SCHEMA = GUANGDONG_SCHEMA
