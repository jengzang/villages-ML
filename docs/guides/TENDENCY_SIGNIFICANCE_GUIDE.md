# Tendency Analysis with Statistical Significance Testing

## Overview

This guide explains how to use the statistical significance testing features added to the tendency analysis system. These features help identify which regional naming patterns are statistically meaningful versus random noise.

## What's New in Phase 1

### Statistical Significance Testing

The system now computes:

1. **Chi-square test**: Tests whether character-region associations are statistically significant
2. **P-values**: Probability that the observed pattern occurred by chance
3. **Effect sizes (Cramér's V)**: Measures the strength of the association
4. **Confidence intervals**: Wilson score intervals for regional frequencies
5. **Significance levels**: Visual markers (***,  **, *, ns) for quick interpretation

### Database Persistence

All results are now stored in the database for:
- Fast querying and filtering
- Cross-analysis integration
- Long-term result tracking
- Reproducible research

## Quick Start

### 1. Initialize Database Tables

First, create the necessary database tables:

```bash
python scripts/init_tendency_tables.py
```

This creates the `tendency_significance` table and indexes.

### 2. Run Analysis with Significance Testing

Use the test script to run a complete analysis:

```bash
python scripts/test_significance.py
```

This will:
- Load village data (~285,000 villages)
- Preprocess names and extract character sets
- Compute global and regional character frequencies
- Calculate tendency metrics (lift, log-odds, z-scores)
- Compute statistical significance for all patterns
- Save results to database

**Expected runtime**: ~20-30 seconds for city-level analysis

### 3. Query Results

Query the results from the database:

```bash
# View all results for a run
python scripts/query_tendency.py --run-id test_sig_1771260439

# View only significant patterns
python scripts/query_tendency.py --run-id test_sig_1771260439 --significant-only

# Filter by character
python scripts/query_tendency.py --run-id test_sig_1771260439 --char 田

# Filter by effect size
python scripts/query_tendency.py --run-id test_sig_1771260439 --min-effect-size 0.1

# Export to CSV
python scripts/query_tendency.py --run-id test_sig_1771260439 --significant-only --output significant_patterns.csv
```

## Understanding the Results

### Significance Levels

- `***`: p < 0.001 (highly significant)
- `**`: p < 0.01 (very significant)
- `*`: p < 0.05 (significant)
- `ns`: p ≥ 0.05 (not significant)

### Effect Size Interpretation

- **Small**: Cramér's V < 0.1 (weak association)
- **Medium**: 0.1 ≤ Cramér's V < 0.3 (moderate association)
- **Large**: Cramér's V ≥ 0.3 (strong association)

### Key Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| `p_value` | Probability of observing this pattern by chance | Lower = more significant |
| `chi_square_statistic` | Chi-square test statistic | Higher = stronger deviation from expected |
| `effect_size` | Cramér's V (0-1) | Measures strength of association |
| `lift` | Regional freq / Global freq | >1 = overrepresented, <1 = underrepresented |
| `ci_lower`, `ci_upper` | 95% confidence interval bounds | Range of plausible frequency values |

## Database Schema

### Table: `tendency_significance`

Stores statistical significance results for each character-region pair.

```sql
CREATE TABLE tendency_significance (
    run_id TEXT NOT NULL,
    region_level TEXT NOT NULL,
    region_name TEXT NOT NULL,
    char TEXT NOT NULL,
    chi_square_statistic REAL NOT NULL,
    p_value REAL NOT NULL,
    is_significant INTEGER NOT NULL,
    significance_level TEXT NOT NULL,
    effect_size REAL NOT NULL,
    effect_size_interpretation TEXT NOT NULL,
    ci_lower REAL,
    ci_upper REAL,
    created_at REAL NOT NULL,
    PRIMARY KEY (run_id, region_level, region_name, char)
);
```

### Indexes

Optimized for common query patterns:

- `idx_significance_level`: Query by region level
- `idx_significance_char`: Query by character
- `idx_significance_pvalue`: Sort by significance
- `idx_significance_flag`: Filter significant results
- `idx_significance_effect`: Sort by effect size

## API Reference

### Core Functions

#### `compute_chi_square_significance()`

```python
from src.analysis.regional_analysis import compute_chi_square_significance

result = compute_chi_square_significance(
    n_region=100,      # Villages with char in region
    N_region=1000,     # Total villages in region
    n_global=500,      # Villages with char globally
    N_global=10000     # Total villages globally
)

# Returns:
# {
#     'chi_square_statistic': 15.2,
#     'p_value': 0.0001,
#     'is_significant': True,
#     'significance_level': '***',
#     'effect_size': 0.039,
#     'effect_size_interpretation': 'small'
# }
```

#### `compute_confidence_interval()`

```python
from src.analysis.regional_analysis import compute_confidence_interval

lower, upper = compute_confidence_interval(
    n_region=100,      # Villages with char in region
    N_region=1000,     # Total villages in region
    confidence_level=0.95
)

# Returns: (0.082, 0.121)  # 95% CI for frequency
```

#### `compute_tendency_significance()`

```python
from src.analysis.regional_analysis import compute_tendency_significance

# Add significance columns to tendency DataFrame
tendency_df = compute_tendency_significance(
    tendency_df,
    compute_ci=True,
    confidence_level=0.95
)

# Adds columns:
# - chi_square_statistic
# - p_value
# - is_significant
# - significance_level
# - effect_size
# - effect_size_interpretation
# - ci_lower (if compute_ci=True)
# - ci_upper (if compute_ci=True)
```

### Database Functions

#### `save_tendency_significance()`

```python
from src.data.db_writer import save_tendency_significance
import sqlite3

conn = sqlite3.connect('data/villages.db')
save_tendency_significance(conn, run_id='my_run', df=tendency_df)
conn.close()
```

#### `query_tendency_results()`

```python
from scripts.query_tendency import query_tendency_results

df = query_tendency_results(
    db_path='data/villages.db',
    run_id='test_sig_1771260439',
    significant_only=True,
    min_effect_size=0.1,
    limit=100
)
```

## Example Workflow

### Complete Analysis Pipeline

```python
import sqlite3
import pandas as pd
from src.data.db_loader import load_villages
from src.preprocessing.char_extractor import process_village_batch
from src.analysis.char_frequency import (
    compute_char_frequency_global,
    compute_char_frequency_by_region,
    calculate_lift
)
from src.analysis.regional_analysis import (
    compute_regional_tendency,
    compute_tendency_significance
)
from src.data.db_writer import (
    create_analysis_tables,
    save_tendency_significance
)

# 1. Load and preprocess data
conn = sqlite3.connect('data/villages.db')
villages_chunks = list(load_villages(conn))
villages_df = pd.concat(villages_chunks, ignore_index=True)
villages_df = process_village_batch(villages_df)

# 2. Compute frequencies
global_freq_df = compute_char_frequency_global(villages_df)
regional_freq_df = compute_char_frequency_by_region(villages_df, 'city')
regional_freq_df = calculate_lift(regional_freq_df, global_freq_df)

# 3. Compute tendency with significance
tendency_df = compute_regional_tendency(regional_freq_df)
tendency_df = compute_tendency_significance(tendency_df, compute_ci=True)

# 4. Save to database
create_analysis_tables(conn)
save_tendency_significance(conn, 'my_run_id', tendency_df)
conn.close()

# 5. Analyze results
significant = tendency_df[tendency_df['is_significant']]
print(f"Found {len(significant)} significant patterns")
print(significant.nlargest(10, 'effect_size'))
```

## Interpreting Results

### Example: Character '田' in Meizhou (梅州)

```
char: 田
region_name: 梅州市
lift: 2.5
p_value: 0.0001
significance_level: ***
effect_size: 0.15
effect_size_interpretation: medium
ci_lower: 0.082
ci_upper: 0.121
```

**Interpretation**:
- The character '田' appears 2.5× more frequently in Meizhou than the provincial average
- This pattern is highly significant (p < 0.001), very unlikely to be random
- The effect size is medium (0.15), indicating a moderate association
- We're 95% confident the true frequency is between 8.2% and 12.1%

### When to Trust a Pattern

A pattern is trustworthy when:
1. **p < 0.05** (statistically significant)
2. **Effect size ≥ 0.1** (at least small effect)
3. **Lift substantially different from 1.0** (e.g., >1.5 or <0.67)
4. **Narrow confidence interval** (precise estimate)

## Performance Notes

### Computation Time

- **City level** (21 regions): ~20-30 seconds
- **County level** (~120 regions): ~2-3 minutes (estimated)
- **Township level** (~1,600 regions): ~20-30 minutes (estimated)

### Memory Usage

- Peak memory: ~500MB for full dataset
- Database size: ~50MB per run (city level)

### Optimization Tips

1. **Filter by support thresholds**: Use `min_global_support` and `min_regional_support` to reduce noise
2. **Skip CI computation**: Set `compute_ci=False` to save ~20% time
3. **Batch processing**: Process one region level at a time for large analyses

## Troubleshooting

### Common Issues

**Issue**: "No module named 'src'"
```bash
# Solution: Set PYTHONPATH
export PYTHONPATH=.  # Linux/Mac
set PYTHONPATH=.     # Windows CMD
$env:PYTHONPATH="."  # Windows PowerShell
```

**Issue**: "KeyError: 'is_valid'"
```python
# Solution: Preprocess villages first
villages_df = process_village_batch(villages_df)
```

**Issue**: "KeyError: 'lift_vs_global'"
```python
# Solution: Calculate lift before tendency
regional_freq_df = calculate_lift(regional_freq_df, global_freq_df)
```

**Issue**: "All p-values are 1.0"
```python
# Solution: Check that global_total_villages is set correctly
# The compute_chi_square_significance function needs this value
```

## Next Steps

### Phase 2: Spatial-Tendency Integration (Planned)

Combine tendency analysis with spatial clustering to:
- Identify geographic boundaries of naming patterns
- Detect spatial coherence of tendencies
- Generate integrated maps

### Phase 3: Z-Score Normalization (Optional)

Add alternative normalization method for academic use:
- More robust for small sample sizes
- Better handling of variance
- Suitable for research publications

## References

### Statistical Methods

- **Chi-square test**: Tests independence between categorical variables
- **Cramér's V**: Effect size measure for chi-square test
- **Wilson score interval**: Confidence interval for binomial proportions

### Further Reading

- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences
- Agresti, A. (2002). Categorical Data Analysis
- Wilson, E. B. (1927). Probable Inference, the Law of Succession, and Statistical Inference

## Support

For issues or questions:
1. Check this guide first
2. Review the test script: `scripts/test_significance.py`
3. Examine the source code: `src/analysis/regional_analysis.py`
4. Open an issue on GitHub

---

**Last Updated**: 2026-02-17
**Version**: Phase 1 (Statistical Significance Testing)
