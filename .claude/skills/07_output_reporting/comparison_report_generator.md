# Skill 19: Comparison Report Generator

## Skill Name
comparison_report_generator

## Purpose
Generate comprehensive comparison reports for multiple clustering runs with different parameters.
Compare evaluation metrics, cluster quality, and semantic coherence across configurations.
Support parameter tuning and model selection through visual and statistical comparisons.

---

# Part A: Comparison Dimensions

**Evaluation Metrics:**
- Silhouette Score (cluster cohesion and separation)
- Davies-Bouldin Index (cluster compactness)
- Calinski-Harabasz Index (cluster variance ratio)
- Inertia (within-cluster sum of squares)
- Noise ratio (percentage of unclustered points)

**Cluster Characteristics:**
- Number of clusters
- Cluster size distribution (mean, median, std)
- Largest cluster size
- Smallest cluster size
- Cluster balance (Gini coefficient)

**Semantic Quality:**
- Semantic coherence per cluster
- Dominant semantic index clarity
- Semantic diversity (Shannon entropy)
- Cross-cluster semantic overlap

**Spatial Quality (if applicable):**
- Geographic compactness
- Spatial coherence
- Boundary clarity
- Isolation patterns

---

# Part B: Report Formats

**Format 1: Summary Table**
- Rows: Different runs (run_id)
- Columns: Metrics and characteristics
- Sortable by any metric
- Highlight best/worst values

**Format 2: Detailed Comparison**
- Side-by-side cluster profiles
- Parameter configurations
- Quality metrics breakdown
- Semantic distribution comparison

**Format 3: Visual Dashboard**
- Interactive HTML report
- Charts: line plots, bar charts, radar plots
- Cluster size distributions
- Metric trends across parameters

**Format 4: Statistical Analysis**
- Correlation between parameters and metrics
- Significance tests (t-test, ANOVA)
- Optimal parameter recommendations
- Sensitivity analysis

---

# Part C: Visualization Types

**1. Metric Comparison Charts**
```
Line Plot: Silhouette Score vs. eps (DBSCAN)
Bar Chart: Number of clusters per run
Radar Plot: Multi-metric comparison (normalized)
```

**2. Cluster Size Distributions**
```
Histogram: Cluster sizes for each run
Box Plot: Size distribution comparison
Violin Plot: Density of cluster sizes
```

**3. Parameter Sensitivity**
```
Heatmap: Metric values across parameter grid
Contour Plot: 2D parameter space exploration
Scatter Plot: Parameter vs. metric correlation
```

**4. Semantic Comparison**
```
Stacked Bar: Semantic distribution per run
Heatmap: Semantic coherence matrix
Network Graph: Semantic overlap between runs
```

---

# Part D: Output Schema

**Table: `clustering_comparison`**

Columns:
- `comparison_id` (TEXT) - Unique comparison identifier
- `run_ids` (TEXT/JSON) - List of run IDs being compared
- `comparison_type` (TEXT) - Type: parameter_sweep, method_comparison, etc.
- `best_run_id` (TEXT) - Run with best overall metrics
- `best_metric` (TEXT) - Primary metric used for ranking
- `summary_stats` (TEXT/JSON) - Summary statistics
- `created_at` (REAL) - Timestamp

**Table: `run_metrics_summary`**

Columns:
- `run_id` (TEXT) - Run identifier
- `method` (TEXT) - Clustering method (DBSCAN, KMeans, etc.)
- `parameters` (TEXT/JSON) - Parameter configuration
- `n_clusters` (INTEGER) - Number of clusters
- `n_noise` (INTEGER) - Number of noise points
- `silhouette_score` (REAL) - Silhouette coefficient
- `davies_bouldin_index` (REAL) - DB index
- `calinski_harabasz_index` (REAL) - CH index
- `semantic_coherence_avg` (REAL) - Average semantic coherence
- `cluster_size_mean` (REAL) - Mean cluster size
- `cluster_size_std` (REAL) - Std of cluster sizes
- `computation_time_seconds` (REAL) - Runtime
- `created_at` (REAL) - Timestamp

