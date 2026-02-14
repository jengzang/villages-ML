# Village Name Tendency Analysis Skill

A comprehensive Claude Code skill for analyzing character usage patterns in Chinese village names using statistical tendency analysis.

## Overview

This skill provides sophisticated tools for identifying which Chinese characters are preferentially used or avoided in specific regions compared to overall patterns. Unlike simple frequency counting, tendency analysis reveals meaningful cultural, linguistic, and historical patterns through relative frequency comparison.

## Quick Start

```python
from tendency_analysis.scripts.data_loader import load_village_data
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

# Load data
data = load_village_data("阳春村庄名录.txt")

# Create analyzer
analyzer = TendencyAnalyzer(data)

# Run analysis
results = analyzer.analyze_tendencies(n=1, high_threshold=10, low_threshold=20)

# Display results
analyzer.print_results(results)
```

## Directory Structure

```
tendency-analysis/
├── SKILL.md                          # Main skill documentation (~1,800 words)
├── references/
│   ├── algorithm-theory.md           # Complete algorithm documentation (1,017 lines)
│   ├── api-reference.md              # Function signatures and parameters
│   ├── data-structures.md            # Input/output format specifications
│   └── performance-guide.md          # Optimization strategies and benchmarks
├── scripts/
│   ├── analyzer.py                   # Basic TendencyAnalyzer class
│   ├── optimized_analyzer.py         # OptimizedTendencyAnalyzer with caching
│   ├── data_loader.py                # Data loading and export utilities
│   └── formatter.py                  # Result formatting (table, markdown, HTML)
├── assets/
│   ├── example-data.json             # Sample village dataset
│   ├── example-output.txt            # Sample analysis results
│   └── config-template.json          # Configuration template
└── examples/
    ├── basic-usage.md                # Quick start guide
    ├── advanced-usage.md             # Complex scenarios and optimization
    └── integration.md                # Integration with existing code
```

## Features

- **Two Analyzer Implementations:**
  - `TendencyAnalyzer`: Basic implementation, easy to understand
  - `OptimizedTendencyAnalyzer`: Cached implementation, ~4x faster for repeated queries

- **Flexible Analysis:**
  - Analyze all towns or specific towns
  - Adjustable thresholds for filtering results
  - Configurable group sizes (n parameter)

- **Multiple Output Formats:**
  - Console output with Chinese formatting
  - JSON export for programmatic use
  - Markdown for documentation
  - HTML for web display
  - ASCII tables for reports

- **Character-Specific Queries:**
  - Get detailed statistics for any character
  - View frequency distribution across towns
  - Identify highest/lowest usage regions

- **Comprehensive Documentation:**
  - 1,800-word skill guide
  - 1,017-line algorithm theory document
  - Complete API reference
  - Performance optimization guide
  - Multiple usage examples

## Installation

The skill is self-contained and requires only Python 3.7+. No external dependencies beyond the Python standard library.

```bash
# No installation needed - just use the scripts directly
cd tendency-analysis/scripts
python analyzer.py
```

## Usage Examples

### Basic Analysis

```python
# Analyze all towns
results = analyzer.analyze_tendencies(n=1)
analyzer.print_results(results)
```

### Specific Town Analysis

```python
# Analyze one town
results = analyzer.analyze_tendencies(n=1, target_town="春城街道")
analyzer.print_results(results)
```

### Character Statistics

```python
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer

analyzer = OptimizedTendencyAnalyzer(data)
stats = analyzer.get_char_statistics("田")
print(f"Overall frequency: {stats['overall_frequency']:.2%}")
print(f"Appears in {stats['town_count']} towns")
```

### Export Results

```python
from tendency_analysis.scripts.data_loader import export_results

# Export to markdown
export_results(results, "results.md", format='markdown')

# Export to JSON
export_results(results, "results.json", format='json')

# Export to HTML
export_results(results, "results.html", format='html')
```

## Documentation

- **[SKILL.md](SKILL.md)**: Main skill documentation with overview, concepts, and workflow
- **[Algorithm Theory](references/algorithm-theory.md)**: Complete mathematical derivation and examples
- **[API Reference](references/api-reference.md)**: Function signatures and parameters
- **[Data Structures](references/data-structures.md)**: Input/output format specifications
- **[Performance Guide](references/performance-guide.md)**: Optimization strategies
- **[Basic Usage](examples/basic-usage.md)**: Quick start guide
- **[Advanced Usage](examples/advanced-usage.md)**: Complex scenarios
- **[Integration Guide](examples/integration.md)**: Using with existing code

## Key Concepts

### Tendency Value

The tendency value measures how much more (or less) frequently a character appears in a region compared to the overall average:

```
T = (group_avg - overall_avg) / overall_avg × 100%
```

- **Positive values**: Character is preferred in the region
- **Negative values**: Character is avoided in the region
- **Near zero**: Character usage matches overall average

### Parameters

- **n**: Number of top/bottom towns in tendency groups (1-5 typical)
- **high_threshold**: Minimum tendency value (%) to display high-tendency characters (5-20 typical)
- **low_threshold**: Minimum absolute tendency value (%) to display low-tendency characters (15-30 typical)
- **display_threshold**: Minimum overall frequency (%) to analyze a character (3-10 typical)

## Performance

- **Basic Analyzer:**
  - Initialization: ~10-50ms
  - Single analysis: ~50-200ms
  - Memory: ~1-5 MB

- **Optimized Analyzer:**
  - Initialization: ~100-500ms (precomputation)
  - Single analysis: ~15-50ms (4x faster)
  - Memory: ~5-20 MB (caching)

Break-even point: ~3-4 analyses on the same dataset

## Examples with Sample Data

The `assets/` directory includes sample data for testing:

```python
from tendency_analysis.scripts.data_loader import load_from_json
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

# Load example data
data = load_from_json("tendency-analysis/assets/example-data.json")

# Run analysis
analyzer = TendencyAnalyzer(data)
results = analyzer.analyze_tendencies(n=1)
analyzer.print_results(results)
```

## Skill Activation

This skill is automatically activated when users ask about:
- "分析倾向性" (analyze tendency)
- "村名分析" (village name analysis)
- "倾向值" (tendency value)
- "高倾向字" / "低倾向字" (high/low tendency characters)
- "naming patterns"
- "character frequency"
- Toponymy research or dialect studies

## Contributing

This skill is part of the getvillagename project. For issues or improvements:
1. Test changes with the example data
2. Update relevant documentation
3. Ensure backward compatibility
4. Add examples for new features

## License

Part of the getvillagename project. See project root for license information.

## Version History

- **v1.0.0** (2026-02-15): Initial release
  - Basic and optimized analyzers
  - Complete documentation suite
  - Multiple output formats
  - Example data and configurations

## Contact

For questions or support, refer to the main project documentation or create an issue in the project repository.
