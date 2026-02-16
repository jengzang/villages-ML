# Skills Directory

This directory contains custom skills for Claude Code organized by functional category.

Skills are reusable commands that provide specialized guidance for working with the Guangdong villages NLP/ML analysis project.

## Directory Structure

```
.claude/skills/
├── README.md (this file)
├── 01_workflow/              # Project workflow and documentation protocols
├── 02_preprocessing/         # Data cleaning and normalization
├── 03_statistical_analysis/  # Character frequency and regional analysis
├── 04_semantic_analysis/     # Semantic indexing and NLP methods
├── 05_embedding_clustering/  # Vector embeddings and clustering
├── 06_deployment/            # Offline/online deployment strategies
├── 07_output_reporting/      # Result export and metrics
└── 08_spatial_analysis/      # Geographic clustering and visualization
```

## Skill Categories

### 01_workflow/ - Project Workflow
Core protocols for maintaining code quality and documentation:
- `readme_update_protocol.md` - Rules for updating README.md
- `code_commit_protocol.md` - Git commit guidelines
- `db_backup_safe_edit_workflow.md` - Database backup requirements

### 02_preprocessing/ - Data Preprocessing
Text cleaning and normalization for village names:
- `text_normalization.md` - Character normalization rules
- `stopwords_filtering.md` - Stopword removal strategies
- `numbered_village_normalization.md` - Handle numbered village names
- `administrative_prefix_cleaning.md` - Remove administrative prefixes

### 03_statistical_analysis/ - Statistical Analysis
Character-level and regional statistical methods:
- `char_frequency_engine.md` - Character frequency computation
- `regional_tendency_engine.md` - Regional pattern analysis
- `toponym_morphology_mining.md` - Morphological structure mining

### 04_semantic_analysis/ - Semantic Analysis
NLP-based semantic indexing and categorization:
- `semantic_lexicon_builder.md` - Build semantic category lexicons
- `toponym_semantic_index.md` - Create semantic indices for toponyms
- `regional_semantic_contrast.md` - Compare semantic patterns by region
- `llm_semantic_labeling.md` - LLM-assisted semantic annotation

### 05_embedding_clustering/ - Embedding & Clustering
Vector representations and clustering methods:
- `village_embedding_generation.md` - Generate village name embeddings
- `semantic_vectorization.md` - Semantic feature vectorization
- `region_feature_schema.md` - Regional feature engineering
- `clustering_pipeline.md` - Clustering workflow and methods
- `cluster_interpretation.md` - Interpret and label clusters
- `feature_materialization_pipeline.md` - Materialize all features for fast queries

### 06_deployment/ - Deployment Strategy
Offline computation and online serving guidelines:
- `offline_feature_tagging.md` - Precompute features offline
- `online_serving_policy.md` - Lightweight online query strategies
- `query_safety_validator.md` - Validate query safety and resource consumption

### 07_output_reporting/ - Output & Reporting
Result export and spatial analysis:
- `result_export_reproducibility.md` - Reproducible result export
- `spatial_hotspot_metrics.md` - Spatial pattern metrics
- `comparison_report_generator.md` - Generate clustering comparison reports

### 08_spatial_analysis/ - Spatial Analysis (Phase 13)
Geographic clustering and interactive visualization:
- `spatial_clustering_pipeline.md` - Run spatial DBSCAN clustering
- `interactive_map_generator.md` - Generate folium maps
- `spatial_feature_extractor.md` - Extract spatial features (NN distance, density, isolation)
- `spatial_semantic_integration.md` - Integrate spatial clustering with semantic analysis

## Usage

Skills are invoked using the `/skill-name` command in Claude Code CLI. However, since skills are now organized in subdirectories, you may need to reference them by their filename without the `.md` extension.

## Design Philosophy

Skills are organized by the natural workflow of the analysis pipeline:
1. **Workflow** - Establish development protocols
2. **Preprocessing** - Clean and normalize data
3. **Statistical Analysis** - Basic frequency and pattern analysis
4. **Semantic Analysis** - NLP-based semantic methods
5. **Embedding & Clustering** - Advanced ML techniques
6. **Deployment** - Production deployment strategies
7. **Output & Reporting** - Results and visualization
8. **Spatial Analysis** - Geographic clustering and interactive maps

This structure reflects the "offline-heavy, online-light" principle where expensive computations are done offline and lightweight queries are served online.

## Adding New Skills

When creating new skills:
1. Place them in the appropriate category directory
2. Use descriptive filenames (e.g., `feature_name.md`)
3. Follow the existing skill format with clear purpose and trigger conditions
4. Update this README with the new skill entry