---

# Part E: CLI Usage

**Module:** `src/export/comparison_report.py`
**Class:** `ComparisonReportGenerator`

**Basic Usage:**
```bash
# Compare multiple runs
python scripts/generate_comparison_report.py \
  --run-ids spatial_v1 spatial_v2 spatial_v3 \
  --output-file comparison_report.html
```

**Parameter Sweep Comparison:**
```bash
# Compare DBSCAN with different eps values
python scripts/generate_comparison_report.py \
  --run-ids dbscan_eps1.0 dbscan_eps2.0 dbscan_eps3.0 dbscan_eps5.0 \
  --comparison-type parameter_sweep \
  --parameter eps \
  --output-file dbscan_eps_comparison.html
```

**Method Comparison:**
```bash
# Compare different clustering methods
python scripts/generate_comparison_report.py \
  --run-ids dbscan_v1 kmeans_v1 gmm_v1 hdbscan_v1 \
  --comparison-type method_comparison \
  --output-file method_comparison.html
```

**Advanced Options:**
```bash
python scripts/generate_comparison_report.py \
  --run-ids run1 run2 run3 \
  --metrics silhouette davies_bouldin calinski_harabasz \
  --best-metric silhouette \
  --include-semantic-analysis \
  --include-spatial-analysis \
  --output-format html pdf csv \
  --output-dir results/comparison_v1/
```

**Parameter Flags:**
- `--run-ids` - List of run IDs to compare
- `--comparison-type` - Type of comparison (parameter_sweep, method_comparison, etc.)
- `--parameter` - Parameter being swept (for parameter_sweep)
- `--metrics` - Metrics to include in comparison
- `--best-metric` - Primary metric for ranking runs
- `--include-semantic-analysis` - Include semantic quality metrics
- `--include-spatial-analysis` - Include spatial quality metrics
- `--output-format` - Output formats (html, pdf, csv, json)
- `--output-dir` - Results directory

---

# Part F: Report Sections

**Section 1: Executive Summary**
- Best performing run
- Key findings
- Recommended configuration
- Quick comparison table

**Section 2: Metric Comparison**
- Detailed metric values for each run
- Statistical significance tests
- Metric trends and patterns
- Optimal parameter ranges

**Section 3: Cluster Quality Analysis**
- Cluster size distributions
- Cluster balance metrics
- Noise ratio comparison
- Quality score breakdown

**Section 4: Semantic Analysis**
- Semantic coherence comparison
- Dominant semantic indices per run
- Semantic diversity metrics
- Cross-run semantic overlap

**Section 5: Spatial Analysis (if applicable)**
- Geographic compactness
- Spatial coherence metrics
- Boundary quality
- Isolation patterns

**Section 6: Parameter Sensitivity**
- Parameter impact on metrics
- Correlation analysis
- Sensitivity heatmaps
- Recommended parameter ranges

**Section 7: Recommendations**
- Best configuration for different use cases
- Trade-offs between metrics
- Parameter tuning suggestions
- Next steps for optimization

---

# Part G: Interpretation Guidelines

**Silhouette Score:**
- Range: -1 to 1
- >0.7: Strong clustering
- 0.5-0.7: Reasonable clustering
- 0.25-0.5: Weak clustering
- <0.25: Poor clustering

**Davies-Bouldin Index:**
- Range: 0 to ∞
- Lower is better
- <1.0: Excellent
- 1.0-2.0: Good
- >2.0: Poor

**Calinski-Harabasz Index:**
- Range: 0 to ∞
- Higher is better
- >1000: Excellent
- 100-1000: Good
- <100: Poor

**Cluster Balance:**
- Gini coefficient: 0 (perfect balance) to 1 (extreme imbalance)
- <0.3: Well-balanced
- 0.3-0.6: Moderately balanced
- >0.6: Imbalanced

