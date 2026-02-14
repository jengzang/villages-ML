# Basic Usage Examples

This guide provides simple, copy-paste ready examples for getting started with the tendency analysis skill.

## Quick Start

### 1. Load Data and Create Analyzer

```python
from tendency_analysis.scripts.data_loader import load_village_data
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

# Load data from text file
data = load_village_data("阳春村庄名录.txt")

# Create analyzer
analyzer = TendencyAnalyzer(data)
```

### 2. Run Basic Analysis

```python
# Analyze all towns with default parameters
results = analyzer.analyze_tendencies(
    n=1,                    # Compare top/bottom 1 town
    high_threshold=10,      # Show chars with >10% tendency
    low_threshold=20,       # Show chars with >20% avoidance
    display_threshold=5     # Only analyze chars appearing in >5% of villages
)

# Print results to console
analyzer.print_results(results)
```

### 3. Analyze Specific Town

```python
# Analyze only one town
results = analyzer.analyze_tendencies(
    n=1,
    target_town="春城街道",
    high_threshold=10,
    low_threshold=20
)

analyzer.print_results(results)
```

## Complete Example

```python
#!/usr/bin/env python3
"""
Basic tendency analysis example
"""

from tendency_analysis.scripts.data_loader import load_village_data
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

def main():
    # Load data
    print("Loading village data...")
    data = load_village_data("阳春村庄名录.txt")
    print(f"Loaded {len(data)} towns")

    # Create analyzer
    print("Creating analyzer...")
    analyzer = TendencyAnalyzer(data)

    # Run analysis
    print("\\nAnalyzing tendencies...")
    results = analyzer.analyze_tendencies(
        n=1,
        high_threshold=10,
        low_threshold=20,
        display_threshold=5
    )

    # Display results
    analyzer.print_results(results)

if __name__ == "__main__":
    main()
```

## Using Example Data

If you don't have the full dataset, use the provided example data:

```python
from tendency_analysis.scripts.data_loader import load_from_json
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

# Load example data
data = load_from_json("tendency-analysis/assets/example-data.json")

# Create analyzer and run analysis
analyzer = TendencyAnalyzer(data)
results = analyzer.analyze_tendencies(n=1)
analyzer.print_results(results)
```

## Adjusting Parameters

### Conservative Analysis (Strong Patterns Only)

```python
results = analyzer.analyze_tendencies(
    n=1,                    # Single highest/lowest town
    high_threshold=20,      # Only very strong preferences
    low_threshold=30,       # Only very strong avoidances
    display_threshold=10    # Only common characters
)
```

### Comprehensive Analysis (More Results)

```python
results = analyzer.analyze_tendencies(
    n=2,                    # Top/bottom 2 towns
    high_threshold=5,       # Include moderate preferences
    low_threshold=10,       # Include moderate avoidances
    display_threshold=3     # Include less common characters
)
```

### Broad Pattern Analysis

```python
results = analyzer.analyze_tendencies(
    n=5,                    # Top/bottom 5 towns
    high_threshold=15,      # Focus on strong patterns
    low_threshold=20,
    display_threshold=8
)
```

## Exporting Results

### Export to JSON

```python
from tendency_analysis.scripts.data_loader import export_results
from datetime import datetime

# Run analysis
results = analyzer.analyze_tendencies(n=1)

# Export to JSON
metadata = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "parameters": "n=1, high_threshold=10, low_threshold=20"
}

export_results(
    results,
    "results.json",
    format='json',
    metadata=metadata
)
```

### Export to Markdown

```python
from tendency_analysis.scripts.formatter import format_results_markdown

# Run analysis
results = analyzer.analyze_tendencies(n=1)

# Format as markdown
markdown = format_results_markdown(results, analyzer)

# Save to file
with open("results.md", "w", encoding="utf-8") as f:
    f.write(markdown)
```

### Export to HTML

```python
from tendency_analysis.scripts.formatter import format_results_html

# Run analysis
results = analyzer.analyze_tendencies(n=1)

# Format as HTML
html = format_results_html(results, analyzer, title="阳春市村名倾向性分析")

# Save to file
with open("results.html", "w", encoding="utf-8") as f:
    f.write(html)
```

## Interpreting Results

### Understanding High Tendency

```
高倾向字 (在以下镇使用频率最高):
  田 (倾向值: +85.3%) - 在 [岗美镇] 中使用频率最高
```

**Interpretation:**
- Character "田" appears 85.3% more frequently in 岗美镇 than the overall average
- This indicates a strong preference for this character in that town
- Likely reflects agricultural naming patterns

### Understanding Low Tendency

```
低倾向字 (在以下镇使用频率最低):
  城 (倾向值: -92.1%) - 在 [岗美镇] 中使用频率最低
```

**Interpretation:**
- Character "城" appears 92.1% less frequently in 岗美镇 than average
- This indicates strong avoidance of this character
- Near -100% means the character is almost completely absent

## Common Patterns

### Urban vs Rural

Urban areas (街道) typically show:
- **High tendency:** 城, 街, 社, 区, 路
- **Low tendency:** 田, 垌, 坑, 寮, 塘

Rural areas (镇) typically show:
- **High tendency:** 田, 垌, 坑, 寮, 塘, 岗
- **Low tendency:** 城, 街, 社, 区, 路

### Geographic Features

Towns near water:
- **High tendency:** 河, 水, 江, 溪, 塘, 湖

Towns in mountainous areas:
- **High tendency:** 山, 岭, 坑, 岗, 峰

## Troubleshooting

### No Results Displayed

If you see "无符合条件的字符", try:

```python
# Lower the thresholds
results = analyzer.analyze_tendencies(
    n=1,
    high_threshold=5,       # Lower threshold
    low_threshold=10,       # Lower threshold
    display_threshold=2     # Lower threshold
)
```

### Too Many Results

If output is overwhelming, try:

```python
# Raise the thresholds
results = analyzer.analyze_tendencies(
    n=1,
    high_threshold=20,      # Higher threshold
    low_threshold=30,       # Higher threshold
    display_threshold=10    # Higher threshold
)
```

### File Not Found Error

Make sure the file path is correct:

```python
import os

# Check if file exists
file_path = "阳春村庄名录.txt"
if os.path.exists(file_path):
    data = load_village_data(file_path)
else:
    print(f"File not found: {file_path}")
    print(f"Current directory: {os.getcwd()}")
```

## Next Steps

- See [Advanced Usage](advanced-usage.md) for complex scenarios
- See [Integration Guide](integration.md) for using with existing code
- See [API Reference](../references/api-reference.md) for detailed documentation
