# New Skill: Online Artifact Serving Only Policy (Prevent Accidental Online Heavy Compute)

## Skill Name
online_artifact_serving_only_policy

## Purpose

Prevent the system from drifting into online heavy computation
once interactive APIs are introduced.

This skill enforces a strict runtime policy:
- online endpoints only read materialized tables
- no expensive recomputation
- all heavy computation must be offline jobs


---

## Policy Rules

Online API may:
- filter by region/tag/cluster_id/suffix/char (prefer indexed columns)
- paginate results
- join small tables by indexed keys
- compute small aggregations on already-filtered subsets

Online API must NOT:
- compute embeddings
- run clustering
- compute province-wide frequencies
- scan entire village table without filters
- rebuild indexes


---

## Enforcement Mechanisms (Recommended)

- A runtime config flag:
  - `ALLOW_ONLINE_HEAVY_COMPUTE = false` by default
- A query cost guard:
  - reject queries that lack region constraints AND request large results
- A max-row hard limit:
  - e.g., 5000 rows per request
- mandatory pagination


---

## Acceptance Criteria

1) APIs are limited to reading materialized artifacts
2) Expensive computations are rejected or routed to offline pipeline
3) The system remains stable on 2-core/2GB
