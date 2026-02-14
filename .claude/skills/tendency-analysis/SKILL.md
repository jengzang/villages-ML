---
name: tendency-analysis
version: 1.0.0
description: This skill should be used when the user asks to "分析倾向性", "analyze tendency", "村名分析", "character frequency", mentions "倾向值", "tendency value", "高倾向字", "低倾向字", "naming patterns", "village name analysis", "地名统计", or discusses toponymy research, dialect studies, or regional naming preferences in Chinese geographic data.
---

# Village Name Tendency Analysis Skill

## Overview

The Village Name Tendency Analysis skill provides a sophisticated statistical framework for analyzing character usage patterns in Chinese geographic names, specifically designed for studying village naming conventions across different administrative regions.

Unlike simple frequency counting, this skill implements a **relative frequency analysis** that identifies which characters are preferentially used or avoided in specific regions compared to the overall dataset. This approach reveals meaningful cultural, linguistic, and historical patterns that absolute counts cannot capture.

**Core Concept:** The tendency value (倾向值) measures how much more (or less) frequently a character appears in a specific region compared to its average usage across all regions. A high positive tendency indicates the character is preferred in that region; a high negative tendency indicates it's avoided.

**Key Insight:** A character appearing 10 times in a small town with 50 villages has much higher significance than appearing 10 times in a large town with 500 villages. Tendency analysis captures this relative importance through statistical normalization.

**Applications:**
- Toponymy research: Understanding regional naming preferences
- Dialect studies: Identifying phonetic or semantic patterns
- Cultural geography: Revealing historical migration and settlement patterns
- Linguistic analysis: Studying character usage evolution

## When to Use This Skill

**Use this skill when:**
- Analyzing naming patterns across multiple administrative regions (towns, counties, districts)
- Identifying characters that are regionally preferred or avoided
- Comparing character usage between specific regions and overall trends
- Researching cultural or linguistic influences on place names
- Studying toponymic patterns in Chinese geographic data

**Don't use this skill for:**
- Simple character frequency counting (use basic statistics instead)
- Single-region analysis without comparison (no baseline for tendency)
- Non-hierarchical data (requires grouped data by region)
- Small datasets (minimum 2 regions, 10-20 samples per region recommended)

## Core Concepts

### Frequency vs Count

**Count** is the absolute number of occurrences: "田" appears 45 times in Town A.

**Frequency** is the relative occurrence rate: "田" appears in 30% of village names in Town A (45 occurrences / 150 villages).

Tendency analysis uses frequency because it normalizes for region size, making comparisons meaningful across regions with different numbers of villages.

### Tendency Value Formula

The tendency value T for a character in a region is calculated as:

```
T = (group_avg - overall_avg) / overall_avg × 100%
```

Where:
- `group_avg`: Average frequency of the character in the target region group
- `overall_avg`: Average frequency of the character across all regions

**Example:**
- Character "田" appears in 30% of villages in Town A (group_avg = 0.30)
- Character "田" appears in 15% of villages overall (overall_avg = 0.15)
- Tendency value: (0.30 - 0.15) / 0.15 = 1.0 = 100%

This means "田" is used 100% more frequently in Town A than average, indicating a strong preference.

### High and Low Tendency Groups

To identify regional patterns, the algorithm:

1. **Ranks all regions** by how frequently they use each character
2. **Selects top-n regions** (high tendency group) - regions that use the character most
3. **Selects bottom-n regions** (low tendency group) - regions that use the character least
4. **Calculates tendency values** for each group relative to the overall average

The parameter `n` controls group size:
- `n=1`: Most conservative, compares single highest/lowest region
- `n=2-3`: Balanced, reduces noise while maintaining specificity
- `n=5+`: Broader patterns, may dilute regional specificity

### Threshold Filtering

Three thresholds control which results are displayed:

**high_threshold** (default: 10): Minimum tendency value (%) to display high-tendency characters
- Higher values show only strongly preferred characters
- Typical range: 5-20%

**low_threshold** (default: 20): Minimum absolute tendency value (%) to display low-tendency characters
- Higher values show only strongly avoided characters
- Typically higher than high_threshold because avoidance patterns are often stronger
- Typical range: 15-30%

**display_threshold** (default: 5): Minimum overall frequency (%) required to analyze a character
- Filters out rare characters that may have unstable statistics
- Prevents noise from characters appearing in only 1-2 villages
- Typical range: 3-10%

## Data Requirements

### Input Format

The skill expects a hierarchical dictionary structure:

```python
{
    "Town Name 1": {
        "村民委员会": ["Committee1", "Committee2"],
        "自然村": {
            "Committee1": ["Village1", "Village2", "Village3"],
            "Committee2": ["Village4", "Village5"]
        }
    },
    "Town Name 2": {
        "村民委员会": ["Committee3"],
        "自然村": {
            "Committee3": ["Village6", "Village7"]
        }
    }
}
```

**Required structure:**
- Top level: Town names (镇/街道)
- Second level: Administrative categories (村民委员会, 居民委员会, 社区)
- Third level: Committee names or natural village mappings
- Leaf level: Village names (自然村)

### Data Quality Requirements

**Minimum requirements:**
- At least 2 towns for comparison
- At least 10-20 villages per town for stable statistics
- Consistent encoding (UTF-8)
- Clean text (the algorithm automatically filters parentheses)

**Recommended:**
- 5+ towns for robust pattern detection
- 30+ villages per town for reliable tendency values
- Balanced dataset (similar numbers of villages across towns)

### Preprocessing

The algorithm automatically:
- Filters parentheses and content: `(旧称)` → removed
- Extracts natural village names from the hierarchy
- Handles both simplified and traditional Chinese characters

