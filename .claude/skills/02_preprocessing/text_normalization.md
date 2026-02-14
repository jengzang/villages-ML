# Skill 01: Text Normalization & Character Extraction

## Skill Name
text_normalization_char_extraction

## Purpose

Define a deterministic and reproducible preprocessing pipeline for natural village names, producing:

- `clean_name`: normalized village name (string)
- `char_set`: set-deduplicated Chinese characters extracted from `clean_name`
- optional diagnostic fields (length, invalid char ratio, etc.)

This skill provides the single source of truth for all downstream statistics:
- high-frequency characters
- tendency scores
- semantic indices
- VTF
- morphology mining
- region clustering features

This skill does NOT require any system architecture work.
A Python script/module implementation is sufficient.


---

## Scope

Primary target column:
- 自然村 (natural village name)

Optional auxiliary column (not required in this skill, but allowed for logging/debug):
- 行政村

This skill does NOT edit database fields unless explicitly requested.
It creates derived outputs for analysis.


---

## Design Constraints

- Counting unit is **village**, not character occurrences.
- Within a single village name, each character must be counted at most once:
  - `char_set = set(chars(clean_name))`
- Deterministic output:
  - same input must yield the same `clean_name` and `char_set`.
- Conservative cleaning:
  - prefer leaving ambiguous content rather than over-deleting.
- Reproducibility:
  - all rules must be recorded and parameterized.


---

## Definitions

### Valid Chinese Character (Configurable)
Default definition:
- Unicode range: `\u4e00` to `\u9fff` (CJK Unified Ideographs)

Optional extensions (disabled by default unless instructed):
- CJK Extensions (rare characters)
- Compatibility Ideographs

### Punctuation / Noise
Characters considered noise (default removal):
- whitespace
- ASCII punctuation
- full-width punctuation
- common brackets and separators

Brackets content handling is configurable.


---

## Pipeline Specification (Step-by-Step)

### Step 0: Input Acquisition
For each row:
- read `raw_name = 自然村` as string
- handle NULL/empty:
  - if empty -> mark as invalid row; do not produce char_set

Output:
- `raw_name`
- `is_valid_row`


### Step 1: Basic Normalization
Apply:
- strip leading/trailing whitespace
- normalize internal whitespace to single (or remove all whitespace; default remove)

Optional (default enabled):
- convert full-width characters to half-width where applicable
- normalize common Unicode variants (NFKC) cautiously

Output:
- `name_norm1`


### Step 2: Bracket Handling (Configurable)
Village names may contain:
- parentheses: () （）
- brackets: [] 【】
- other separators

Default strategy:
- remove bracketed content entirely
  - Example: "石岭村(上村)" -> "石岭村"

Configuration options:
- `bracket_mode = remove_content | keep_content | remove_brackets_only`

Default:
- `remove_content`

Output:
- `name_norm2`


### Step 3: Noise Character Removal
Remove:
- punctuation (Chinese + ASCII)
- digits (Arabic)
- Latin letters (A-Z, a-z)
- special symbols

Keep:
- Chinese characters

Output:
- `name_hanzi_only`


### Step 4: Stopword/Structural Token Handling (Deferred)
This skill only prepares clean_name.
Stopword removal may be applied here if project decides so, but by default:

- DO NOT remove structural tokens like “村/社/队/组” at this stage
- Because some downstream tasks may want to keep them
- Stopword filtering is owned by Skill 02

Therefore:
- clean_name at this stage remains "hanzi-only normalized name"

Output:
- `clean_name`


### Step 5: Character Extraction + Set Deduplication (Mandatory)
Extract all Chinese characters from `clean_name` in order,
then produce:

- `char_list = [c1, c2, ...]`
- `char_set = set(char_list)`  # mandatory

Also produce:
- `name_len = len(clean_name)`
- `unique_char_cnt = len(char_set)`

Output:
- `clean_name`
- `char_set`
- `name_len`
- `unique_char_cnt`


### Step 6: Diagnostic Fields (Recommended)
Compute:
- `pct_hanzi = (#hanzi chars) / (#original chars after Step1)` (optional)
- `had_brackets = true/false`
- `had_noise_removed = true/false`

These help validate cleaning quality.


---

## Output Artifacts

This skill must produce at least one of:

1) A derived table (CSV):
- `results/<run_id>/village_cleaned.csv`

Columns (minimum):
- village_id (if available)
- region fields (city/county/town if available)
- raw_name
- clean_name
- name_len
- unique_char_cnt

And optionally a JSON-serializable representation of char_set:
- `char_set_json` (e.g., sorted list joined or JSON array)

2) Or a SQLite derived table:
- `village_cleaned`

Important:
- Do NOT modify the original DB in this skill by default.


---

## Edge Cases & Rules

### Edge Case A: Very Short Names
If `name_len <= 1`:
- keep, but mark as suspicious
- do not discard automatically

### Edge Case B: Non-Hanzi or Empty After Cleaning
If `clean_name == ""`:
- mark row invalid for downstream statistics
- record reason: "empty_after_cleaning"

### Edge Case C: Rare / Extended Characters
If encountering CJK extension characters:
- by default they are removed unless configured to keep
- record counts in a diagnostics report


---

## Quality Validation (Required)

This skill must output a basic validation summary:

- total rows processed
- valid rows count
- invalid rows count (empty/null/empty after cleaning)
- distribution of name_len (min/median/max)
- top 20 most common removed noise symbols (optional)
- sample before/after pairs (at least 20)

Save:
- `results/<run_id>/cleaning_report.txt` (or CSV)

(README updates are handled by `readme_update_protocol`)


---

## Performance Considerations

- Must be streamable: process rows in chunks if needed
- Avoid loading entire DB into memory if not necessary
- Output can be written incrementally


---

## Dependencies (Recommended)

- Python standard library: `re`, `unicodedata`, `json`
- Optional: pandas (for convenience)

No ML libraries required.


---

## Non-Goals

- No database editing
- No administrative prefix cleaning (handled by its own DB-edit skill)
- No numbered village normalization (handled by its own non-destructive skill)
- No clustering
- No tendency computation


---

## Acceptance Criteria

This skill is complete when:

1) A deterministic `clean_name` + `char_set` pipeline exists
2) `set()` deduplication is correctly applied per village
3) Outputs can be generated via Python scripts
4) A validation report is produced
