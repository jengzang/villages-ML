# Skill 09: Offline Village Embedding Generation

## Skill Name
embedding_generation_offline

## Purpose

Generate vector embeddings for village names (自然村) offline.

This skill enables:

- semantic similarity modeling beyond lexicon rules
- region-level semantic aggregation
- embedding-based clustering
- future LLM-compatible extensions

This skill is strictly offline.
It must NOT run on the 2-core / 2GB production server.

All heavy computation happens on:
- local workstation
- or higher-resource machine

Only final embedding artifacts are deployed.


---

# Part A: Input

Required:

- village_id
- clean_name (from Skill 01)
- optional region fields

Optional:

- filtered_name (if stopword mode applied)


---

# Part B: Embedding Strategy Options

The skill must support pluggable embedding models.

## B1. Default (Recommended Lightweight Chinese Model)

Example model types:
- sentence-transformers (Chinese pretrained)
- text2vec-base-chinese
- similar transformer-based embedding models

Embedding per village:

embedding(village) = model.encode(clean_name)

Output dimension:
- typically 384 / 512 / 768 depending on model


---

## B2. Alternative: Character-Level Aggregation (Ultra-Light Mode)

If transformer models are too heavy:

Option:
- Train Word2Vec on village corpus
- Represent village as mean of character embeddings

This avoids heavy transformer inference.

However:
- less semantic power
- suitable for experimental use only


---

# Part C: Processing Flow

Step 1:
Load cleaned village dataset.

Step 2:
Remove empty or invalid clean_name.

Step 3:
Batch encode names:
- batch_size configurable (default 64 or 128)
- disable gradient
- inference mode only

Step 4:
Store embeddings as:

Option A:
- NumPy array (.npz)
- village_id aligned

Option B:
- Parquet with vector column

Preferred:
- `.npz` for compactness
- plus CSV mapping for metadata


---

# Part D: Output Artifacts

Directory:
`results/<run_id>/embeddings/`

Files:

- village_embeddings.npy (or .npz)
- village_ids.csv
- embedding_metadata.json

Metadata must include:

- model_name
- model_version
- embedding_dimension
- batch_size
- device (cpu/gpu)
- date
- run_id


---

# Part E: Region-Level Aggregation (Optional)

If region clustering is desired:

Compute:

For region g:

μ_g =
  mean(embedding_i for villages in region g)

Store:

- region_embeddings.npy
- region_ids.csv

These will feed into clustering skill.


---

# Part F: Memory & Performance Constraints

For 200k villages:

If embedding_dim = 384:
- memory ≈ 200k × 384 × 4 bytes ≈ 307MB

If 768 dim:
- ≈ 600MB

Recommendation:
- Use 384-dim model for safety.

Do NOT attempt embedding generation on 2GB server.


---

# Part G: Reproducibility Requirements

- fixed random seeds if any
- no shuffling affecting order
- deterministic encoding order
- mapping village_id to embedding index must be exact

All parameters must be logged.


---

# Acceptance Criteria

1) All villages have embedding vectors
2) Output artifacts saved
3) Metadata recorded
4) No server-side inference required
