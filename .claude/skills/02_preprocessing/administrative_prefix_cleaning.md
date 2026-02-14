# Skill: Administrative Prefix Cleaning (Database Editing) — Updated

## Skill Name
`administrative_prefix_cleaning`

## Purpose

Detect and remove redundant administrative-village prefixes embedded in natural-village names.

This skill **is allowed to modify the database** (edits 自然村 only).

The goal is to correct structural redundancy and reduce noise for downstream statistics.


---

## Scope

Affected columns:

- 行政村
- 自然村

Only 自然村 may be edited.
行政村 remains unchanged.


---

## Core Idea (Updated)

Before matching 自然村 against the corresponding 行政村 in the same row, the system must **prioritize natural-name parsing**:

1. **First attempt to split/segment 自然村 into two parts** (i.e., detect whether 自然村 is composed of an administrative-like prefix + a remaining suffix).
2. Then validate the candidate prefix using:
   - the row’s 行政村, AND/OR
   - a broader lookup of 行政村 within the same town/county/city if needed.

Rationale:
- Sometimes the row’s 行政村 does not match perfectly, but 自然村 still clearly contains an embedded administrative prefix.
- The embedded prefix may appear **without explicit delimiters** such as “村”.
  - Example: 行政村=魁头村, 自然村=魁头三角村 (no “村” delimiter inside 自然村)
  - Examples:
    - 行政村：石岭村  
    - 自然村：石岭村上村

    - 行政村：龙岗  
    - 自然村：龙岗村新村

    - 行政村：葵山村
    - 自然村：葵山土头村


---

## Step 0: Length Guard (Conservative Entry Filter)

Before attempting any split or match:

- If 自然村 length ≤ 3 (or ≤ 4, configurable), do not attempt prefix removal.
  - Too short to reliably contain an extra embedded prefix.
- For longer names, proceed.


---

## Step 1: Natural-Village Name Parsing (Split First)

The system should attempt to identify whether 自然村 can be decomposed into:

- `prefix_candidate + suffix_candidate`

Parsing heuristics (non-exhaustive, must remain conservative):

1. Try prefix lengths of 2–3 characters (configurable)
2. Consider common delimiter characters if present (optional):
   - “村”“寨”“坊”“圩”“墟”“围”“片”“组”等
3. If no delimiter exists, still try prefix candidates based on:
   - first 2 chars
   - first 3 chars

The objective is to generate a small set of plausible `prefix_candidate` values for later validation.


---

## Step 2: Match & Validate Prefix Candidate

Validation must happen in the following priority order:

### 2.1 Row-Level Match (Primary)

Compare `prefix_candidate` to the row’s 行政村 using flexible rules:

- Normalize 行政村 by optionally removing trailing:
  - “村”
  - “寨”
- Compare:
  - exact prefix match against normalized 行政村
  - or 2–3 char partial match

### 2.2 Local Search Match (Fallback)

If row-level match fails but prefix_candidate seems plausible:

- Search administrative-village names in the **same region scope** (preferably same 镇/县/市).
- Use `prefix_candidate` (first 2 or 3 chars) as the search key.
- Prefer the closest match under these constraints:
  - same 镇 > same 县 > same 市 (priority order)
- Matching must remain conservative; avoid fuzzy edit-distance matching unless explicitly instructed.

This step is designed for cases where:
- the row’s 行政村 is missing/incorrect
- but 自然村 still contains a valid administrative-like prefix


---

## Step 3: Editing Rule (Database Write)

If validation confidence is high:

- Remove the validated prefix from 自然村 (strip only at the beginning)
- Persist the edited 自然村 back to the database

Hard restrictions:

- Never remove internal substrings (only prefix)
- Never remove more than one prefix segment in a single pass (unless explicitly instructed)
- Avoid aggressive stripping; prefer false negatives over false positives


---

## Step 4: Reporting & Safety

After batch processing:

- Output a validation summary:
  - number of affected rows
  - top patterns encountered
  - representative before/after samples (at least 20)
  - any ambiguous cases skipped

All DB edits must follow `db_backup_safe_edit_workflow`:
- backup before edit
- retain backup until user confirmation
- do not commit DB files
- delete backup only after user confirms results are valid


---

## Commit Requirement

After code changes (scripts/rules/logs/README updates):

- perform a git commit when the user says “提交”
- commit message must clearly describe:
  - parsing strategy (split-first)
  - match strategy (row-level + local search fallback)
  - safety guards (length threshold, conservative rules)
- do NOT push
- do NOT commit database files


---

## Design Philosophy

- Split-first parsing is mandatory before relying solely on row-level 行政村 matching.
- Conservative behavior is required: skip ambiguous edits rather than over-edit.
- Edits must be explainable and reproducible.

This skill improves:
- frequency statistics reliability
- tendency analysis robustness
- downstream NLP/semantic analysis quality
