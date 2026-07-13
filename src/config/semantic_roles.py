"""
Semantic role classification for Chinese village name pattern detection.

This is the **single source of truth** shared by all modules that detect
modifier-head patterns or semantic conflicts in village names.

When you add, rename, or remove categories in any semantic lexicon
(semantic_lexicon_v1.json, semantic_lexicon_v4_hybrid.json, etc.),
update the sets below.  Both old and new parent-category names are
supported — keep the old aliases as long as any data or lexicon still
references them, and add new names as you introduce them.

An unclassified parent category silently produces zero patterns and
zero conflicts.  Use ``verify_coverage()`` to check after changes.

Terminology
-----------
- **modifier**: qualifies / describes the head (e.g. direction, size, clan)
- **head**: the semantic core — what the place *is* (e.g. terrain, water, settlement)
"""

from typing import Set, List, Tuple

# ---------------------------------------------------------------------------
# Categories that typically appear **first** in a bigram, modifying the head.
# ---------------------------------------------------------------------------
MODIFIER_CATEGORIES: Set[str] = {
    # v4 lexicon (2026-07-13): 9 parents, 53 subcategories
    "spatial",      # v4: direction + elevation + position etc.
    "clan",         # v4: general / cantonese / hakka / teochew
    "culture",      # v4: religion / auspicious / virtue / animal / community
    "modifier",     # v4: number / size / color / time / quality / suffix

    # v1 lexicon names
    "direction",    # renamed to "spatial" in v4

    # v4_hybrid / legacy lexicon names
    "symbolic",     # renamed to "culture" in v1/v4
    "size",         # merged into "modifier" in v1/v4
    "number",       # merged into "modifier" in v1/v4
    "color",        # merged into "modifier" in v1/v4
    "time",         # merged into "modifier" in v1/v4
    "shape",        # removed in v4
}

# ---------------------------------------------------------------------------
# Categories that form the **semantic core** — the "what" of a place name.
# ---------------------------------------------------------------------------
HEAD_CATEGORIES: Set[str] = {
    # v4 lexicon (2026-07-13): 9 parents, 53 subcategories
    "terrain",          # v4: peak_ridge / slope / valley / rock / flatland / surface
    "water",            # v4: river / stream / ditch / pond_lake / bay_port / ...
    "settlement",       # v4: village / dwelling / building / fortification / ...
    "agriculture",      # v4: field / crop / livestock / farming_infra
    "vegetation",       # v4: tree / bamboo / fruit / herb

    # v1 lexicon names — same as v4 for heads (no rename)

    # v4_hybrid / legacy lexicon names
    "mountain",         # merged into "terrain" in v1/v4
    "landform",         # merged into "terrain" in v1/v4
    "infrastructure",   # merged into "settlement" in v4, into "modifier" in v1
}

# ---------------------------------------------------------------------------
# Parent-category pairs considered semantically incompatible in one name.
# ---------------------------------------------------------------------------
INCOMPATIBLE_PAIRS: List[Tuple[str, str]] = [
    ("water", "terrain"),
]


# ---------------------------------------------------------------------------
# Verification helper
# ---------------------------------------------------------------------------
def verify_coverage(parent_categories: Set[str]) -> List[str]:
    """Check that every parent category is classified or explicitly skipped.

    Args:
        parent_categories: all unique parent-category names from a lexicon

    Returns:
        List of unclassified categories (empty = all covered)
    """
    skipped = {"other"}
    classified = MODIFIER_CATEGORIES | HEAD_CATEGORIES | skipped
    return sorted(c for c in parent_categories if c not in classified)