**Semantic Coherence:**
- Range: 0 to 1
- >0.8: Highly coherent
- 0.6-0.8: Moderately coherent
- <0.6: Low coherence

---

# Part H: Performance Characteristics

**Computation Time:**
- 2 runs: <1 minute
- 5 runs: 1-2 minutes
- 10 runs: 2-5 minutes
- 20+ runs: 5-10 minutes

**Memory Usage:**
- Base: ~100 MB
- Per run: ~50 MB
- Peak: ~500 MB for 10 runs

**Output Sizes:**
- HTML report: 1-5 MB
- PDF report: 2-10 MB
- CSV data: 10-100 KB
- JSON data: 50-500 KB

**Scalability:**
- Linear in number of runs
- Linear in number of clusters
- Visualization generation is bottleneck

---

# Part I: Example Use Cases

**Use Case 1: DBSCAN Parameter Tuning**
```bash
# Compare eps values: 1.0, 2.0, 3.0, 5.0 km
python scripts/generate_comparison_report.py \
  --run-ids dbscan_eps1 dbscan_eps2 dbscan_eps3 dbscan_eps5 \
  --comparison-type parameter_sweep \
  --parameter eps \
  --best-metric silhouette
```

**Use Case 2: Method Selection**
```bash
# Compare DBSCAN, KMeans, GMM
python scripts/generate_comparison_report.py \
  --run-ids dbscan_v1 kmeans_v1 gmm_v1 \
  --comparison-type method_comparison \
  --include-semantic-analysis
```

**Use Case 3: Regional Comparison**
```bash
# Compare clustering across different cities
python scripts/generate_comparison_report.py \
  --run-ids guangzhou_v1 shenzhen_v1 foshan_v1 \
  --comparison-type regional_comparison \
  --include-spatial-analysis
```

**Use Case 4: Temporal Comparison**
```bash
# Compare clustering over time (if data updated)
python scripts/generate_comparison_report.py \
  --run-ids clustering_2024q1 clustering_2024q2 clustering_2024q3 \
  --comparison-type temporal_comparison
```

---

# Part J: Quality Checks

**Before Generating Report:**
1. Verify all run IDs exist in database
2. Confirm metrics are computed for all runs
3. Check that runs are comparable (same dataset, similar scale)
4. Ensure output directory is writable

**After Generating Report:**
1. Verify all sections are populated
2. Check visualizations render correctly
3. Validate metric values are reasonable
4. Confirm best run selection makes sense
5. Review recommendations for consistency

**Expected Outputs:**
- HTML report with interactive charts
- Summary CSV with all metrics
- Detailed JSON with full comparison data
- PDF report (if requested)

---

# Part K: Integration with Other Skills

**Clustering Pipelines (Skills 5, 13):**
- Compare results from different clustering methods
- Evaluate parameter configurations
- Select optimal clustering approach

**Export & Reproducibility (Skill 12):**
- Track comparison metadata
- Ensure reproducible comparisons
- Version control for comparison reports

**Deployment Strategy (Skill 11):**
- Select best configuration for production
- Validate performance constraints
- Optimize for 2-core/2GB deployment

---

# Acceptance Criteria

1. ✅ Comparison report generated for multiple runs
2. ✅ All evaluation metrics computed and compared
3. ✅ Cluster quality metrics included
4. ✅ Semantic analysis comparison (if requested)
5. ✅ Spatial analysis comparison (if requested)
6. ✅ Visualizations generated (charts, plots, heatmaps)
7. ✅ Best run identified based on primary metric
8. ✅ Recommendations provided for parameter tuning
9. ✅ Multiple output formats supported (HTML, PDF, CSV, JSON)
10. ✅ Report includes interpretation guidelines
11. ✅ Computation completes in <10 minutes for 20 runs
12. ✅ Memory usage stays under 1GB
