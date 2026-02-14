# Data Structures Reference

## Input Data Format

### Hierarchical Village Data Structure

The tendency analyzer expects a nested dictionary representing the administrative hierarchy of villages.

#### Schema

```python
{
    "Town Name 1": {
        "村民委员会": [
            "Committee Name 1",
            "Committee Name 2",
            ...
        ],
        "居民委员会": [
            "Committee Name 3",
            ...
        ],
        "社区": [
            "Community Name 1",
            ...
        ],
        "自然村": {
            "Committee Name 1": [
                "Village Name 1",
                "Village Name 2",
                ...
            ],
            "Committee Name 2": [
                "Village Name 3",
                ...
            ],
            ...
        }
    },
    "Town Name 2": {
        ...
    }
}
```

#### Hierarchy Levels

**Level 1: Towns (镇/街道)**
- Keys: Town names (string)
- Type: `Dict[str, Dict]`
- Example: `"春城街道"`, `"岗美镇"`

**Level 2: Administrative Categories**
- Keys: Category names (string)
  - `"村民委员会"`: Village committees
  - `"居民委员会"`: Resident committees
  - `"社区"`: Communities
  - `"自然村"`: Natural villages (special - contains nested dict)
- Type: `List[str]` for committees/communities, `Dict[str, List[str]]` for natural villages

**Level 3: Committees/Communities**
- For `"村民委员会"`, `"居民委员会"`, `"社区"`: List of committee/community names
- For `"自然村"`: Dictionary mapping committee names to village lists

**Level 4: Natural Villages**
- Keys: Committee names (string)
- Values: Lists of village names (string)
- Type: `List[str]`

#### Example

```python
{
    "春城街道": {
        "村民委员会": [
            "城西村民委员会",
            "城东村民委员会"
        ],
        "居民委员会": [
            "东湖居民委员会"
        ],
        "社区": [
            "春城社区"
        ],
        "自然村": {
            "城西村民委员会": [
                "田心村",
                "石桥村",
                "新村"
            ],
            "城东村民委员会": [
                "东门村",
                "河边村"
            ]
        }
    },
    "岗美镇": {
        "村民委员会": [
            "岗美村民委员会",
            "田头村民委员会"
        ],
        "自然村": {
            "岗美村民委员会": [
                "岗美村",
                "田垌村"
            ],
            "田头村民委员会": [
                "田头村",
                "水田村",
                "大田村"
            ]
        }
    }
}
```

### Validation Rules

#### Required Structure

1. **Minimum Towns**: At least 2 towns required for comparison
2. **Town Keys**: Non-empty strings
3. **Administrative Categories**: At least one of `"村民委员会"`, `"居民委员会"`, `"社区"`, or `"自然村"`
4. **Natural Villages**: Must be present and contain at least one committee with villages

#### Data Type Validation

```python
def validate_data_structure(data: dict) -> bool:
    """
    Validates input data structure.

    Returns:
        bool: True if valid, raises ValueError if invalid
    """
    # Check top level
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    if len(data) < 2:
        raise ValueError("At least 2 towns required for tendency analysis")

    # Check each town
    for town_name, town_data in data.items():
        if not isinstance(town_name, str) or not town_name:
            raise ValueError(f"Town name must be non-empty string: {town_name}")

        if not isinstance(town_data, dict):
            raise ValueError(f"Town data must be dictionary: {town_name}")

        # Check for natural villages
        if "自然村" not in town_data:
            raise ValueError(f"Town must have '自然村' key: {town_name}")

        natural_villages = town_data["自然村"]
        if not isinstance(natural_villages, dict):
            raise ValueError(f"'自然村' must be dictionary: {town_name}")

        # Check each committee
        for committee, villages in natural_villages.items():
            if not isinstance(committee, str) or not committee:
                raise ValueError(f"Committee name must be non-empty string: {committee}")

            if not isinstance(villages, list):
                raise ValueError(f"Villages must be list: {committee}")

            if not villages:
                raise ValueError(f"Committee must have at least one village: {committee}")

            for village in villages:
                if not isinstance(village, str) or not village:
                    raise ValueError(f"Village name must be non-empty string: {village}")

    return True
```

#### Data Quality Recommendations

**Minimum Sample Sizes:**
- At least 10-20 villages per town for stable statistics
- At least 5 towns for robust pattern detection
- Balanced dataset (similar village counts across towns) preferred

**Character Encoding:**
- UTF-8 encoding required
- Both simplified and traditional Chinese supported

**Text Cleaning:**
- Parentheses and content automatically filtered: `村庄(旧称)` → `村庄`
- No manual preprocessing required

---

## Output Data Format

### Analysis Results Structure

```python
{
    "Town Name 1": {
        "high_tendency": [
            (char, tendency_value, [town_list]),
            (char, tendency_value, [town_list]),
            ...
        ],
        "low_tendency": [
            (char, tendency_value, [town_list]),
            (char, tendency_value, [town_list]),
            ...
        ]
    },
    "Town Name 2": {
        ...
    }
}
```

#### Result Fields

**Town Name** (string)
- Key: Name of the analyzed town
- If `target_town=None`, contains results for all towns
- If `target_town="春城街道"`, contains only that town's results

**high_tendency** (list of tuples)
- Characters with positive tendency values above `high_threshold`
- Sorted by tendency value (descending)
- Each tuple: `(character, tendency_value, town_list)`

**low_tendency** (list of tuples)
- Characters with negative tendency values below `-low_threshold`
- Sorted by absolute tendency value (descending)
- Each tuple: `(character, tendency_value, town_list)`

#### Tuple Structure

