# Scripts Directory Structure

This directory contains all analysis and utility scripts organized by function.

## Subdirectories

### core/
Active pipeline scripts for main analysis phases:
- Frequency analysis
- Morphology analysis
- Semantic analysis
- Clustering analysis
- Spatial analysis
- Character embeddings
- N-gram analysis
- Semantic composition

### preprocessing/
Data preprocessing and validation scripts:
- Create preprocessed table
- Backup analysis tables
- Audit logging and reporting
- Validation scripts

### analysis/
Analysis utilities and tools:
- LLM character labeling
- Embedding analysis
- Semantic co-occurrence
- Semantic network analysis
- Lexicon coverage
- Cluster analysis

### visualization/
Visualization and mapping scripts:
- Cluster visualization
- Embedding visualization
- Semantic network visualization
- Spatial maps generation

### reporting/
Report generation scripts:
- Comprehensive report generator
- Analysis results extraction
- Chinese showcase creation

### query/
Query utilities for database:
- Query results
- Query tendency
- Query spatial tendency

### utils/
General utilities:
- Database verification
- Feature materialization
- Export results
- Compare runs
- Initialize tables

### experimental/
Experimental and alternative approaches:
- Village-level clustering (KMeans, DBSCAN, GMM)
- Hierarchical clustering
- Spatial tendency integration

## Usage

Run scripts from the project root directory:

```bash
# Core pipeline
python scripts/core/run_frequency_analysis.py

# Preprocessing
python scripts/preprocessing/create_preprocessed_table.py

# Analysis
python scripts/analysis/llm_label_characters.py

# Reporting
python scripts/reporting/generate_comprehensive_report.py
```
