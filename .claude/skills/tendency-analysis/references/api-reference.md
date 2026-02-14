# API Reference

## Classes

### TendencyAnalyzer

Basic tendency analyzer for village name character analysis.

#### Constructor

```python
TendencyAnalyzer(data: dict)
```

**Parameters:**
- `data` (dict): Hierarchical village data structure with towns, committees, and villages

**Raises:**
- `ValueError`: If data structure is invalid or contains fewer than 2 towns

**Example:**
```python
analyzer = TendencyAnalyzer({
    "Town1": {"自然村": {"Committee1": ["Village1", "Village2"]}},
    "Town2": {"自然村": {"Committee2": ["Village3", "Village4"]}}
})
```

#### Methods

##### analyze_tendencies()

```python
analyze_tendencies(
    n: int = 1,
    target_town: str | None = None,
    high_threshold: float = 10,
    low_threshold: float = 20,
    display_threshold: float = 5
) -> dict
```

Analyzes character usage tendencies across towns.

**Parameters:**
- `n` (int, default=1): Number of top/bottom towns to include in high/low tendency groups
  - `n=1`: Most conservative, single highest/lowest town
  - `n=2-3`: Balanced approach
  - `n>=5`: Broader patterns
- `target_town` (str | None, default=None): Specific town to analyze, or None for all towns
- `high_threshold` (float, default=10): Minimum tendency value (%) to display high-tendency characters
- `low_threshold` (float, default=20): Minimum absolute tendency value (%) to display low-tendency characters
- `display_threshold` (float, default=5): Minimum overall frequency (%) to analyze a character

**Returns:**
- dict: Results dictionary with structure:
  ```python
  {
      "Town Name": {
          "high_tendency": [
              (char, tendency_value, [town_list]),
              ...
          ],
          "low_tendency": [
              (char, tendency_value, [town_list]),
              ...
          ]
      }
  }
  ```

**Example:**
```python
# Analyze all towns
results = analyzer.analyze_tendencies(n=1, high_threshold=10, low_threshold=20)

# Analyze specific town
results = analyzer.analyze_tendencies(n=1, target_town="春城街道")
```

##### print_results()

```python
print_results(results: dict) -> None
```

Prints formatted analysis results to console.

**Parameters:**
- `results` (dict): Results dictionary from `analyze_tendencies()`

**Output Format:**
```
=== 春城街道 ===

高倾向字 (在以下镇使用频率最高):
  田 (倾向值: +85.3%) - 在 [岗美镇] 中使用频率最高
  ...

低倾向字 (在以下镇使用频率最低):
  城 (倾向值: -92.1%) - 在 [岗美镇] 中使用频率最低
  ...
```

**Example:**
```python
results = analyzer.analyze_tendencies(n=1)
analyzer.print_results(results)
```

#### Private Methods

##### _calculate_frequencies()

```python
_calculate_frequencies() -> None
```

Calculates character frequencies for all towns. Called automatically during initialization.

**Internal Data Structures:**
- `self.char_town_counts`: Dict mapping characters to town-specific counts
- `self.town_total_counts`: Dict mapping towns to total character counts
- `self.char_total_counts`: Dict mapping characters to overall counts
- `self.total_chars`: Total character count across all villages

##### _filter_chars()

```python
_filter_chars(text: str) -> str
```

Filters parentheses and their content from text.

**Parameters:**
- `text` (str): Input text

**Returns:**
- str: Filtered text with parentheses removed

**Example:**
```python
filtered = analyzer._filter_chars("村庄(旧称)")  # Returns: "村庄"
```

---

### OptimizedTendencyAnalyzer

Optimized analyzer with caching for improved performance on large datasets or repeated queries.

**Inherits from:** `TendencyAnalyzer`

**Performance:** ~4x faster for repeated queries due to frequency caching

#### Constructor

```python
OptimizedTendencyAnalyzer(data: dict)
```

**Parameters:**
- `data` (dict): Hierarchical village data structure

**Additional Initialization:**
- Precomputes all character frequencies
- Initializes frequency cache
- Initializes filtered text cache

**Example:**
```python
analyzer = OptimizedTendencyAnalyzer(data)
```

#### Additional Methods

##### get_frequencies()

```python
get_frequencies(char: str) -> dict
```

Gets cached frequency data for a specific character.

**Parameters:**
- `char` (str): Character to query

**Returns:**
- dict: Frequency data with structure:
  ```python
  {
      "overall_frequency": float,  # Overall frequency (0-1)
      "town_frequencies": {
          "Town1": float,
          "Town2": float,
          ...
      }
  }
  ```

**Example:**
```python
freq_data = analyzer.get_frequencies("田")
print(f"Overall: {freq_data['overall_frequency']:.2%}")
print(f"Town frequencies: {freq_data['town_frequencies']}")
```

##### get_char_statistics()

```python
get_char_statistics(char: str) -> dict
```

Gets comprehensive statistics for a specific character.

**Parameters:**
- `char` (str): Character to query

**Returns:**
- dict: Statistics with structure:
  ```python
  {
      "overall_frequency": float,      # Overall frequency (0-1)
      "town_frequencies": dict,        # Town-specific frequencies
      "town_count": int,               # Number of towns using this char
      "total_count": int,              # Total occurrences
      "max_frequency": float,          # Highest town frequency
      "min_frequency": float,          # Lowest town frequency
      "max_town": str,                 # Town with highest frequency
      "min_town": str                  # Town with lowest frequency
  }
  ```

