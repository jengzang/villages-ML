# Skill: Semantic Vectorization (Region-Level) + Regional Semantic Clustering

## Skill Name
regional_semantic_vectorization_and_clustering

## Purpose

Build region-level semantic vectors from village-name statistics and perform clustering to discover
groups of regions with similar naming semantics.

This avoids heavy LLM usage and avoids per-village embedding at runtime.
It is designed for:
- offline heavy computation (allowed)
- lightweight online serving (2-core/2GB)

Key outcome:
- region clusters (e.g., counties/towns) based on semantic naming profiles
- interpretable cluster descriptors (top distinguishing categories / suffixes / characters)


---

## Inputs

1) Cleaned village-name representation per village:
- `clean_name`
- `char_set` (set-deduplicated)

2) Region mapping:
- region level: city / county / town (configurable)
- `region_id` or `region_name`

3) Semantic lexicons:
- categories (mountain, water, settlement, etc.) from `semantic_lexicon_builder`

4) Optional morphology features:
- suffix bigrams/trigrams from `toponym_morphology_mining`

All computation uses offline scripts.


---

## Output Artifacts

### Core outputs (must-have)
- `region_vectors.csv` (or SQLite table)
  - region_id
  - feature vector (stored as multiple columns)
- `region_cluster_assignments.csv`
  - region_id
  - cluster_id
  - algorithm + parameters
- `cluster_profiles.csv`
  - cluster_id
  - top distinguishing features (interpretable)

### Optional outputs
- PCA/UMAP 2D projection for visualization (offline)
- silhouette / Davies–Bouldin metrics for model selection


---

## Phase 1: Region-Level Semantic Vector Construction

### 1.1 Feature families

Construct a concatenated feature vector per region g:

A) Semantic category intensity features (recommended baseline)
- For each category C:
  - `intensity(C,g) = Σ |char_set(v) ∩ Lexicon_C| / N_g`
  - optionally normalized by global baseline

B) Character distribution features (optional)
- For a selected vocabulary V (e.g., top 1000 chars province-wide):
  - `char_rate(c,g) = n_{g,c} / N_g`
- Use only top chars to control dimensionality

C) Morphology features (optional, high interpretability)
- Top suffix bigrams/trigrams S (e.g., top 2000):
  - `suffix_rate(S,g) = count_g(S)/N_g`

D) Diversity / structure features (optional)
- suffix entropy H_g
- average name length (after cleaning)
- proportion of names that contain water/mountain signals


---

### 1.2 Feature scaling

Before clustering, apply scaling:

- StandardScaler (z-score) for continuous features
- Optionally apply log transform for heavy-tailed rates:
  - `log(1 + x)`

Important:
- Store scaling parameters for reproducibility.


---

### 1.3 Dimensionality control (recommended)

If you include char/suffix rates, dimensionality can grow quickly.

Suggested approach:
- semantic categories: keep all (small)
- char features: top 500–2000 only
- suffix features: top 500–2000 only
- optionally use PCA to reduce to 20–100 dims before clustering


---

## Phase 2: Regional Semantic Clustering (Offline)

### 2.1 Candidate algorithms

A) KMeans (fast, baseline)
- good for spherical clusters
- requires K selection

B) HDBSCAN (recommended if available)
- handles varying density
- can label noise
- does not require K

C) Agglomerative clustering (optional)
- good for interpretability via dendrogram

Preferred default:
- start with KMeans for baseline
- optionally switch to HDBSCAN for robustness


---

### 2.2 Model selection

If using KMeans:
- evaluate K in a range (e.g., 4..20)
- metrics:
  - silhouette score (higher better)
  - Davies–Bouldin (lower better)
- pick K that balances interpretability and stability

If using HDBSCAN:
- tune:
  - min_cluster_size
  - min_samples
- inspect cluster sizes and stability


---

## Phase 3: Cluster Interpretation (Must-have)

Clustering without interpretation is weak.
This skill must output interpretable descriptions for each cluster.

### 3.1 Compute cluster centroid / mean profile

For each cluster k:
- compute mean feature vector μ_k

### 3.2 Distinguishing features

For each cluster k, compute "contrast" against all others:

- lift: μ_k / μ_global
- or z-diff: (μ_k - μ_global) / σ_global

Report top features:
- Top semantic categories (mountain/water/etc.)
- Top suffixes (e.g., “X涌”, “X坑”)
- Top chars if included

### 3.3 Representative regions

For each cluster:
- list top N regions closest to centroid
- helps manual inspection and qualitative validation


---

## Phase 4: Reproducibility & Logging

Every run must record:

- date/time
- region level (city/county/town)
- features included (semantic only vs +char vs +suffix)
- vocabulary sizes
- scaling strategy
- dimensionality reduction (PCA dims if used)
- clustering algorithm + parameters
- evaluation metrics

Store under:
- `results/run_<timestamp>/` (or equivalent)


---

## Runtime (Online) Constraint Handling

Online server must NOT recompute vectors or clusters.

Online serving should only:
- load precomputed cluster assignments
- allow filtering by region
- display cluster profile summary

All heavy work is offline.


---

## Quality Checks (Required)

Before accepting a clustering result:

1) Cluster size sanity:
- avoid clusters with 1–2 regions unless expected
2) Geographic sanity (optional):
- check if clusters correspond to known macro-regions (Pearl River Delta vs north etc.)
3) Feature sanity:
- cluster descriptors should be interpretable (e.g., water vs mountain dominance)
4) Stability test:
- rerun with different seed; check assignment stability (KMeans)


---

## Deliverables

This skill must produce:

- scripts to generate region vectors
- scripts to run clustering and output assignments
- scripts to generate cluster interpretation tables
- update README in Simplified Chinese with:
  - how to run
  - what outputs mean
  - update log entry

No new documentation files.
