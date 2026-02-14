# Skill 11: Cluster Interpretation & Contrast

## Skill Name
cluster_interpretation_contrast

## Purpose

Provide interpretable explanations for clusters.

Clustering alone is meaningless without interpretation.


---

# Part A: Cluster Mean Profiles

For cluster k:

μ_k = mean(feature vectors of regions in cluster)

Global mean:

μ_global


---

# Part B: Contrast Score

For feature f:

contrast(k,f) =
  (μ_k[f] - μ_global[f]) / (std_global[f] + eps)

Rank features by contrast.


---

# Part C: Output

File:
`results/<run_id>/cluster_profiles.csv`

Columns:

- cluster_id
- cluster_size
- top_positive_features_json
- top_negative_features_json
- representative_regions_json


---

# Part D: Human-Readable Interpretation

For each cluster:

List:

- dominant semantic categories
- dominant suffix patterns
- distinguishing characters

Example:

Cluster 3:
- High water index
- Dominant suffix: X涌, X湾
- Strong negative mountain index

This must be generated programmatically.


---

# Acceptance Criteria

1) Cluster profiles generated
2) Top distinguishing features identified
3) Output JSON stored
4) Ready for visualization
