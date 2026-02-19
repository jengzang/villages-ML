"""Constants for preprocessing operations.

This module contains all configurable constants used in village name preprocessing,
including delimiters, modifiers, and homophone mappings.
"""

# Administrative delimiters used in village names
# These are checked in order (longer matches first for greedy matching)
DELIMITERS = ["社区", "村", "寨", "片", "管区", "农场", "区"]

# Subset of delimiters used in specific matching contexts
# (Used when we need to check for delimiter after a prefix)
DELIMITERS_SUBSET = ["社区", "村", "寨", "片", "管区", "农场", "区"]

# Size and direction modifiers that can prefix village names
MODIFIERS = ["大", "小", "新", "老", "東", "西", "南", "北", "上", "下"]

# Homophone pairs for Cantonese pronunciation variants
# Format: {standard_form: [variant1, variant2, ...]}
HOMOPHONE_PAIRS = {
    "湖下": ["湖厦", "湖夏"],
    "石": ["时"],
    # Add more pairs as needed
}

# Minimum number of Chinese characters required after prefix removal
MIN_LENGTH_DEFAULT = 2

# Minimum confidence score for automatic prefix removal
CONFIDENCE_THRESHOLD_DEFAULT = 0.7

# Confidence scores for different match types
CONFIDENCE_SCORES = {
    "rule1_delimiter": 1.0,      # Delimiter-based removal (highest confidence)
    "rule2_admin_match": 0.9,    # Admin village comparison
    "rule3_modifier": 0.9,       # Modifier-based match
    "rule5_identical": 1.0,      # Identical names (no removal)
    "none": 0.0,                 # No match found
}
