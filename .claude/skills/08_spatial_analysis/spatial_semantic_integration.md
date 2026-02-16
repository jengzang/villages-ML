# Skill 17: Spatial-Semantic Integration

## Skill Name
spatial_semantic_integration

## Purpose
Integrate spatial clustering results with semantic analysis to identify geographic-semantic associations.
Analyze how naming patterns vary across spatial clusters and discover regional linguistic boundaries.
Strictly offline computation.

---

# Part A: Integration Strategy

**Data Sources:**
- Spatial clusters from `spatial_clusters` table (Skill 13)
- Semantic indices from `village_semantic_index` table (Skill 4)
- Spatial features from `village_spatial_features` table (Skill 16)
- Character tendencies from regional analysis (Skill 3)

**Integration Levels:**
1. **Cluster-level**: Aggregate semantic profiles per spatial cluster
2. **Village-level**: Correlate spatial features with semantic categories
3. **Regional-level**: Compare spatial-semantic patterns across cities/counties

**Analysis Goals:**
- Identify dominant semantic themes in each spatial cluster
- Discover geographic boundaries of naming patterns
- Correlate isolation with semantic diversity
- Map linguistic-geographic associations

---

# Part B: Analysis Methods

**Method 1: Cluster Semantic Profiling**
- For each spatial cluster, compute:
  - Top semantic indices (water, mountain, settlement, etc.)
  - Character frequency distribution
  - Naming pattern prevalence (suffixes, prefixes)
- Compare profiles across clusters
- Identify spatially-coherent semantic regions

**Method 2: Spatial-Semantic Correlation**
- Correlate spatial features with semantic categories:
  - Do water-related names cluster near rivers?
  - Are mountain names more isolated?
  - Do settlement names appear in dense areas?
- Statistical tests: Chi-square, correlation coefficients
- Visualization: Heatmaps, scatter plots

**Method 3: Geographic Boundary Detection**
- Identify spatial boundaries where semantic patterns shift
- Use cluster transitions as potential linguistic boundaries
- Compare with known dialect regions
- Validate against administrative boundaries

**Method 4: Isolation-Semantic Analysis**
- Compare semantic diversity in isolated vs. connected villages
- Analyze naming conservatism in remote areas
- Identify unique naming patterns in isolated clusters

---

# Part C: Output Schema

**Table: `spatial_semantic_profiles`**

Columns:
- `cluster_id` (INTEGER) - Spatial cluster identifier
- `cluster_size` (INTEGER) - Number of villages
- `centroid_lon` (REAL) - Cluster center longitude
- `centroid_lat` (REAL) - Cluster center latitude
- `dominant_semantic_index` (TEXT) - Most common semantic category
- `semantic_distribution` (TEXT/JSON) - Distribution of semantic indices
- `top_characters` (TEXT/JSON) - Most frequent characters
- `naming_patterns` (TEXT/JSON) - Common suffixes/prefixes
- `semantic_diversity` (REAL) - Shannon entropy of semantic distribution
- `isolation_correlation` (REAL) - Correlation with isolation score
- `run_id` (TEXT) - Reproducibility tracking
- `created_at` (REAL) - Timestamp

**Table: `village_spatial_semantic`**

Columns:
- `village_id` (INTEGER) - Foreign key
- `village_name` (TEXT) - Village name
- `cluster_id` (INTEGER) - Spatial cluster
- `semantic_index` (TEXT) - Primary semantic category
- `isolation_score` (REAL) - Spatial isolation
- `density_5km` (INTEGER) - Local density
- `semantic_match_cluster` (INTEGER) - 1 if matches cluster dominant semantic
- `run_id` (TEXT) - Reproducibility tracking

---

# Part D: Visualization Methods

**Map Visualizations:**
1. **Semantic Cluster Map**
   - Color clusters by dominant semantic index
   - Size by cluster size
   - Interactive tooltips with semantic profiles

2. **Isolation-Semantic Heatmap**
   - Overlay isolation scores with semantic categories
   - Identify isolated semantic outliers
   - Highlight unique naming regions

3. **Boundary Detection Map**
   - Show cluster boundaries
   - Highlight semantic transition zones
   - Compare with dialect/administrative boundaries

**Statistical Visualizations:**
1. **Semantic Distribution by Cluster**
   - Stacked bar charts per cluster
   - Compare semantic diversity across clusters

2. **Correlation Matrix**
   - Spatial features vs. semantic categories
   - Heatmap of correlation coefficients

3. **Scatter Plots**
   - Isolation score vs. semantic diversity
   - Density vs. semantic category prevalence

---

# Part E: CLI Usage

**Module:** `src/spatial/spatial_semantic_integration.py`
**Class:** `SpatialSemanticIntegrator`

