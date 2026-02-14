# Skill 10: Clustering Pipeline (Offline)

## Skill Name
clustering_pipeline_offline

## Purpose

Cluster regions (or optionally villages) based on:

- semantic feature vectors (from Skill 07)
- embedding vectors (from Skill 09)
- or combined feature sets

Strictly offline.


---

# Part A: Input Types

Must support:

1) region semantic vectors (preferred default)
2) region embedding vectors
3) concatenated feature vectors


---

# Part B: Preprocessing

Step 1:
Load feature matrix X

Step 2:
Apply scaling:
- StandardScaler (default)
- or precomputed scaler

Step 3 (optional):
Apply PCA if:
- dimension > 200

Default:
- n_components = 50


---

# Part C: KMeans Baseline

Default:

k_range = [4,6,8,10,12,15,18,20]
n_init = 20
max_iter = 500
random_state = 42

For each k:
- fit
- compute silhouette score
- compute Davies-Bouldin index

Select best k based on:
- highest silhouette
- reasonable cluster balance


---

# Part D: HDBSCAN (Optional)

Parameters:

min_cluster_size = 3 (county level)
min_samples = 2

Noise cluster labeled as -1.


---

# Part E: Output

Directory:
`results/<run_id>/clustering/`

Files:

- region_cluster_assignments.csv
- clustering_metrics.csv
- cluster_model.pkl
- pca_model.pkl (if used)


---

# Part F: Assignment Schema

Columns:

- region_id
- region_name
- cluster_id
- algorithm
- k (if KMeans)
- silhouette_score
- run_id


---

# Part G: Stability Check (Recommended)

Repeat clustering with different seeds:
- measure assignment overlap

If unstable:
- reconsider k or feature scaling


---

# Acceptance Criteria

1) Clusters generated
2) Metrics computed
3) Assignments saved
4) Models serialized
