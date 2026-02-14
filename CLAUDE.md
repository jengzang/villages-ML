# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project is a sub-module of a larger system.  
It focuses specifically on statistical analysis and natural language processing (NLP) of natural village names in Guangdong Province.

The dataset contains **200,000+ natural villages** across Guangdong.

The purpose of this sub-project is to:

- Perform high-frequency character statistics on village names
- Conduct regional tendency analysis (e.g., city/county-level comparison)
- Explore semantic expansion (e.g., virtual term frequency)
- Apply clustering and pattern discovery on naming structures
- Introduce NLP and LLM-assisted analysis where appropriate
- Extend toward more advanced NLP-based structural and semantic analysis

This module is responsible only for data analysis and NLP-related computation.  
It does **not** implement or manage the full system architecture.

This is a machine learning project focused on village data from Guangdong Province, China. The repository contains geographic and administrative data about natural villages (自然村) in the region.

## Data Structure

The project uses a SQLite database located at `data/villages.db` containing a single table with the following schema:

**Table: 广东省自然村 (Guangdong Province Natural Villages)**

- 市级 (City level) - TEXT
- 县区级 (County/District level) - TEXT
- 乡镇 (Township) - TEXT
- 村委会 (Village Committee) - TEXT
- 自然村 (Natural Village name) - TEXT
- 拼音 (Pinyin romanization) - TEXT
- 语言分布 (Language distribution) - TEXT
- longitude - TEXT
- latitude - TEXT
- 备注 (Notes) - TEXT
- 更新时间 (Update time) - REAL
- 数据来源 (Data source) - TEXT

## Working with the Database

Access the database using Python's sqlite3 module:

```python
import sqlite3
conn = sqlite3.connect('data/villages.db')
cursor = conn.cursor()
```

Note: Column names and table names are in Chinese. When querying, use the exact Chinese characters or reference columns by index.

## Project Structure

```
villages-ML/
├── data/              # SQLite database and data files
├── src/               # Source code
├── notebooks/         # Jupyter notebooks for exploration
├── tests/             # Unit tests
└── .claude/skills/    # Custom Claude Code skills
```

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
source venv/bin/activate      # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/
```

### Jupyter Notebooks
```bash
# Start Jupyter
jupyter notebook
```

## Custom Skills

This repository includes custom skills in the `.claude/skills/` directory. Skills are reusable commands that can be invoked with `/skill-name` in Claude Code.

To use a skill, type `/skill-name` in the Claude Code CLI. Skills can accept parameters and provide specialized functionality for this project.


## Data Assumptions & Statistical Rules

- Dataset scale: 200,000+ natural villages (Guangdong Province)
- Basic counting unit: **village**
- Within each village name, characters must be deduplicated using `set()` before counting
- Only valid Chinese characters are considered for statistics
- All analysis is based on the natural village name field

Additional normalization, cleaning, or linguistic preprocessing rules may be introduced gradually.


---

## Project Scope

This module:

- Is implemented primarily using Python scripts
- Produces statistical and NLP analysis results
- Does not handle full backend/frontend architecture
- Does not require real-time online computation
- Does not manage deployment configuration

The goal is to ensure reproducible analytical workflows via Python.


---

## Technical Stack (Preferred)

### Core Data Processing
- Python 3.x
- Pandas
- NumPy

### NLP-Related Techniques
- Character-level statistical analysis
- Feature extraction from short text
- Virtual term frequency analysis
- Semantic expansion and category labeling
- Text embedding (offline usage)
- Clustering methods (e.g., KMeans, DBSCAN, HDBSCAN)
- Optional LLM API usage for semantic annotation and interpretation

### Machine Learning
- scikit-learn
- sentence-transformers (offline only)

Principle:

> Statistical rigor is the foundation. NLP and LLM techniques are enhancement layers.


---

## Computation Strategy

The project distinguishes between two phases:

### 1. Heavy Offline Computation (Allowed)

During preprocessing, experimentation, or model preparation stages:

- Large-scale data processing is allowed
- Embedding generation is allowed
- Clustering is allowed
- LLM-assisted semantic annotation is allowed
- Long-running computations are acceptable
- High resource consumption is acceptable

All heavy operations can be executed offline, locally, or on higher-performance machines.

Precomputed artifacts may include:

- Character frequency tables
- Regional tendency matrices
- Semantic label mappings
- Embedding vectors
- Cluster assignments
- Any derived analytical results

### 2. Lightweight Online Deployment (Required)

The final deployed system (running on 2-core, 2GB server) must:

- Avoid heavy model training
- Avoid large embedding computation
- Avoid clustering during runtime
- Only load precomputed results
- Perform lightweight querying and filtering

The deployed artifacts (models or derived results) must be small and efficient.


---

## Deployment Context

Target runtime environment:

- 2 CPU cores
- 2GB RAM
- Docker-based deployment

Containerization and deployment configuration are outside the scope of this module.

Only Python script execution and lightweight result serving are required.


---

## Performance Constraints

- No large-scale model training on the server
- No heavy real-time NLP inference
- All computationally expensive tasks must be completed offline
- Runtime environment must remain lightweight and stable
- Memory usage must fit within 2GB constraint

The system design must assume limited server resources and optimize accordingly.

# Trade-off Strategy (Strong Recommendation)

## Default: Offline-Heavy, Online-Light

### Offline (Allowed to be heavy and slow)
- full-table scans
- expensive aggregation
- embedding generation
- clustering
- LLM-assisted labeling (optional)
- building inverted indexes for top-N tokens
- writing derived tables back to DB

### Online (Must be cheap and bounded)
- indexed lookups
- filtering by region/tag/cluster_id
- pagination
- simple aggregations on precomputed tables
- NO full recomputation of embeddings/clustering
- NO unbounded scans

## How to Keep "Interactivity" Without Online Heavy Compute
Front-end “chooses parameters” by selecting:
- a region level (city/county/town)
- a feature view (semantic-index / tendency / suffix patterns / clusters)
- a tag filter (water-tag / mountain-tag / settlement-tag, etc.)
- a precomputed run_id version

Not by triggering recomputation.