```python
(
    char: str,              # Single Chinese character
    tendency_value: float,  # Tendency value as percentage (-100 to +∞)
    town_list: List[str]    # Towns in the high/low tendency group
)
```

**Example:**
```python
("田", 85.3, ["岗美镇"])
```

Interpretation: Character "田" has +85.3% tendency, meaning it appears 85.3% more frequently in the high-tendency group (岗美镇) compared to the overall average.

#### Complete Example

```python
{
    "春城街道": {
        "high_tendency": [
            ("城", 120.5, ["春城街道"]),
            ("街", 95.3, ["春城街道"]),
            ("社", 78.2, ["春城街道"])
        ],
        "low_tendency": [
            ("田", -85.7, ["岗美镇"]),
            ("垌", -92.1, ["岗美镇"]),
            ("坑", -88.4, ["河口镇"])
        ]
    },
    "岗美镇": {
        "high_tendency": [
            ("田", 145.8, ["岗美镇"]),
            ("垌", 132.4, ["岗美镇"]),
            ("坑", 98.7, ["岗美镇"])
        ],
        "low_tendency": [
            ("城", -95.2, ["春城街道"]),
            ("街", -98.1, ["春城街道"]),
            ("社", -91.3, ["春城街道"])
        ]
    }
}
```

---

## Internal Data Structures

### Character Frequency Data

#### char_town_counts

Maps characters to town-specific occurrence counts.

```python
{
    "田": {
        "春城街道": 5,
        "岗美镇": 45,
        "河口镇": 12,
        ...
    },
    "城": {
        "春城街道": 38,
        "岗美镇": 2,
        ...
    },
    ...
}
```

**Type:** `Dict[str, Dict[str, int]]`

#### town_total_counts

Maps towns to total character counts (sum of all characters in all villages).

```python
{
    "春城街道": 1250,
    "岗美镇": 980,
    "河口镇": 1100,
    ...
}
```

**Type:** `Dict[str, int]`

#### char_total_counts

Maps characters to overall occurrence counts across all towns.

```python
{
    "田": 125,
    "城": 87,
    "村": 456,
    ...
}
```

**Type:** `Dict[str, int]`

#### total_chars

Total character count across all villages in all towns.

```python
total_chars = 15780
```

**Type:** `int`

### Frequency Cache (OptimizedTendencyAnalyzer)

#### _frequency_cache

Precomputed frequency data for all characters.

```python
{
    "田": {
        "overall_frequency": 0.0079,  # 125 / 15780
        "town_frequencies": {
            "春城街道": 0.004,  # 5 / 1250
            "岗美镇": 0.0459,   # 45 / 980
            "河口镇": 0.0109,   # 12 / 1100
            ...
        }
    },
    ...
}
```

**Type:** `Dict[str, Dict[str, any]]`

**Benefits:**
- Eliminates redundant calculations
- ~4x speedup for repeated queries
- Enables fast character-specific lookups

#### _filtered_text_cache

Cached filtered village names (parentheses removed).

```python
{
    "村庄(旧称)": "村庄",
    "田心村(新村)": "田心村",
    ...
}
```

**Type:** `Dict[str, str]`

---

## JSON Export Format

### Standard JSON Output

```json
{
    "metadata": {
        "analysis_date": "2026-02-15",
        "parameters": {
            "n": 1,
            "high_threshold": 10,
            "low_threshold": 20,
            "display_threshold": 5
        },
        "data_summary": {
            "total_towns": 17,
            "total_villages": 1250,
            "total_characters_analyzed": 45
        }
    },
    "results": {
        "春城街道": {
            "high_tendency": [
                {
                    "character": "城",
                    "tendency_value": 120.5,
                    "towns": ["春城街道"],
                    "interpretation": "Strong preference"
                }
            ],
            "low_tendency": [
                {
                    "character": "田",
                    "tendency_value": -85.7,
                    "towns": ["岗美镇"],
                    "interpretation": "Strong avoidance"
                }
            ]
        }
    }
}
```

### Compact JSON Output

```json
{
    "春城街道": {
        "high": [["城", 120.5, ["春城街道"]], ["街", 95.3, ["春城街道"]]],
        "low": [["田", -85.7, ["岗美镇"]], ["垌", -92.1, ["岗美镇"]]]
    }
}
```

---

## Markdown Export Format

```markdown
# Village Name Tendency Analysis Results

**Analysis Date:** 2026-02-15
**Parameters:** n=1, high_threshold=10%, low_threshold=20%, display_threshold=5%

---

## 春城街道

### High Tendency Characters
Characters preferentially used in this town:

| Character | Tendency Value | High-Usage Towns |
|-----------|----------------|------------------|
| 城 | +120.5% | 春城街道 |
| 街 | +95.3% | 春城街道 |
| 社 | +78.2% | 春城街道 |

### Low Tendency Characters
Characters avoided in this town:

| Character | Tendency Value | Low-Usage Towns |
|-----------|----------------|-----------------|
| 田 | -85.7% | 岗美镇 |
| 垌 | -92.1% | 岗美镇 |
| 坑 | -88.4% | 河口镇 |

---

## 岗美镇

...
```

---

## Data Conversion Utilities

### Converting from Text File

```python
from tendency_analysis.scripts.data_loader import load_village_data

# Load from original text format
data = load_village_data("阳春村庄名录.txt")

# Data is now in the required hierarchical format
```

### Converting to JSON

```python
import json

# Export data structure to JSON
with open("village_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Loading from JSON

```python
from tendency_analysis.scripts.data_loader import load_from_json

data = load_from_json("village_data.json")
```
