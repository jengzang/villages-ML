# Skill 03: Character Frequency Engine

## Skill Name
char_frequency_engine

## Purpose

Compute high-frequency character statistics
at configurable regional levels.

This engine must support:

- province-level statistics
- city-level statistics
- county-level statistics
- town-level statistics

Counting unit:
- village-level binary presence
- set() deduplicated per village


---

## Mathematical Definition

Let:

S_i = set of unique characters in village i (after stopword filtering if enabled)

For region g:

n_{g,c} =
  number of villages in region g
  whose char_set contains c

N_g =
  total number of valid villages in region g

Frequency:

p_g(c) = n_{g,c} / N_g


---

## Configuration Parameters

region_level:
- province
- city
- county
- town

min_count_threshold:
- default = 10 (province level)
- configurable

use_filtered_chars:
- true / false


---

## Output Table: char_frequency

File:
- `results/<run_id>/char_frequency_<region_level>.csv`

Columns:

- region_level
- region_id
- region_name
- char
- village_count
- N_villages
- frequency
- rank_within_region
- global_frequency
- lift_vs_global


---

## Global Baseline

Compute:

n_global(c)
N_global

global_frequency(c) = n_global(c) / N_global

lift:

lift_vs_global = p_g(c) / global_frequency(c)


---

## Ranking

Within each region:

Sort by:
- village_count DESC
- frequency DESC

Assign:
- rank_within_region


---

## Optional Enhancements

- top_k per region
- entropy of character distribution
- Gini coefficient of char distribution


---

## Performance Strategy

- Use groupby on region
- Precompute char_set once
- Avoid recomputing per query

For 200k villages:
- this is computationally trivial


---

## Diagnostic Report

Generate:

- total unique characters province-wide
- top 50 characters overall
- long-tail distribution summary
- region with highest diversity


---

## Non-Goals

- No semantic grouping
- No clustering
- No embedding
- No LLM usage


---

## Acceptance Criteria

1) Output char_frequency table exists
2) lift_vs_global computed
3) set() deduplication confirmed
4) Threshold filtering supported