## Basic Workflow

### Step 1: Load and Prepare Data

```python
from tendency_analysis.scripts.data_loader import load_village_data
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

# Load data from text file
data = load_village_data("阳春村庄名录.txt")

# Or load from JSON
# data = load_from_json("village_data.json")
```

### Step 2: Create Analyzer

```python
# Create analyzer instance
analyzer = TendencyAnalyzer(data)
```

### Step 3: Run Analysis

```python
# Analyze all towns (compare each town against overall average)
results = analyzer.analyze_tendencies(
    n=1,                      # Top/bottom 1 town
    target_town=None,         # None = analyze all towns
    high_threshold=10,        # Show high-tendency chars with T > 10%
    low_threshold=20,         # Show low-tendency chars with |T| > 20%
    display_threshold=5       # Only analyze chars appearing in > 5% of villages
)

# Analyze specific town
results = analyzer.analyze_tendencies(
    n=1,
    target_town="春城街道",
    high_threshold=10,
    low_threshold=20,
    display_threshold=5
)
```

### Step 4: Display Results

```python
# Print formatted results to console
analyzer.print_results(results)

# Or export to file
from tendency_analysis.scripts.formatter import format_results_markdown
markdown_output = format_results_markdown(results, analyzer)
with open("results.md", "w", encoding="utf-8") as f:
    f.write(markdown_output)
```

### Parameter Selection Guide

**For initial exploration:**
- `n=1`, `high_threshold=10`, `low_threshold=20`, `display_threshold=5`
- Conservative settings reveal strongest patterns

**For detailed analysis:**
- `n=2-3`, `high_threshold=5`, `low_threshold=15`, `display_threshold=3`
- Captures more nuanced patterns, includes more characters

**For broad patterns:**
- `n=5`, `high_threshold=15`, `low_threshold=25`, `display_threshold=10`
- Focuses on very strong, widespread patterns

## Output Interpretation

### Result Structure

```python
{
    "Town Name": {
        "high_tendency": [
            ("字", tendency_value, [town_list]),
            ...
        ],
        "low_tendency": [
            ("字", tendency_value, [town_list]),
            ...
        ]
    }
}
```

### Reading High Tendency Results

```
高倾向字 (在以下镇使用频率最高):
  田 (倾向值: +85.3%) - 在 [岗美镇] 中使用频率最高
```

**Interpretation:**
- "田" appears 85.3% more frequently in 岗美镇 than the overall average
- This suggests agricultural naming preferences in this town
- Strong positive tendency indicates cultural or geographic significance

### Reading Low Tendency Results

```
低倾向字 (在以下镇使用频率最低):
  城 (倾向值: -92.1%) - 在 [岗美镇] 中使用频率最低
```

**Interpretation:**
- "城" appears 92.1% less frequently in 岗美镇 than average
- Near -100% indicates the character is almost completely avoided
- May reflect rural vs urban naming patterns

### Practical Interpretation Tips

1. **High tendency (50-100%+)**: Strong regional preference, likely cultural/geographic significance
2. **Moderate tendency (20-50%)**: Notable pattern, worth investigating
3. **Low tendency (-50% to -80%)**: Character is avoided but not absent
4. **Very low tendency (-90% to -100%)**: Character is almost completely absent

## Advanced Features

### Custom Thresholds

Adjust thresholds to focus on specific patterns:

```python
# Focus on very strong patterns only
results = analyzer.analyze_tendencies(
    n=1,
    high_threshold=50,    # Only show chars with 50%+ tendency
    low_threshold=70,     # Only show chars with 70%+ avoidance
    display_threshold=10  # Only common characters
)
```

### Optimized Analyzer

For large datasets or repeated queries, use the optimized analyzer:

```python
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer

# Precomputes and caches frequencies for 4x speedup
analyzer = OptimizedTendencyAnalyzer(data)

# Same interface as basic analyzer
results = analyzer.analyze_tendencies(n=1)

# Additional features: query specific characters
char_stats = analyzer.get_char_statistics("田")
print(f"Overall frequency: {char_stats['overall_frequency']:.2%}")
print(f"Appears in {char_stats['town_count']} towns")
```

### Character-Specific Queries

```python
# Get detailed statistics for a specific character
stats = analyzer.get_char_statistics("田")
# Returns: overall_frequency, town_frequencies, town_count, total_count
```

### Batch Analysis

```python
# Analyze multiple towns
towns_to_analyze = ["春城街道", "岗美镇", "河口镇"]
all_results = {}

for town in towns_to_analyze:
    all_results[town] = analyzer.analyze_tendencies(
        n=1,
        target_town=town
    )
```

## References

For detailed technical documentation, see:

- **[Algorithm Theory](references/algorithm-theory.md)**: Complete mathematical derivation, examples, and edge cases (1,017 lines)
- **[API Reference](references/api-reference.md)**: Function signatures, parameters, and return types
- **[Data Structures](references/data-structures.md)**: Input/output format specifications and validation
- **[Performance Guide](references/performance-guide.md)**: Optimization strategies and benchmarks

For practical examples, see:

- **[Basic Usage](examples/basic-usage.md)**: Quick start guide with copy-paste examples
- **[Advanced Usage](examples/advanced-usage.md)**: Complex scenarios and custom configurations
- **[Integration Guide](examples/integration.md)**: Using the skill with existing codebases

For sample data and configurations:

- **[Example Data](assets/example-data.json)**: Sample village dataset
- **[Example Output](assets/example-output.txt)**: Sample analysis results
- **[Config Template](assets/config-template.json)**: Configuration file template
