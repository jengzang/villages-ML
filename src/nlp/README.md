# NLP Module

Advanced semantic analysis tools for village name characters.

## Features

- **Character Embeddings**: Word2Vec-based distributional semantics
- **Similarity Queries**: Find semantically related characters
- **Semantic Arithmetic**: Vector operations (e.g., "山+水-石")
- **Analogy Solving**: Solve analogies (e.g., "东:西::南:?")
- **Clustering**: Discover semantic groups
- **Visualization**: Interactive t-SNE/UMAP plots

## Quick Start

### Train Embeddings

```bash
python scripts/train_char_embeddings.py \
  --run-id embed_001 \
  --db-path data/villages.db \
  --output-dir models/embeddings/
```

### Query Similar Characters

```bash
python scripts/analyze_embeddings.py \
  --run-id embed_001 \
  --query 田 \
  --top-k 20
```

### Visualize

```bash
python scripts/visualize_embeddings.py \
  --run-id embed_001 \
  --method tsne \
  --output results/tsne.html
```

## Modules

- `embedding_trainer.py` - Word2Vec training
- `embedding_storage.py` - Database persistence
- `embedding_analyzer.py` - Similarity and clustering
- `embedding_visualizer.py` - Interactive visualizations

## Documentation

See `docs/CHAR_EMBEDDINGS_GUIDE.md` for complete documentation.
