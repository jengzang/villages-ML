# Skill 02: Stopwords & Structural Token Rules

## Skill Name
stopwords_structural_rules

## Purpose

Define a deterministic, version-controlled rule system for:

1) Structural token filtering (e.g., 村 / 社 / 队 / 组 etc.)
2) Optional stopword removal
3) Controlled normalization strategies for downstream statistics

This skill refines `clean_name` produced by:
- text_normalization_char_extraction

It does NOT modify raw database fields by default.
It produces derived analytical fields.

This skill ensures:
- consistent statistical basis
- controlled removal of structural noise
- reproducibility across runs


---

## Design Philosophy

Village names often contain structural tokens that:
- carry low semantic signal
- artificially inflate frequency counts
- distort suffix analysis

Examples:
- 村
- 社
- 队
- 组
- 片
- 屯
- 坊
- 里

However:
- In some analyses (e.g., morphology mining),
  structural tokens must be preserved.

Therefore:

Stopword filtering must be configurable and not destructive.


---

## Stopword Categories

Stopwords are divided into semantic types:

### 1️⃣ Structural Suffix Tokens (Default: removable in char stats)

村  
社  
队  
组  
片  
屯  
坊  
里  
寨  
庄  
堡  
坊  
屋  
楼  
堂  
埠  
市  
场  
塆  

### 2️⃣ Administrative / Organizational Tokens (Optional removal)

行政  
自然  
管理  
社区  
委员会  
小组  
大队  
生产  

### 3️⃣ Functional Words (Rare but possible)

的  
和  
与  

(Default: rarely appear in village names; safe to ignore.)


---

## Stopword Configuration Modes

The skill must support three modes:

### Mode A: No Stopword Removal
- Use raw `clean_name`
- char_set = set(clean_name)

### Mode B: Char-Level Stopword Removal (Recommended for frequency stats)

- Remove stopword characters before building char_set
- Example:
  "石岭村上村" -> remove 村 -> "石岭上"

Then:
  char_set = set(filtered_name)

### Mode C: Feature-Specific Removal

- Keep structural tokens in morphology analysis
- Remove structural tokens only for semantic category counts

This allows:
- suffix mining unaffected
- semantic intensity more precise


---

## Implementation Specification

### Step 1: Load Stopword List

Stopwords must be stored in:
- `stopwords_v1.json`

Structure:

{
  "structural_tokens": ["村", "社", "队", ...],
  "admin_tokens": [...],
  "functional_tokens": [...]
}

Each version update:
- increment version
- log changes in README


---

### Step 2: Apply Filtering

Given:
- clean_name (string)
- char_set_raw (set of chars)

Produce:

- filtered_name
- char_set_filtered

Default logic (Mode B):
- filtered_chars = [c for c in clean_name if c not in structural_tokens]
- char_set_filtered = set(filtered_chars)


If filtered_name becomes empty:
- fallback to original clean_name (avoid losing signal entirely)


---

## Output Fields (Derived Table Extension)

If applied after Skill 01:

Extend `village_cleaned` with:

- filtered_name
- filtered_char_set_json
- removed_char_cnt
- stopword_mode
- stopword_version


---

## Diagnostic Reporting (Required)

Generate summary:

- total structural tokens removed
- frequency of each removed token
- % villages affected by removal
- top 20 tokens by removal count

Save:
- `results/<run_id>/stopword_report.txt`


---

## Important Constraints

- Stopword removal must NOT alter:
  - original raw_name
  - original clean_name
- Filtering must be reversible (since we retain original)
- All filtering decisions must be logged


---

## Non-Goals

- No clustering
- No tendency computation
- No semantic classification
- No database modification


---

## Acceptance Criteria

This skill is complete when:

1) Stopwords are version-controlled
2) Filtering modes are configurable
3) Derived fields are generated
4) Diagnostic report is produced
5) README updated (via readme_update_protocol)
