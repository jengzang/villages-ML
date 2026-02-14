# Skill: Toponym Semantic Index Engine

## Skill Name
toponym_semantic_index_engine

## Purpose

Construct quantitative semantic indices for each region
based on predefined semantic lexicons (mountain, water, settlement, etc.).

This engine transforms raw character statistics into
interpretable semantic intensity measures.

No LLM required.


---

## Core Idea

Each village contributes a semantic signal.

For village i:

Let S_i be the set of unique characters in the cleaned village name.

For category C:

semantic_score_i(C) = |S_i ∩ Lexicon_C|

At regional level g:

SemanticIntensity(C, g) =
  ( Σ semantic_score_i(C) ) / N_g

Where:
- N_g = number of villages in region g


---

## Normalized Index

To make values comparable:

NormalizedSemanticIndex(C, g) =
  SemanticIntensity(C, g) / GlobalSemanticIntensity(C)

Optional:
- Z-score normalization
- Log transformation


---

## Derived Indices

### 1️⃣ Mountain Index
Based on mountain lexicon

### 2️⃣ Water Index
Based on water lexicon

### 3️⃣ Settlement Index
Based on settlement lexicon

### 4️⃣ Directional Index

### 5️⃣ Clan Index

### 6️⃣ Agriculture Index

Each region will have a vector:

RegionProfile_g =
[
  MountainIndex,
  WaterIndex,
  SettlementIndex,
  DirectionIndex,
  ClanIndex,
  AgricultureIndex,
  VegetationIndex
]


---

## Output Table

For each region:

- region_name
- category
- raw_count
- normalized_index
- z_score (optional)
- rank_within_province


---

## Research Value

This allows:

- Comparing regional naming structures
- Identifying semantic dominance patterns
- Constructing a multi-dimensional naming profile per region
- Supporting spatial clustering analysis later

