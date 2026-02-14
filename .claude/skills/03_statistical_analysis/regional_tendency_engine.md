# Skill 04: Regional Tendency Engine (Character-Level)

## Skill Name
regional_tendency_engine

## Purpose

Compute statistically meaningful regional tendency scores
for characters (and optionally suffixes or semantic categories).

This engine goes beyond raw frequency and measures:

- overrepresentation
- underrepresentation
- deviation from provincial baseline
- statistical stability (small-sample control)

It must support:

- city / county / town level
- configurable minimum thresholds
- smoothing to avoid small-count inflation

No clustering or embedding is involved here.


---

# Part A: Definitions

Let:

S_i = set of unique characters in village i  
(after stopword filtering if enabled)

For region g:

n_{g,c} =
  number of villages in region g whose S_i contains c

N_g =
  total number of valid villages in region g

Global:

n_{*,c} =
  total villages province-wide whose S_i contains c

N_* =
  total valid villages province-wide


---

# Part B: Core Probability Measures

Regional probability:

p_g(c) = n_{g,c} / N_g

Global probability:

p(c) = n_{*,c} / N_*

These are village-level binary probabilities.


---

# Part C: Tendency Metrics

This skill must support multiple tendency metrics.

## C1. Lift (Baseline)

lift(c,g) = p_g(c) / p(c)

Interpretation:
- >1 → overrepresented
- <1 → underrepresented
- =1 → neutral

Problem:
- unstable when p(c) is very small


---

## C2. Log-Lift (Recommended)

log_lift(c,g) = log( p_g(c) / p(c) )

Symmetric around 0.

More interpretable for statistical ranking.


---

## C3. Smoothed Log-Odds (Recommended for Robustness)

To reduce small-sample inflation:

Add Laplace smoothing α (default α=1):

p_g'(c) =
  (n_{g,c} + α) / (N_g + 2α)

p'(c) =
  (n_{*,c} + α) / (N_* + 2α)

log_odds(c,g) =
  log( p_g'(c) / (1 - p_g'(c)) )
  -
  log( p'(c) / (1 - p'(c)) )

This is much more stable than raw lift.


---

## C4. Z-score Deviation (Optional)

Let expected count:

E_{g,c} = N_g * p(c)

Variance (binomial approximation):

Var_{g,c} = N_g * p(c) * (1 - p(c))

z_score(c,g) =
  (n_{g,c} - E_{g,c}) / sqrt(Var_{g,c} + eps)

Interpretation:
- >2 significant overrepresentation
- <-2 significant underrepresentation

Use eps = 1e-9 to avoid division by zero.


---

# Part D: Filtering Strategy (Mandatory)

To avoid noise:

Apply minimum thresholds:

- n_{*,c} >= 20 (global support threshold)
- n_{g,c} >= 5 (regional support threshold)

If thresholds not met:
- do not compute tendency
- mark as low_support

These thresholds must be configurable.


---

# Part E: Output Table Schema

File:
`results/<run_id>/regional_tendency_<region_level>.csv`

Columns:

- run_id
- region_level
- region_id
- region_name
- char
- n_region
- N_region
- p_region
- n_global
- p_global
- lift
- log_lift
- log_odds
- z_score
- support_flag
- rank_overrepresented
- rank_underrepresented


---

# Part F: Ranking Strategy

Within each region:

Sort by:
- log_odds DESC (overrepresented ranking)
- log_odds ASC (underrepresented ranking)

Assign:
- rank_overrepresented
- rank_underrepresented


---

# Part G: Optional Extension (Suffix Tendency)

This engine must optionally support suffix patterns:

Replace:
- c (character)
with:
- S (suffix)

All formulas remain identical.


---

# Part H: Diagnostic Report

Produce:

- region with strongest positive deviation overall
- region with strongest negative deviation overall
- top 20 province-wide most regionally polarized characters
- histogram of log_odds distribution

Save:
`results/<run_id>/tendency_report.txt`


---

# Part I: Statistical Integrity Requirements

This engine must:

- never mix village-level and character-frequency counts
- always operate on village-level binary presence
- always use consistent smoothing parameter α
- log threshold values used in run metadata


---

# Part J: Performance

For 200k villages:
- complexity roughly O(total unique char occurrences)
- must use precomputed char_set
- grouping via pandas groupby is acceptable


---

# Acceptance Criteria

This skill is complete when:

1) Lift, log_lift, log_odds, and z_score are implemented
2) Threshold filtering exists
3) Rankings generated per region
4) Output CSV generated
5) Diagnostic report produced
6) README updated via update skill