**Basic Usage:**
```bash
python scripts/integrate_spatial_semantic.py \
  --spatial-run-id spatial_v1 \
  --semantic-run-id semantic_v1 \
  --output-run-id integration_v1
```

**Advanced Options:**
```bash
python scripts/integrate_spatial_semantic.py \
  --spatial-run-id spatial_v1 \
  --semantic-run-id semantic_v1 \
  --output-run-id integration_guangzhou_v1 \
  --region-filter "广州市" \
  --min-cluster-size 10 \
  --generate-maps \
  --output-dir results/integration_guangzhou_v1/
```

**Parameter Flags:**
- `--spatial-run-id` - Run ID of spatial clustering results
- `--semantic-run-id` - Run ID of semantic analysis results
- `--output-run-id` - Unique identifier for integration results
- `--region-filter` - Optional city/county filter
- `--min-cluster-size` - Minimum cluster size for analysis
- `--generate-maps` - Generate interactive maps
- `--output-dir` - Results directory

**Output Files:**
- `spatial_semantic_profiles.json` - Cluster semantic profiles
- `correlation_matrix.csv` - Spatial-semantic correlations
- `semantic_cluster_map.html` - Interactive folium map
- `boundary_analysis.json` - Geographic boundary detection results
- `isolation_semantic_report.pdf` - Comprehensive analysis report

---

# Part F: Performance Characteristics

**Computation Time:**
- Full dataset (285k villages): ~5-10 minutes
- Regional subset (50k villages): ~1-2 minutes
- Bottleneck: Semantic aggregation per cluster

**Memory Usage:**
- Peak memory: ~1 GB
- Cluster profiles: ~10 MB
- Village-level features: ~100 MB

**Scalability:**
- Linear in number of villages
- Linear in number of clusters
- Map generation: O(n) for villages

**Deployment Constraint:**
- ⚠️ **Offline only** - Never run on 2-core/2GB server
- Precompute integration results and save to database
- Online queries only read precomputed profiles

---

# Part G: Interpretation Guidelines

**Cluster Semantic Profiles:**
- **Water-dominant clusters**: Near rivers, coasts, wetlands
- **Mountain-dominant clusters**: Hilly/mountainous regions
- **Settlement-dominant clusters**: Urban centers, historical towns
- **Mixed clusters**: Transition zones, diverse geography

**Spatial-Semantic Correlations:**
- Strong positive: Geographic feature matches semantic category
- Strong negative: Inverse relationship (e.g., water names in dry areas)
- Weak: No clear geographic-semantic association

**Isolation-Semantic Patterns:**
- High isolation + low diversity: Conservative naming, remote areas
- High isolation + high diversity: Unique local naming traditions
- Low isolation + high diversity: Cultural mixing, trade routes

**Boundary Detection:**
- Sharp semantic transitions: Potential dialect boundaries
- Gradual transitions: Cultural diffusion zones
- Administrative alignment: Policy-driven naming patterns

---

# Part H: Quality Checks

**Before Running:**
1. Verify spatial clustering completed successfully
2. Confirm semantic analysis results exist
3. Check spatial features are computed
4. Ensure run IDs match between datasets

**After Running:**
1. Validate cluster semantic profiles are reasonable
2. Check correlation coefficients are in valid range (-1 to 1)
3. Inspect maps for geographic coherence
4. Verify boundary detections align with known features

**Expected Results:**
- 70-90% of clusters have dominant semantic index
- Semantic diversity: 0.5-2.0 (Shannon entropy)
- Strong correlations (>0.5) for water/mountain names
- 10-20 major semantic-geographic boundaries

---

# Part I: Use Cases

**Research Applications:**
1. **Linguistic Geography**: Map dialect boundaries using naming patterns
2. **Historical Analysis**: Identify settlement patterns and migration routes
3. **Cultural Studies**: Discover regional naming traditions
4. **Toponymy Research**: Analyze place name formation principles

**Practical Applications:**
1. **Infrastructure Planning**: Identify underserved isolated regions
2. **Cultural Heritage**: Preserve unique naming traditions
3. **Tourism Development**: Highlight regions with distinctive names
4. **Education**: Teach regional geography and culture

---

# Acceptance Criteria

1. ✅ Cluster semantic profiles computed for all spatial clusters
2. ✅ Spatial-semantic correlations calculated and validated
3. ✅ Village-level integration completed
4. ✅ Results saved to `spatial_semantic_profiles` and `village_spatial_semantic` tables
5. ✅ Interactive maps generated (if requested)
6. ✅ Correlation matrix and statistical reports produced
7. ✅ Boundary detection analysis completed
8. ✅ Run ID tracked for reproducibility
9. ✅ Computation completes in <10 minutes for full dataset
10. ✅ Memory usage stays under 1.5GB
