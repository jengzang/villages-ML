# New Skill: Offline Feature Tagging Pipeline (Materialized Tags)

## Skill Name
offline_feature_tagging_pipeline

## Purpose

Perform offline heavy computation to produce per-village tags and per-region features,
then materialize them into database tables for fast online queries.

This is the recommended approach to maximize:
- statistical depth
- frontend controllability
- runtime performance on 2-core/2GB


---

## Core Outputs

### 1) Village-level tags table (must-have)
A table mapping each village to a set of semantic and structural tags.

### 2) Region-level aggregated feature tables (must-have)
Materialized precomputed statistics for city/county/town.

### 3) Optional inverted indexes (top-N only)
For fast “contains_char/suffix/tag” queries without full scans.


---

## Village Tagging Design

### Tag Types

A) Semantic tags (from lexicons)
- water_related
- mountain_related
- settlement_related
- direction_related
- clan_related
- symbolic_related
- agriculture_related
- vegetation_related
- transport_related

Definition (per village):
- tag is true if char_set intersects lexicon category

B) Morphology tags (suffix/prefix patterns)
- suffix2 = last 2 chars
- suffix3 = last 3 chars
- optional: prefix2/prefix3

C) Numeric normalization flags (non-destructive concept)
- has_chinese_numeral_suffix (一二三四五六七八九十)
- base_name (derived, for aggregation only)

D) Data quality flags
- short_name
- empty_after_cleaning
- suspicious_symbols_removed


---

## Materialized Tables (Recommended Schema)

### Table: village_features (offline-written)

Columns:
- village_id (PK)
- raw_name
- clean_name
- name_len
- city_name
- county_name
- town_name

Semantic boolean tags:
- tag_water (0/1)
- tag_mountain (0/1)
- tag_settlement (0/1)
- tag_direction (0/1)
- tag_clan (0/1)
- tag_symbolic (0/1)
- tag_agriculture (0/1)
- tag_vegetation (0/1)
- tag_transport (0/1)

Morphology fields:
- suffix2
- suffix3
- prefix2 (optional)
- prefix3 (optional)

Normalization flags:
- has_cn_num_suffix (0/1)
- base_name_for_stats (string)

Lineage fields:
- run_id
- lexicon_version
- stopword_version
- created_at


---

## Region Aggregates Materialization

Create separate tables for:
- city_aggregates
- county_aggregates
- town_aggregates

Each should store:
- N_villages
- semantic indices (intensity/coverage/lift)
- top-k suffixes (precomputed list or separate table)
- top-k tendency chars (precomputed list or separate table)
- cluster_id (if clustering computed)
- run_id


---

## Optional Top-N Inverted Index Tables (Strongly Bounded)

If needed for performance, build ONLY for top-N tokens:

### char_index_topN
- char
- village_id

### suffix_index_topN
- suffix2 / suffix3
- village_id

N default:
- 2000 max

For rare chars not in index:
- online fallback is allowed but must be limited (region filter + hard limit + pagination).


---

## Safety & Backup

If writing to DB:
- must follow db_backup_safe_edit_workflow
- do not commit DB files
- keep backups until user confirms validity


---

## Acceptance Criteria

1) Offline scripts produce village_features table
2) Region aggregate tables exist and are queryable
3) All outputs are versioned by run_id
4) Online can serve queries without heavy compute
