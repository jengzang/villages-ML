# Skill 13: Spatial Clustering Pipeline (Geographic DBSCAN)

## Skill Name
spatial_clustering_pipeline

## Purpose
Run geographic clustering on village coordinates using DBSCAN with haversine metric.
Identifies spatial clusters and isolated villages based on geographic proximity.
Strictly offline computation.

---

# Part A: Input Requirements

**Data Source:**
- Table: `广东省自然村`
- Required columns: `longitude`, `latitude`, `自然村` (village name)
- Valid Guangdong Province bounds: 109°-118°E, 20°-26°N
- Minimum 285k+ villages with valid coordinates

**Data Quality:**
- Non-null coordinates
- Valid numeric format
- Within province bounds
- Deduplicated records

---

# Part B: DBSCAN Parameters

**Default Configuration:**
- `eps = 2.0` km (geographic distance threshold)
- `min_samples = 5` (minimum villages per cluster)
- `metric = 'haversine'` (great-circle distance)

**Parameter Tuning Guidelines:**
- Urban areas: `eps = 1.0-2.0` km (dense settlements)
- Rural areas: `eps = 3.0-5.0` km (sparse settlements)
- Coastal regions: `eps = 2.0-3.0` km (linear patterns)
- Mountain regions: `eps = 1.5-2.5` km (valley clusters)

**Interpretation:**
- Larger `eps` → fewer, larger clusters
- Smaller `eps` → more, tighter clusters
- Higher `min_samples` → stricter cluster definition

---

# Part C: Implementation

**Module:** `src/spatial/spatial_clustering.py`
**Class:** `SpatialClusterer`

**Processing Steps:**
1. Load coordinates via `CoordinateLoader`
2. Validate and filter coordinates (bounds check)
3. Convert degrees to radians for haversine metric
4. Run DBSCAN clustering with sklearn
5. Label noise points as `cluster_id = -1`
6. Extract cluster profiles (size, centroid, dominant regions)
7. Compute semantic profiles per cluster
8. Save results to database

**Key Methods:**
- `fit_predict()` - Run clustering and return labels
- `get_cluster_profiles()` - Extract cluster statistics
- `compute_centroids()` - Calculate geographic centers

---

# Part D: Output Schema

**Table 1: `spatial_clusters`**

Columns:
- `cluster_id` (INTEGER) - Cluster identifier (-1 for noise)
- `cluster_size` (INTEGER) - Number of villages in cluster
- `centroid_lon` (REAL) - Longitude of cluster center
- `centroid_lat` (REAL) - Latitude of cluster center
- `dominant_city` (TEXT) - Most common city in cluster
- `dominant_county` (TEXT) - Most common county in cluster
- `semantic_profile` (TEXT/JSON) - Top semantic indices
- `naming_patterns` (TEXT/JSON) - Common name patterns
- `run_id` (TEXT) - Reproducibility tracking
- `created_at` (REAL) - Timestamp

**Table 2: `village_spatial_features`**

Columns:
- `village_id` (INTEGER) - Foreign key to main table
- `village_name` (TEXT) - Village name
- `cluster_id` (INTEGER) - Assigned cluster (-1 if noise)
- `distance_to_centroid` (REAL) - Distance to cluster center (km)
- `is_noise` (INTEGER) - Boolean flag (1 if noise point)
- `run_id` (TEXT) - Reproducibility tracking

---

# Part E: CLI Usage

**Script:** `scripts/run_spatial_analysis.py`

**Basic Usage:**
```bash
python scripts/run_spatial_analysis.py \
  --eps 2.0 \
  --min-samples 5 \
  --run-id spatial_v1
```

**Advanced Options:**
```bash
python scripts/run_spatial_analysis.py \
  --eps 3.0 \
  --min-samples 10 \
  --region-filter "广州市" \
  --run-id spatial_guangzhou_v1 \
  --output-dir results/spatial_guangzhou_v1/
```

**Parameter Flags:**
- `--eps` - Distance threshold in kilometers
- `--min-samples` - Minimum cluster size
- `--run-id` - Unique identifier for this run
- `--region-filter` - Optional city/county filter
- `--output-dir` - Results directory

---

# Part F: Performance Characteristics

**Computation Time:**
- Full dataset (285k villages): ~30-60 seconds
- Regional subset (50k villages): ~5-10 seconds

**Memory Usage:**
- Peak memory: ~500 MB
- Distance matrix: O(n²) space (handled by sklearn internally)

**Scalability:**
- Linear in number of villages for DBSCAN
- Haversine metric is efficient for geographic data

**Deployment Constraint:**
- ⚠️ **Offline only** - Never run on 2-core/2GB server
- Precompute clusters and save to database
- Online queries only read precomputed results

---

# Part G: Cluster Interpretation

**Cluster Types:**
- **Dense urban clusters** (eps=1-2km, size>100): City centers
- **Suburban clusters** (eps=2-3km, size=20-100): Town peripheries
- **Rural clusters** (eps=3-5km, size=5-20): Village groups
- **Noise points** (cluster_id=-1): Isolated villages

**Semantic Analysis:**
- Extract dominant semantic indices per cluster
- Identify naming pattern trends (e.g., water-related clusters)
- Compare cluster profiles across regions

---

# Part H: Quality Checks

**Before Running:**
1. Verify coordinate data loaded correctly
2. Check for null/invalid coordinates
3. Confirm province bounds filtering

**After Running:**
1. Check cluster size distribution (histogram)
2. Verify noise ratio (typically 5-15%)
3. Inspect cluster centroids on map
4. Validate semantic profiles make sense

**Expected Results:**
- 50-200 major clusters (depends on eps)
- 5-15% noise points
- Clusters align with geographic features (rivers, mountains)

---

# Acceptance Criteria

1. ✅ Clusters identified with DBSCAN using haversine metric
2. ✅ Cluster profiles computed (size, centroid, dominant regions)
3. ✅ Results saved to `spatial_clusters` and `village_spatial_features` tables
4. ✅ Noise points labeled with cluster_id = -1
5. ✅ Run ID tracked for reproducibility
6. ✅ Computation completes in <2 minutes for full dataset
7. ✅ Memory usage stays under 1GB