**Example:**
```python
stats = analyzer.get_char_statistics("田")
print(f"Appears in {stats['town_count']} towns")
print(f"Most common in: {stats['max_town']} ({stats['max_frequency']:.2%})")
```

#### Private Methods

##### _precompute_frequencies()

```python
_precompute_frequencies() -> None
```

Precomputes and caches all character frequencies. Called automatically during initialization.

##### _get_top_n_with_ties()

```python
_get_top_n_with_ties(
    sorted_items: list,
    n: int,
    reverse: bool = True
) -> list
```

Gets top-n items with tie handling.

**Parameters:**
- `sorted_items` (list): Sorted list of (town, frequency) tuples
- `n` (int): Number of items to select
- `reverse` (bool, default=True): If True, select highest values; if False, select lowest

**Returns:**
- list: Selected items including ties

##### _format_town_results()

```python
_format_town_results(
    char: str,
    tendency_value: float,
    towns: list
) -> tuple
```

Formats results for a single character.

**Parameters:**
- `char` (str): Character
- `tendency_value` (float): Calculated tendency value
- `towns` (list): List of towns in the tendency group

**Returns:**
- tuple: (char, tendency_value, towns)

---

## Utility Functions

### data_loader Module

#### load_village_data()

```python
load_village_data(file_path: str) -> dict
```

Loads village data from text file using the existing parser.

**Parameters:**
- `file_path` (str): Path to village registry text file

**Returns:**
- dict: Parsed hierarchical village data

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `UnicodeDecodeError`: If file encoding is incorrect

**Example:**
```python
from tendency_analysis.scripts.data_loader import load_village_data
data = load_village_data("阳春村庄名录.txt")
```

#### validate_data_structure()

```python
validate_data_structure(data: dict) -> bool
```

Validates input data structure.

**Parameters:**
- `data` (dict): Data to validate

**Returns:**
- bool: True if valid, False otherwise

**Validation Checks:**
- Minimum 2 towns
- Proper hierarchical structure
- Required keys present
- Data types correct

#### load_from_json()

```python
load_from_json(file_path: str) -> dict
```

Loads pre-parsed JSON data.

**Parameters:**
- `file_path` (str): Path to JSON file

**Returns:**
- dict: Parsed data

#### export_results()

```python
export_results(
    results: dict,
    output_path: str,
    format: str = 'json'
) -> None
```

Exports analysis results to file.

**Parameters:**
- `results` (dict): Results from `analyze_tendencies()`
- `output_path` (str): Output file path
- `format` (str, default='json'): Output format ('json', 'markdown', 'txt')

**Example:**
```python
export_results(results, "output.json", format='json')
export_results(results, "output.md", format='markdown')
```

### formatter Module

#### format_results_table()

```python
format_results_table(results: dict, analyzer: TendencyAnalyzer) -> str
```

Formats results as ASCII table.

**Parameters:**
- `results` (dict): Analysis results
- `analyzer` (TendencyAnalyzer): Analyzer instance for accessing frequency data

**Returns:**
- str: Formatted ASCII table

#### format_results_markdown()

```python
format_results_markdown(results: dict, analyzer: TendencyAnalyzer) -> str
```

Formats results as markdown.

**Parameters:**
- `results` (dict): Analysis results
- `analyzer` (TendencyAnalyzer): Analyzer instance

**Returns:**
- str: Markdown-formatted results

#### format_results_html()

```python
format_results_html(results: dict, analyzer: TendencyAnalyzer) -> str
```

Formats results as HTML.

**Parameters:**
- `results` (dict): Analysis results
- `analyzer` (TendencyAnalyzer): Analyzer instance

**Returns:**
- str: HTML-formatted results

#### generate_summary_report()

```python
generate_summary_report(results: dict, analyzer: TendencyAnalyzer) -> str
```

Generates comprehensive analysis report.

**Parameters:**
- `results` (dict): Analysis results
- `analyzer` (TendencyAnalyzer): Analyzer instance

**Returns:**
- str: Comprehensive report with statistics and interpretations

---

## Type Hints

```python
from typing import Dict, List, Tuple, Optional

# Data structure types
VillageData = Dict[str, Dict[str, any]]
TownFrequencies = Dict[str, float]
CharCounts = Dict[str, int]

# Result types
TendencyResult = Tuple[str, float, List[str]]  # (char, tendency_value, towns)
AnalysisResults = Dict[str, Dict[str, List[TendencyResult]]]

# Statistics types
CharStatistics = Dict[str, any]  # See get_char_statistics() return type
FrequencyData = Dict[str, any]   # See get_frequencies() return type
```

---

## Error Handling

### Common Exceptions

**ValueError:**
- Invalid data structure (fewer than 2 towns)
- Invalid parameter values (negative thresholds, n < 1)
- Missing required keys in data structure

**KeyError:**
- Target town not found in data
- Invalid character query

**FileNotFoundError:**
- Data file doesn't exist

**UnicodeDecodeError:**
- Incorrect file encoding (should be UTF-8)

### Example Error Handling

```python
try:
    analyzer = TendencyAnalyzer(data)
    results = analyzer.analyze_tendencies(n=1, target_town="NonexistentTown")
except ValueError as e:
    print(f"Invalid data or parameters: {e}")
except KeyError as e:
    print(f"Town not found: {e}")
```
