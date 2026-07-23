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
    - Logical keys (e.g. REGION_LEVELS[0]) are the public API; physical names (e.g. '市级') are internal
"""

from dataclasses import dataclass
from typing import Dict, List

# ---------------------------------------------------------------------------
# Canonical region levels – single source of truth for hierarchical order.
# All code should import from here rather than hardcoding [REGION_LEVELS[0], REGION_LEVELS[1], …].
# ---------------------------------------------------------------------------
_DEFAULT_REGION_LEVELS = ['city', 'county', 'township', 'committee']
REGION_LEVELS = list(_DEFAULT_REGION_LEVELS)


def init_region_levels(levels: list[str]) -> None:
    """Replace REGION_LEVELS from config at startup.

    Mutates the list in-place so all existing imports see the new values.
    Call once before any pipeline code that reads ``REGION_LEVELS[N]``.
    """
    REGION_LEVELS.clear()
    REGION_LEVELS.extend(levels)


def level_index(level: str) -> int:
    """Return 1‑based index of *level* in REGION_LEVELS."""
    return REGION_LEVELS.index(level) + 1


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
            REGION_LEVELS[0]: self.city_col,
            REGION_LEVELS[1]: self.county_col,
            REGION_LEVELS[2]: self.township_col,
            REGION_LEVELS[3]: self.committee_col_preprocessed,
        }

    @property
    def level_order(self) -> List[str]:
        """Administrative levels in hierarchical order."""
        return list(REGION_LEVELS)

    @property
    def admin_columns(self) -> List[str]:
        """All four administrative hierarchy column names."""
        return [self.city_col, self.county_col, self.township_col, self.committee_col_preprocessed]

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
    char_set_col='char_set',
    char_count_col='char_count',
    village_id_col='village_id',
    longitude_col='longitude',
    latitude_col='latitude',
    language_col_raw='方言分布',
    language_col_preprocessed='方言分布',
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
    char_set_col='char_set',
    char_count_col='char_count',
    village_id_col='village_id',
    longitude_col='longitude',
    latitude_col='latitude',
    language_col_raw='方言分布',
    language_col_preprocessed='语言分布',
    pinyin_col='拼音',
)

DEFAULT_SCHEMA = GUANGDONG_SCHEMA


SCHEMAS = {
    'guangdong': GUANGDONG_SCHEMA,
    'national': NATIONAL_SCHEMA,
}


def get_schema(name: str | None = None) -> VillageTableSchema:
    """Return a configured village table schema by profile name."""
    schema_name = name or 'guangdong'
    try:
        return SCHEMAS[schema_name]
    except KeyError as exc:
        available = ', '.join(sorted(SCHEMAS))
        raise ValueError(f"Unknown village schema: {schema_name}. Available: {available}") from exc
