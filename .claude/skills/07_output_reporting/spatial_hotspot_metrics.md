# Skill 12: Spatial Hotspot Metrics (Optional Research Extension)

## Skill Name
spatial_hotspot_metrics_optional

## Purpose

Add spatial statistical rigor to semantic or character distributions.

This skill is research-oriented.
It enhances academic value but is optional for production deployment.

Requires:
- region-level coordinates (centroids)
or
- village-level coordinates


---

# Part A: Input Requirements

At minimum:

- region_id
- region semantic indices (e.g., mountain index, water index)
- region centroid longitude/latitude

Village-level hotspot analysis optional.


---

# Part B: Moran's I (Global Spatial Autocorrelation)

For feature F (e.g., water index):

Compute Moran's I:

I =
  (N / W)
  *
  ( Σ_i Σ_j w_ij (F_i - F̄)(F_j - F̄) )
  /
  Σ_i (F_i - F̄)^2

Where:
- w_ij = spatial weight (e.g., adjacency or inverse distance)
- W = sum of weights

Interpretation:
- I > 0 → clustering
- I < 0 → dispersion


---

# Part C: Local Moran's I (LISA)

Identify hotspot regions:

For each region i:

Compute local statistic:
I_i

Classify:
- High-High (hotspot)
- Low-Low (coldspot)
- High-Low
- Low-High


---

# Part D: Optional Getis-Ord Gi*

Alternative hotspot metric for detecting high-value clusters.


---

# Part E: Output

Files:

- spatial_moran_global.csv
- spatial_moran_local.csv
- hotspot_regions.csv

Columns:

- region_id
- feature
- I_value
- p_value
- hotspot_type


---

# Part F: Performance

Region-level computation is lightweight.
Village-level may require spatial indexing.


---

# Acceptance Criteria

1) Moran's I computed
2) Local hotspots identified
3) Results saved
4) No production server heavy computation
