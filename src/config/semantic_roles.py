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
    # v1 lexicon names (2026-07)
    "direction",
    "clan",
    "culture",   # was "symbolic" in older lexicons
    "modifier",  # v1 catch-all: size + number + color + shape + a few old-infra chars

    # v4_hybrid / legacy lexicon names
    "symbolic",  # renamed to "culture" in v1
    "size",
    "number",
    "color",
    "time",
    "shape",
}

# ---------------------------------------------------------------------------
# Categories that form the **semantic core** — the "what" of a place name.
# ---------------------------------------------------------------------------
HEAD_CATEGORIES: Set[str] = {
    # v1 lexicon names (2026-07)
    "terrain",      # was "mountain" + "landform" in older lexicons
    "water",
    "settlement",
    "agriculture",
    "vegetation",

    # v4_hybrid / legacy lexicon names
    "mountain",     # merged into "terrain" in v1
    "landform",     # merged into "terrain" in v1
    "infrastructure",  # merged into "modifier" in v1, but linguistically a head
}

# ---------------------------------------------------------------------------
# Parent-category pairs considered semantically incompatible in one name.
# ---------------------------------------------------------------------------
INCOMPATIBLE_PAIRS: List[Tuple[str, str]] = [
    ("water", "terrain"),
    ("water", "mountain"),
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
