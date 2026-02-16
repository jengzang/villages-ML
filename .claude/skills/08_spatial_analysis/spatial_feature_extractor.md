# Skill 16: Spatial Feature Extractor

## Skill Name
spatial_feature_extractor

## Purpose
Extract spatial features for each village including nearest neighbor distances, local density, and isolation metrics.
These features support spatial clustering, outlier detection, and spatial-semantic integration analysis.
Strictly offline computation.

---

# Part A: Feature Types

**Nearest Neighbor Features:**
- `nn_distance_1` - Distance to 1st nearest neighbor (km)
- `nn_distance_5` - Average distance to 5 nearest neighbors (km)
- `nn_distance_10` - Average distance to 10 nearest neighbors (km)

**Local Density Features:**
- `density_1km` - Number of villages within 1km radius
- `density_5km` - Number of villages within 5km radius
- `density_10km` - Number of villages within 10km radius

**Isolation Metrics:**
- `isolation_score` - Normalized isolation metric (0-1, higher = more isolated)
- `is_isolated` - Boolean flag (1 if isolation_score > 0.7)

**Spatial Context:**
- `cluster_id` - Assigned spatial cluster from DBSCAN
- `distance_to_cluster_centroid` - Distance to cluster center (km)

---

# Part B: Implementation Methods

**Distance Calculation:**
- Metric: Haversine formula (great-circle distance)
- Input: Longitude/latitude in degrees
- Output: Distance in kilometers
- Handles Earth's curvature accurately

**Nearest Neighbor Search:**
- Algorithm: KD-Tree with haversine metric
- Complexity: O(n log n) for building tree, O(log n) per query
- Library: `sklearn.neighbors.BallTree`

**Density Computation:**
- Method: Count villages within radius using BallTree
- Radius options: 1km, 5km, 10km
- Normalized by area (villages per km²)

**Isolation Score:**
- Formula: `isolation_score = 1 - (density_5km / max_density_5km)`
- Range: 0 (dense) to 1 (isolated)
- Threshold: 0.7 for binary classification

---

# Part C: Parameter Configuration

**Default Parameters:**
```python
{
    'k_neighbors': [1, 5, 10],      # K values for nearest neighbors
    'density_radii': [1, 5, 10],    # Radii in km for density
    'isolation_threshold': 0.7,      # Threshold for is_isolated flag
    'use_cluster_features': True     # Include cluster-based features
}
```

**Tuning Guidelines:**
- Urban areas: Use smaller radii (0.5km, 2km, 5km)
- Rural areas: Use larger radii (2km, 10km, 20km)
- Coastal regions: Adjust for linear settlement patterns
- Mountain regions: Account for valley-based clustering

---

# Part D: Output Schema

**Table: `village_spatial_features`**

Columns:
- `village_id` (INTEGER) - Foreign key to main table
- `village_name` (TEXT) - Village name
- `longitude` (REAL) - Longitude coordinate
- `latitude` (REAL) - Latitude coordinate
- `nn_distance_1` (REAL) - Distance to nearest neighbor (km)
- `nn_distance_5` (REAL) - Average distance to 5 nearest neighbors (km)
- `nn_distance_10` (REAL) - Average distance to 10 nearest neighbors (km)
- `density_1km` (INTEGER) - Villages within 1km radius
- `density_5km` (INTEGER) - Villages within 5km radius
- `density_10km` (INTEGER) - Villages within 10km radius
- `isolation_score` (REAL) - Normalized isolation metric (0-1)
- `is_isolated` (INTEGER) - Boolean flag (1 if isolated)
- `cluster_id` (INTEGER) - Spatial cluster assignment (-1 if noise)
- `distance_to_centroid` (REAL) - Distance to cluster center (km)
- `run_id` (TEXT) - Reproducibility tracking
- `created_at` (REAL) - Timestamp

**Index Recommendations:**
```sql
CREATE INDEX idx_village_spatial_cluster ON village_spatial_features(cluster_id);
CREATE INDEX idx_village_spatial_isolated ON village_spatial_features(is_isolated);
CREATE INDEX idx_village_spatial_density ON village_spatial_features(density_5km);
```

---

# Part E: CLI Usage

