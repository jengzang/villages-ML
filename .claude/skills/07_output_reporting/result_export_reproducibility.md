# Skill 13: Result Export & Reproducibility Pack

## Skill Name
result_export_repro_pack

## Purpose

Ensure that every analytical run is:

- reproducible
- traceable
- parameter-documented
- auditable

This skill standardizes output structure.


---

# Part A: Directory Structure

All outputs must be under:

results/<run_id>/

Where run_id:
- timestamp or hash
- unique per run


---

# Part B: Required Files Per Run

- config_snapshot.json
- region_vectors.csv (if generated)
- char_frequency.csv (if generated)
- regional_tendency.csv (if generated)
- clustering outputs
- embedding metadata (if used)
- cleaning report
- stopword report
- tendency report


---

# Part C: config_snapshot.json

Must include:

- region_level
- thresholds
- smoothing alpha
- stopword_mode
- lexicon_version
- model_name (if embedding)
- clustering parameters
- date
- run_id


---

# Part D: Determinism Requirements

- fixed random_state
- fixed PCA parameters
- fixed smoothing constant
- consistent vocabulary selection


---

# Part E: README Update

Via readme_update_protocol:

Append:

- Run date
- Summary of outputs
- Parameter snapshot summary
- Observations (optional)


---

# Acceptance Criteria

1) Every run produces structured directory
2) Parameters snapshot saved
3) All outputs grouped
4) No undocumented runs allowed
