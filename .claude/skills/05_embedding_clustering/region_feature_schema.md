# Skill: Region-Level Semantic Feature Vector Schema + Default Clustering Configuration

## Skill Name
region_feature_schema_and_default_clustering_config

## Purpose

Provide a concrete, unambiguous, field-level schema for:

1) Region-level semantic feature vectors
2) Offline regional semantic clustering configuration (default parameters)

This skill is designed to eliminate implementation ambiguity for Cloud Code:
- column names must be explicit
- feature definitions must be explicit
- output artifacts must be explicit
- defaults must be runnable with minimal changes

This skill does NOT require any system architecture work.
Python scripts that generate the tables are sufficient.


---

## Definitions

### Region Level
A region is one of:
- city (市)
- county/district (县/区)
- town (镇/街道)

`region_level` is a configuration parameter.

### Basic Unit
Village name is the counting unit.
Within each village name, characters are set-deduplicated before counting.

### Required Inputs (minimum)
- village_id
- 自然村 (natural village name)
- region identifiers:
  - city_name (市)
  - county_name (县/区)
  - town_name (镇/街道)
- optional: lon/lat (not required for this skill)

### Required Preprocessing
- `clean_name`
- `char_set(clean_name)` with set() deduplication
- stopwords filtering (if enabled)


---

# Part A: Feature Vector Table Schema

## A1. Output Table: region_vectors

### Table name
- CSV: `results/<run_id>/region_vectors.csv`
- SQLite table (optional): `region_vectors`

### Primary Keys
- `region_level` (string)   # "city" | "county" | "town"
- `region_id` (string)      # stable id or normalized region name
- `region_name` (string)

### Required Meta Columns
- `run_id` (string)                 # timestamp or hash id
- `region_level` (string)
- `region_id` (string)
- `region_name` (string)
- `N_villages` (int)                # count of villages included
- `avg_name_len` (float)            # average clean_name length
- `pct_valid_hanzi` (float)         # optional, 0..1 (if computed)
- `created_at` (string, ISO time)

### Feature Column Naming Convention

All feature columns must be prefixed:

- `sem_` for semantic category features
- `char_` for character-rate features
- `suf2_` for suffix-bigram features
- `suf3_` for suffix-trigram features
- `meta_` for metadata-derived numeric features

All categories/features must use consistent normalized identifiers.

Examples:
- `sem_water_intensity`
- `sem_mountain_lift`
- `suf2_坑尾_rate`
- `char_涌_rate`


---

## A2. Semantic Category Features (Required Baseline)

Semantic features are derived from lexicons.
Assume categories C in a fixed list (see A2.4).

### A2.1 Intensity (Required)

For each category C:

Let:
- S_i = set of unique characters in village i
- L_C = lexicon set for category C
- score_i(C) = |S_i ∩ L_C|

Regional raw intensity:

`sem_<C>_intensity = ( Σ score_i(C) ) / N_villages`

Interpretation:
- average number of category-related characters per village name (set-deduped)

### A2.2 Coverage (Optional but recommended)

Binary coverage per village:
- covered_i(C) = 1 if score_i(C) > 0 else 0

Regional coverage:

`sem_<C>_coverage = ( Σ covered_i(C) ) / N_villages`

Interpretation:
- fraction of villages that contain at least one character from category C

### A2.3 Lift / Normalized Index (Recommended)

Compute global baselines over all regions (province-wide):

`global_intensity(C) = ( Σ_all score_i(C) ) / N_all`

Lift:

`sem_<C>_lift = sem_<C>_intensity / global_intensity(C)`

Optional log form:

`sem_<C>_loglift = log(sem_<C>_lift)`

### A2.4 Required Semantic Category Set (Core)

These categories must exist as lexicons (characters listed in Chinese; maintained in lexicon builder):

- mountain (山地地形类)
- water (水系相关类)
- settlement (聚落形态类)
- direction (方位类)
- clan (宗族姓氏类)
- symbolic (象征信仰类)
- agriculture (农业耕作类)
- vegetation (植物生态类)
- transport (交通基础设施类)

The category names used in columns are:

