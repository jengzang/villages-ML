# New API Endpoints Quick Reference

**Date**: 2026-02-20
**Total New Endpoints**: 11

---

## Spatial Analysis (4 endpoints)

### 1. Get Hotspots
```
GET /api/spatial/hotspots
```
**Parameters**:
- `run_id` (default: "spatial_001")
- `min_density` (optional)
- `min_village_count` (optional)

**Example**:
```bash
curl "http://localhost:8000/api/spatial/hotspots?min_density=0.5"
```

### 2. Get Hotspot Detail
```
GET /api/spatial/hotspots/{hotspot_id}
```

### 3. Get Spatial Clusters
```
GET /api/spatial/clusters
```
**Parameters**:
- `run_id`, `cluster_id`, `min_size`, `limit`

### 4. Get Cluster Summary
```
GET /api/spatial/clusters/summary
```

---

## N-gram Analysis (3 endpoints)

### 5. Get N-gram Frequency
```
GET /api/ngrams/frequency
```
**Parameters**:
- `n` (required: 2-4)
- `top_k` (default: 100)
- `min_frequency` (optional)

**Example**:
```bash
curl "http://localhost:8000/api/ngrams/frequency?n=2&top_k=20"
```

### 6. Get Regional N-grams
```
GET /api/ngrams/regional
```
**Parameters**:
- `n`, `region_level`, `region_name`, `top_k`

### 7. Get Structural Patterns
```
GET /api/ngrams/patterns
```

---

## Character Embeddings (3 endpoints)

### 8. Get Embedding Vector
```
GET /api/character/embeddings/vector
```
**Parameters**:
- `char` (required)
- `run_id` (default: "embed_001")

**Example**:
```bash
curl "http://localhost:8000/api/character/embeddings/vector?char=村"
```

### 9. Get Similar Characters
```
GET /api/character/embeddings/similarities
```
**Parameters**:
- `char`, `top_k`, `min_similarity`

### 10. List Embeddings
```
GET /api/character/embeddings/list
```

---

## Semantic Labels (3 endpoints)

### 11. Get Label by Character
```
GET /api/semantic/labels/by-character
```
**Parameters**:
- `char` (required)

### 12. Get Characters by Category
```
GET /api/semantic/labels/by-category
```
**Parameters**:
- `category` (required)
- `min_confidence` (optional)

### 13. List Categories
```
GET /api/semantic/labels/categories
```

---

## Character Significance (3 endpoints)

### 14. Get Significance by Character
```
GET /api/character/significance/by-character
```
**Parameters**:
- `char`, `region_level`, `min_zscore`

### 15. Get Significant Characters by Region
```
GET /api/character/significance/by-region
```
**Parameters**:
- `region_name`, `region_level`, `significance_only`, `top_k`

### 16. Get Significance Summary
```
GET /api/character/significance/summary
```

---

## Common Parameters

- `run_id`: Analysis run identifier (varies by module)
- `region_level`: "city", "county", or "township"
- `region_name`: Specific region name (e.g., "广州市")
- `top_k` / `limit`: Number of results to return
- `min_*`: Minimum threshold filters

---

## Response Format

All endpoints return JSON:
- Success: List of objects or single object
- Error: `{"detail": "error message"}`

---

## Interactive Documentation

Visit http://localhost:8000/docs for full API documentation with try-it-out functionality.