# Advanced Usage Examples

This guide covers advanced scenarios, custom configurations, and optimization techniques.

## Using the Optimized Analyzer

For large datasets or repeated queries, use the optimized analyzer:

```python
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer
from tendency_analysis.scripts.data_loader import load_village_data

# Load data
data = load_village_data("阳春村庄名录.txt")

# Create optimized analyzer (slower init, faster queries)
analyzer = OptimizedTendencyAnalyzer(data)

# Fast repeated queries
results1 = analyzer.analyze_tendencies(n=1, high_threshold=10)
results2 = analyzer.analyze_tendencies(n=2, high_threshold=5)
results3 = analyzer.analyze_tendencies(n=1, target_town="春城街道")

# All queries after the first are ~4x faster
```

## Character-Specific Queries

Query statistics for specific characters:

```python
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer

analyzer = OptimizedTendencyAnalyzer(data)

# Get comprehensive statistics for a character
stats = analyzer.get_char_statistics("田")

print(f"Character: 田")
print(f"Overall frequency: {stats['overall_frequency']:.2%}")
print(f"Appears in {stats['town_count']} towns")
print(f"Total occurrences: {stats['total_count']}")
print(f"Highest frequency: {stats['max_frequency']:.2%} in {stats['max_town']}")
print(f"Lowest frequency: {stats['min_frequency']:.2%} in {stats['min_town']}")

# Get just frequency data
freq_data = analyzer.get_frequencies("田")
print(f"\\nTown-specific frequencies:")
for town, freq in freq_data['town_frequencies'].items():
    print(f"  {town}: {freq:.2%}")
```

## Batch Processing Multiple Towns

Analyze multiple towns efficiently:

```python
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer

analyzer = OptimizedTendencyAnalyzer(data)

# List of towns to analyze
towns_to_analyze = ["春城街道", "岗美镇", "河口镇", "潭水镇"]

# Batch analysis
all_results = {}
for town in towns_to_analyze:
    results = analyzer.analyze_tendencies(
        n=1,
        target_town=town,
        high_threshold=10,
        low_threshold=20
    )
    all_results.update(results)

# Process all results
for town, town_results in all_results.items():
    print(f"\\n=== {town} ===")
    print(f"High tendency chars: {len(town_results['high_tendency'])}")
    print(f"Low tendency chars: {len(town_results['low_tendency'])}")
```

## Custom Threshold Configurations

### Find Only Very Strong Patterns

```python
# Ultra-conservative: only extreme patterns
results = analyzer.analyze_tendencies(
    n=1,
    high_threshold=50,      # 50%+ increase
    low_threshold=70,       # 70%+ decrease
    display_threshold=15    # Only very common chars
)
```

### Comprehensive Character Coverage

```python
# Include rare characters and weak patterns
results = analyzer.analyze_tendencies(
    n=3,                    # Broader groups
    high_threshold=3,       # Include weak preferences
    low_threshold=5,        # Include weak avoidances
    display_threshold=1     # Include rare characters
)
```

### Focus on Common Characters Only

```python
# Analyze only frequently-used characters
results = analyzer.analyze_tendencies(
    n=2,
    high_threshold=10,
    low_threshold=15,
    display_threshold=20    # Only chars in 20%+ of villages
)
```

## Data Filtering and Preprocessing

### Filter Towns by Village Count

```python
def filter_towns_by_size(data, min_villages=15, max_villages=None):
    """Keep only towns with village count in specified range."""
    filtered = {}
    for town, town_data in data.items():
        village_count = sum(
            len(villages)
            for villages in town_data.get('自然村', {}).values()
        )
        if village_count >= min_villages:
            if max_villages is None or village_count <= max_villages:
                filtered[town] = town_data
    return filtered

# Use filtered data
filtered_data = filter_towns_by_size(data, min_villages=20)
analyzer = TendencyAnalyzer(filtered_data)
```