- `mountain`
- `water`
- `settlement`
- `direction`
- `clan`
- `symbolic`
- `agriculture`
- `vegetation`
- `transport`


---

## A3. Character Rate Features (Optional, Controlled Dimensionality)

Character-rate features are computed only for a selected vocabulary V.

### A3.1 Vocabulary selection (Recommended default)
Select top `V_char = 1000` characters province-wide by village-level frequency.

This vocabulary must be saved:
- `results/<run_id>/vocab_chars_top1000.txt`

### A3.2 Feature definition

For each character c in V:

Let:
- n_{g,c} = number of villages in region g whose char_set contains c (binary per village)
- N_g = N_villages

`char_<c>_rate = n_{g,c} / N_g`

Note:
- This uses village-level binary presence, consistent with set() deduplication.

### A3.3 Optional transforms

- `char_<c>_lograte = log(1 + char_<c>_rate)`
- or z-score across regions (only if needed for clustering)

### A3.4 Dimensionality guards
- Do NOT exceed 2000 char features by default.
- Use 500–1000 initially for stability.


---

## A4. Morphology Features: Suffix Bigram/Trigram Rates (Optional but highly interpretable)

Suffix patterns provide strong linguistic signal.

### A4.1 Pattern extraction (Required rule)
From each clean_name:

- if len >= 2: extract last 2 characters as `suffix2`
- if len >= 3: extract last 3 characters as `suffix3`

Suffixes should be extracted after cleaning but before stopword removal (configurable).

### A4.2 Vocabulary selection (Recommended default)
Select top suffixes province-wide:

- `V_suf2 = 1000` bigram suffixes
- `V_suf3 = 1000` trigram suffixes

Save:
- `results/<run_id>/vocab_suf2_top1000.txt`
- `results/<run_id>/vocab_suf3_top1000.txt`

### A4.3 Feature definition
For each suffix S:

`count_g(S) = number of villages in region g whose suffix == S`

`rate_g(S) = count_g(S) / N_g`

Columns:

- `suf2_<S>_rate`
- `suf3_<S>_rate`

Example columns (Chinese suffix must remain Chinese in column name):
- `suf2_坑尾_rate`
- `suf2_涌口_rate`
- `suf3_水口村_rate` (if trigram suffix captured)


---

## A5. Diversity Features (Optional)

### A5.1 Suffix entropy
For region g, with suffix distribution p(S):

`meta_suffix2_entropy = - Σ p(S) log p(S)`

Interpretation:
- higher entropy = more suffix diversity

### A5.2 Semantic balance indices (Recommended)
Mountain-water balance:

`meta_mw_balance = (sem_mountain_intensity - sem_water_intensity) / (sem_mountain_intensity + sem_water_intensity + eps)`

Where eps = 1e-9.

Coverage difference (optional):
`meta_mw_coverage_diff = sem_mountain_coverage - sem_water_coverage`


---

# Part B: Default Preprocessing + Scaling Rules

## B1. Cleaning defaults (minimum)

- strip spaces
- remove punctuation
- keep Chinese characters only (configurable; conservative)
- build set() for counting

## B2. Feature scaling defaults for clustering

### Recommended default path (robust & simple)

- Semantic features (`sem_*_intensity`, `sem_*_lift`, `meta_*`):
  - apply StandardScaler (z-score across regions)

- Character rates and suffix rates (if included):
  - apply log(1+x) transform then StandardScaler

This prevents heavy-tailed features from dominating distance metrics.

### Output artifacts
Save scaling parameters:
- `results/<run_id>/scaler.pkl` (if using sklearn)
- or JSON summary of means/stds


---

# Part C: Dimensionality Reduction Defaults (PCA)

## C1. When to use PCA
- If you include char_ and/or suffix features and dimension > 200,
  PCA is recommended for KMeans stability.

## C2. Default PCA config

- `pca_enabled = true` when total feature dim >= 300
- `pca_n_components = 50` (default)
- Alternative: choose components to explain 90% variance (optional)

Output:
- `results/<run_id>/pca.pkl`
- `results/<run_id>/pca_explained_variance.csv`