**Module:** `src/spatial/spatial_features.py`
**Class:** `SpatialFeatureExtractor`

**Basic Usage:**
```bash
python scripts/extract_spatial_features.py \
  --run-id spatial_features_v1
```

**Advanced Options:**
```bash
python scripts/extract_spatial_features.py \
  --k-neighbors 1 5 10 20 \
  --density-radii 1 5 10 20 \
  --isolation-threshold 0.8 \
  --region-filter "广州市" \
  --run-id spatial_features_guangzhou_v1 \
  --output-dir results/spatial_features_guangzhou_v1/
```

**Parameter Flags:**
- `--k-neighbors` - List of K values for nearest neighbors
- `--density-radii` - List of radii in km for density computation
- `--isolation-threshold` - Threshold for isolation classification
- `--region-filter` - Optional city/county filter
- `--run-id` - Unique identifier for this run
- `--output-dir` - Results directory

**Output Files:**
- `spatial_features_summary.json` - Feature statistics
- `isolated_villages.csv` - List of isolated villages
- `density_distribution.png` - Density histogram

---

# Part F: Performance Characteristics

**Computation Time:**
- Full dataset (285k villages): ~2-5 minutes
- Regional subset (50k villages): ~30-60 seconds
- Bottleneck: Nearest neighbor search

**Memory Usage:**
- Peak memory: ~800 MB
- BallTree structure: O(n) space
- Feature matrix: ~50 MB for 285k villages

**Scalability:**
- BallTree construction: O(n log n)
- Per-village query: O(log n)
- Total complexity: O(n log n)

**Deployment Constraint:**
- ⚠️ **Offline only** - Never run on 2-core/2GB server
- Precompute features and save to database
- Online queries only read precomputed features

---

# Part G: Feature Interpretation

**Nearest Neighbor Distance:**
- Low (<0.5km): Dense urban settlements
- Medium (0.5-2km): Suburban or town areas
- High (>5km): Rural or isolated villages

**Local Density:**
- High (>50 within 5km): Urban centers
- Medium (10-50 within 5km): Towns and suburbs
- Low (<10 within 5km): Rural areas

**Isolation Score:**
- 0.0-0.3: Well-connected villages
- 0.3-0.7: Moderately isolated
- 0.7-1.0: Highly isolated (remote villages)

**Use Cases:**
- Outlier detection: Identify isolated villages
- Spatial clustering: Use as features for clustering
- Semantic analysis: Correlate isolation with naming patterns
- Infrastructure planning: Identify underserved areas

---

# Part H: Quality Checks

**Before Running:**
1. Verify coordinate data loaded correctly
2. Check for null/invalid coordinates
3. Confirm province bounds filtering
4. Ensure no duplicate villages

**After Running:**
1. Check feature distributions (histograms)
2. Verify isolation score range (0-1)
3. Inspect isolated villages on map
4. Validate density values are reasonable

**Expected Results:**
- Isolation score distribution: Right-skewed (most villages connected)
- Isolated villages: 5-10% of total
- Density distribution: Log-normal (few dense areas, many sparse)
- NN distance: Median ~1-2km for Guangdong

---

# Part I: Integration with Other Analyses

**Spatial Clustering (Skill 13):**
- Use spatial features as input to clustering
- Validate cluster assignments with density metrics
- Identify noise points using isolation score

**Semantic Analysis (Skill 4):**
- Correlate isolation with semantic indices
- Analyze naming patterns in isolated vs. connected villages
- Identify geographic-semantic associations

**Tendency Analysis:**
- Compare character tendencies in isolated vs. dense areas
- Analyze regional patterns with spatial context
- Identify spatial-linguistic boundaries

---

# Acceptance Criteria

1. ✅ Nearest neighbor distances computed for k=1,5,10
2. ✅ Local density computed for radii=1km,5km,10km
3. ✅ Isolation score calculated and normalized (0-1)
4. ✅ Features saved to `village_spatial_features` table
5. ✅ Cluster-based features included (if clusters exist)
6. ✅ Run ID tracked for reproducibility
7. ✅ Computation completes in <5 minutes for full dataset
8. ✅ Memory usage stays under 1GB
9. ✅ Output includes summary statistics and visualizations