### Exclude Specific Towns

```python
def exclude_towns(data, exclude_list):
    """Remove specific towns from analysis."""
    return {
        town: town_data
        for town, town_data in data.items()
        if town not in exclude_list
    }

# Exclude urban areas to focus on rural patterns
rural_data = exclude_towns(data, ["春城街道", "春湾街道"])
analyzer = TendencyAnalyzer(rural_data)
```

### Include Only Specific Towns

```python
def include_only_towns(data, include_list):
    """Keep only specific towns."""
    return {
        town: town_data
        for town, town_data in data.items()
        if town in include_list
    }

# Compare only specific towns
comparison_data = include_only_towns(data, ["岗美镇", "河口镇", "潭水镇"])
analyzer = TendencyAnalyzer(comparison_data)
```

## Comparative Analysis

### Compare Urban vs Rural Patterns

```python
# Analyze urban areas
urban_towns = ["春城街道", "春湾街道"]
urban_data = include_only_towns(data, urban_towns)
urban_analyzer = TendencyAnalyzer(urban_data)
urban_results = urban_analyzer.analyze_tendencies(n=1)

# Analyze rural areas
rural_towns = [t for t in data.keys() if t not in urban_towns]
rural_data = include_only_towns(data, rural_towns)
rural_analyzer = TendencyAnalyzer(rural_data)
rural_results = rural_analyzer.analyze_tendencies(n=1)

# Compare results
print("Urban high-tendency characters:")
for town, results in urban_results.items():
    for char, value, _ in results['high_tendency'][:5]:
        print(f"  {char}: +{value:.1f}%")

print("\\nRural high-tendency characters:")
for town, results in rural_results.items():
    for char, value, _ in results['high_tendency'][:5]:
        print(f"  {char}: +{value:.1f}%")
```

## Integration with Pandas

Convert results to DataFrame for analysis:

```python
import pandas as pd

# Run analysis
results = analyzer.analyze_tendencies(n=1)

# Convert to DataFrame
rows = []
for town, town_results in results.items():
    for char, value, towns in town_results['high_tendency']:
        rows.append({
            'town': town,
            'character': char,
            'tendency_type': 'high',
            'tendency_value': value,
            'reference_towns': ', '.join(towns)
        })
    for char, value, towns in town_results['low_tendency']:
        rows.append({
            'town': town,
            'character': char,
            'tendency_type': 'low',
            'tendency_value': value,
            'reference_towns': ', '.join(towns)
        })

df = pd.DataFrame(rows)

# Analyze with pandas
print("Top 10 strongest tendencies:")
print(df.nlargest(10, 'tendency_value')[['town', 'character', 'tendency_value']])

print("\\nTop 10 strongest avoidances:")
print(df.nsmallest(10, 'tendency_value')[['town', 'character', 'tendency_value']])

# Export to CSV
df.to_csv('tendency_analysis.csv', index=False, encoding='utf-8-sig')
```

## Visualization

Create visualizations using matplotlib:

```python
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # Chinese font

# Run analysis
results = analyzer.analyze_tendencies(n=1, target_town="岗美镇")

# Extract data for visualization
town_results = results["岗美镇"]
high_chars = [char for char, _, _ in town_results['high_tendency'][:10]]
high_values = [value for _, value, _ in town_results['high_tendency'][:10]]

# Create bar chart
plt.figure(figsize=(12, 6))
plt.bar(high_chars, high_values, color='green', alpha=0.7)
plt.xlabel('Character')
plt.ylabel('Tendency Value (%)')
plt.title('岗美镇 - High Tendency Characters')
plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('岗美镇_high_tendency.png', dpi=300)
plt.show()
```

## Parallel Processing for Large Datasets

Process multiple towns in parallel:

```python
from concurrent.futures import ProcessPoolExecutor
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

def analyze_single_town(args):
    """Analyze a single town (for parallel processing)."""
    data, town, n, high_threshold, low_threshold = args
    analyzer = TendencyAnalyzer(data)
    return analyzer.analyze_tendencies(
        n=n,
        target_town=town,
        high_threshold=high_threshold,
        low_threshold=low_threshold
    )

# Prepare arguments
towns = list(data.keys())
args_list = [(data, town, 1, 10, 20) for town in towns]

# Parallel execution
with ProcessPoolExecutor(max_workers=4) as executor:
    results_list = list(executor.map(analyze_single_town, args_list))

# Combine results
combined_results = {}
for result in results_list:
    combined_results.update(result)
```

## Custom Result Filtering

Filter results based on custom criteria:

```python
def filter_results(results, min_tendency=20, max_results=5):
    """Filter results to show only strongest patterns."""
    filtered = {}
    for town, town_results in results.items():
        filtered[town] = {
            'high_tendency': [
                (char, value, towns)
                for char, value, towns in town_results['high_tendency']
                if value >= min_tendency
            ][:max_results],
            'low_tendency': [
                (char, value, towns)
                for char, value, towns in town_results['low_tendency']
                if abs(value) >= min_tendency
            ][:max_results]
        }
    return filtered

# Apply filter
results = analyzer.analyze_tendencies(n=1)
filtered_results = filter_results(results, min_tendency=30, max_results=3)
analyzer.print_results(filtered_results)
```

## Generating Comprehensive Reports

Create detailed analysis reports:

```python
from tendency_analysis.scripts.formatter import generate_summary_report

# Run analysis
results = analyzer.analyze_tendencies(n=1)

# Generate comprehensive report
report = generate_summary_report(results, analyzer)

# Save to file
with open("comprehensive_report.txt", "w", encoding="utf-8") as f:
    f.write(report)

print("Report saved to comprehensive_report.txt")
```

## Configuration-Based Analysis

Use configuration files for reproducible analysis:

```python
import json

# Load configuration
with open("tendency-analysis/assets/config-template.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Extract parameters
params = config['analysis_parameters']
output_opts = config['output_options']

# Run analysis with config
results = analyzer.analyze_tendencies(
    n=params['n'],
    high_threshold=params['high_threshold'],
    low_threshold=params['low_threshold'],
    display_threshold=params['display_threshold']
)

# Export with config
from tendency_analysis.scripts.data_loader import export_results

export_results(
    results,
    f"results.{output_opts['format']}",
    format=output_opts['format'],
    metadata={
        'parameters': params,
        'date': datetime.now().strftime('%Y-%m-%d')
    }
)
```

## Performance Optimization Tips

### 1. Cache Parsed Data

```python
import pickle

# First run: parse and cache
data = load_village_data("阳春村庄名录.txt")
with open("data_cache.pkl", "wb") as f:
    pickle.dump(data, f)

# Subsequent runs: load from cache (much faster)
with open("data_cache.pkl", "rb") as f:
    data = pickle.load(f)
```

### 2. Reuse Analyzer Instance

```python
# Efficient: create once, use many times
analyzer = OptimizedTendencyAnalyzer(data)
for threshold in [5, 10, 15, 20]:
    results = analyzer.analyze_tendencies(n=1, high_threshold=threshold)
    # Process results...

# Inefficient: recreate every time
for threshold in [5, 10, 15, 20]:
    analyzer = OptimizedTendencyAnalyzer(data)  # Slow!
    results = analyzer.analyze_tendencies(n=1, high_threshold=threshold)
```

### 3. Profile Performance

```python
import time

# Time analysis
start = time.time()
results = analyzer.analyze_tendencies(n=1)
elapsed = time.time() - start
print(f"Analysis completed in {elapsed:.2f} seconds")
```

## Next Steps

- See [Integration Guide](integration.md) for using with existing code
- See [Performance Guide](../references/performance-guide.md) for optimization strategies
- See [API Reference](../references/api-reference.md) for complete documentation