---

# Part D: Default Clustering Configurations

This skill must provide runnable defaults for two algorithms:
- KMeans baseline
- HDBSCAN optional (if installed)

## D1. KMeans Default (Baseline)

### Parameter defaults
- `k_range = [4, 6, 8, 10, 12, 15, 18, 20]`
- `n_init = 20`
- `max_iter = 500`
- `random_state = 42`

### Selection metric defaults
Evaluate each K by:
- silhouette score (higher is better)
- Davies–Bouldin index (lower is better)

Pick K with:
- high silhouette
- reasonable cluster sizes
- interpretable cluster descriptors

Save:
- `results/<run_id>/kmeans_model.pkl`
- `results/<run_id>/kmeans_metrics.csv`
- `results/<run_id>/region_cluster_assignments.csv`

Assignments schema:
- region_id
- region_name
- cluster_id
- algorithm = "kmeans"
- k
- run_id


---

## D2. HDBSCAN Default (Optional Robustness)

Only apply if library exists; otherwise skip.

### Parameter defaults
- `min_cluster_size = 5` (town level) / `3` (county level)
- `min_samples = 2`
- `metric = "euclidean"` (after scaling/PCA)
- `cluster_selection_method = "eom"`

Outputs:
- `results/<run_id>/hdbscan_model.pkl`
- `results/<run_id>/hdbscan_assignments.csv`
- include `probability` if available

Assignment schema:
- region_id
- region_name
- cluster_id (noise = -1)
- probability (optional)
- algorithm = "hdbscan"
- run_id


---

# Part E: Cluster Interpretation Output Schema (Mandatory)

## E1. Output Table: cluster_profiles

File:
- `results/<run_id>/cluster_profiles.csv`

Columns:
- run_id
- algorithm
- cluster_id
- cluster_size
- top_features_json
- top_semantic_categories_json
- top_suffixes_json (if suffix features enabled)
- representative_regions_json

### Distinguishing feature calculation (default)
For each cluster k:
- compute mean feature vector μ_k
- compute global mean μ_global
- compute contrast:
  - `contrast = (μ_k - μ_global) / (σ_global + eps)`  # standardized difference
Pick top positive and top negative features.

Store as JSON arrays for compactness:
- top_features_json: [{"feature": "...", "z_diff": ...}, ...]


---

# Part F: Online Serving Constraints (Explicit)

The final deployment environment is 2-core / 2GB.

Therefore:
- online service MUST NOT recompute embeddings
- online service MUST NOT recompute PCA
- online service MUST NOT run clustering
- online service MUST only load:
  - region_cluster_assignments
  - cluster_profiles
  - optionally region_vectors (for display)
All heavy computation is offline.


---

# Required Deliverables of This Skill

This skill must deliver:

1) A concrete region feature schema as defined above
2) A default clustering configuration (KMeans + optional HDBSCAN)
3) Clear, reproducible output artifact formats
4) Run logging requirements (run_id, params, metrics)
5) README update in Simplified Chinese with:
   - how to run vector generation
   - how to run clustering
   - where outputs are saved
   - update log entry

No new documentation files.
Everything goes to README.


---

# Notes on Chinese Column Names

Suffix and character columns may contain Chinese tokens in column names.

This is acceptable as long as:
- CSV is UTF-8
- downstream code reads by exact column names
- column generation is deterministic

If column name encoding becomes problematic,
store feature names in a separate mapping file:

- `feature_index.json`
  - idx -> feature_name

But default approach is human-readable Chinese in column names.
# Default Configuration Summary (Copy/Paste)

region_level: county
use_semantic_features: true
use_char_features: false
use_suffix_features: true

V_char: 1000
V_suf2: 1000
V_suf3: 1000

transform_rates: log1p
scaler: standard

pca_enabled: true
pca_n_components: 50

clustering:
  algorithm_primary: kmeans
  k_range: [4, 6, 8, 10, 12, 15, 18, 20]
  n_init: 20
  max_iter: 500
  random_state: 42

optional_hdbscan:
  enabled_if_available: true
  min_cluster_size: 3
  min_samples: 2
