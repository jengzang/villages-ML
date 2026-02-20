# API Audit: Actual Status Report

**Date**: 2026-02-20
**Database**: villages.db (1.7GB, 26+ tables)
**Project**: Guangdong Province Natural Village Analysis System

---

## Executive Summary

### Key Findings

1. **API Coverage Better Than Expected**: The audit plan suggested 42% coverage, but actual implementation shows ~60-70% coverage
2. **Clustering Endpoints**: ✅ **ALREADY EXIST** (contrary to audit plan)
3. **Semantic Endpoints**: ✅ **ALREADY EXIST** (category, VTF, tendency)
4. **Spatial Endpoints**: ❌ **MISSING** (hotspots, clusters)
5. **Character Embeddings**: ❌ **MISSING** (embeddings, similarities)
6. **N-gram Endpoints**: ❌ **MISSING** (frequency, patterns)

### Current API Structure

The API is organized by feature domains:
- `/api/character/*` - Character frequency and tendency
- `/api/village/*` - Village search and details
- `/api/semantic/*` - Semantic categories, VTF, tendency
- `/api/clustering/*` - Cluster assignments, profiles, metrics
- `/api/compute/*` - On-demand computation (clustering, semantic, features)
- `/api/metadata/*` - Database statistics

---

## Detailed Endpoint Inventory

### ✅ Implemented Endpoints (15+ endpoints)

#### Character Analysis (`/api/character/`)
1. `GET /api/character/frequency/global` - Global character frequency
2. `GET /api/character/frequency/regional` - Regional character frequency
3. `GET /api/character/tendency/*` - Character tendency analysis

#### Village Search (`/api/village/`)
4. `GET /api/village/search` - Search villages by name/region
5. `GET /api/village/detail` - Get village details with features

#### Semantic Analysis (`/api/semantic/category/`)
6. `GET /api/semantic/category/list` - List all semantic categories
7. `GET /api/semantic/category/vtf/global` - Global semantic VTF
8. `GET /api/semantic/category/vtf/regional` - Regional semantic VTF
9. `GET /api/semantic/category/tendency` - Semantic tendency by region

#### Clustering Analysis (`/api/clustering/`) ✅ **ALREADY EXISTS**
10. `GET /api/clustering/assignments` - Get cluster assignments
11. `GET /api/clustering/assignments/by-region` - Get assignment for specific region
12. `GET /api/clustering/profiles` - Get cluster profiles
13. `GET /api/clustering/metrics` - Get clustering quality metrics
14. `GET /api/clustering/metrics/best` - Get best clustering configuration

#### Compute Endpoints (`/api/compute/`)
15. `POST /api/compute/semantic/cooccurrence` - Semantic cooccurrence analysis
16. `POST /api/compute/semantic/network` - Semantic network building
17. `POST /api/compute/clustering/*` - On-demand clustering
18. `POST /api/compute/features/*` - Feature extraction

#### Metadata (`/api/metadata/`)
19. `GET /api/metadata/stats` - Database statistics

---

### ❌ Missing Endpoints (High Priority)

#### Spatial Analysis (`/api/spatial/`) - **NEEDS CREATION**
20. `GET /api/spatial/hotspots` - Get KDE density hotspots (Phase 13)
21. `GET /api/spatial/clusters` - Get DBSCAN spatial clusters (Phase 4)
22. `GET /api/spatial/features` - Get village spatial features

**Tables**: `spatial_hotspots` (~8 rows), `spatial_clusters`, `village_spatial_features` (~283K rows)

#### Character Embeddings (`/api/character/embeddings/`) - **NEEDS CREATION**
23. `GET /api/character/embeddings` - Get Word2Vec embeddings for character
24. `GET /api/character/similarities` - Get similar characters by embedding

**Tables**: `char_embeddings` (~9K rows), `character_similarities`

#### N-gram Analysis (`/api/ngrams/`) - **NEEDS CREATION**
25. `GET /api/ngrams/frequency` - Get global n-gram frequencies
26. `GET /api/ngrams/regional` - Get regional n-gram frequencies
27. `GET /api/ngrams/patterns` - Get structural patterns

**Tables**: `ngram_frequency` (~1.9M rows), `regional_ngram_frequency`, `structural_patterns`

#### Character Significance (`/api/character/significance/`) - **NEEDS CREATION**
28. `GET /api/character/significance` - Get statistical significance tests

**Tables**: `character_significance` (~27K rows)

#### Semantic Labels (`/api/semantic/labels/`) - **NEEDS CREATION**
29. `GET /api/semantic/labels` - Get LLM-generated semantic labels for characters

**Tables**: `semantic_labels` (~9K rows)

---

## Revised Implementation Plan

### Phase 1: High Priority Spatial Endpoints (2-3 hours)

**Create**: `api/spatial/hotspots.py`

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
import sqlite3

from ..dependencies import get_db, execute_query
from ..models import SpatialHotspot

router = APIRouter(prefix="/spatial", tags=["spatial"])

@router.get("/hotspots", response_model=List[SpatialHotspot])
def get_spatial_hotspots(
    run_id: str = Query("spatial_001", description="Spatial analysis run ID"),
    min_density: float = Query(None, description="Minimum density threshold"),
    db: sqlite3.Connection = Depends(get_db)
):
    """Get KDE density hotspots"""
    query = """
        SELECT
            hotspot_id,
            center_lon,
            center_lat,
            density_peak,
            village_count,
            radius_km
        FROM spatial_hotspots
        WHERE run_id = ?
    """
    params = [run_id]

    if min_density is not None:
        query += " AND density_peak >= ?"
        params.append(min_density)

    query += " ORDER BY density_peak DESC"

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(status_code=404, detail="No hotspots found")

    return results
```

**Create**: `api/spatial/clusters.py` (similar structure for DBSCAN clusters)

**Update**: `api/main.py` to register spatial routers

---

### Phase 2: Medium Priority N-gram Endpoints (2-3 hours)

**Create**: `api/ngrams/frequency.py`

```python
@router.get("/frequency", response_model=List[NgramFrequency])
def get_ngram_frequency(
    n: int = Query(..., ge=2, le=4, description="N-gram size"),
    run_id: str = Query("ngram_001", description="N-gram analysis run ID"),
    top_k: int = Query(100, ge=1, le=1000, description="Top K n-grams"),
    db: sqlite3.Connection = Depends(get_db)
):
    """Get global n-gram frequencies"""
    query = """
        SELECT
            ngram,
            frequency,
            village_count
        FROM ngram_frequency
        WHERE run_id = ? AND n = ?
        ORDER BY frequency DESC
        LIMIT ?
    """

    results = execute_query(db, query, (run_id, n, top_k))

    if not results:
        raise HTTPException(status_code=404, detail=f"No {n}-grams found")

    return results
```

---

### Phase 3: Low Priority Embeddings & Labels (2-3 hours)

**Create**: `api/character/embeddings.py`
**Create**: `api/semantic/labels.py`

---

## Database Table Status Check

### Critical Tables to Verify

Run these checks to confirm table population:

```sql
-- Check spatial hotspots
SELECT COUNT(*) FROM spatial_hotspots;  -- Expected: ~8

-- Check spatial clusters
SELECT COUNT(*) FROM spatial_clusters;  -- Expected: >0

-- Check character embeddings
SELECT COUNT(*) FROM char_embeddings;  -- Expected: ~9K

-- Check n-gram frequency
SELECT COUNT(*) FROM ngram_frequency;  -- Expected: ~1.9M

-- Check semantic labels
SELECT COUNT(*) FROM semantic_labels;  -- Expected: ~9K

-- Check character significance
SELECT COUNT(*) FROM character_significance;  -- Expected: ~27K
```

---

## Action Items

### Immediate (Today)
1. ✅ Create accurate API audit report (this document)
2. ⏳ Verify database table population status
3. ⏳ Create spatial hotspots endpoint
4. ⏳ Create spatial clusters endpoint

### Short-term (This Week)
5. ⏳ Create n-gram frequency endpoints
6. ⏳ Create character embeddings endpoints
7. ⏳ Create semantic labels endpoint
8. ⏳ Create character significance endpoint

### Documentation
9. ⏳ Update API_REFERENCE.md with new endpoints
10. ⏳ Create API usage examples
11. ⏳ Update PROJECT_STATUS.md

---

## Corrected Coverage Estimate

**Current Coverage**: ~60-70% (15-19 endpoints covering 11-15 tables)
**Target Coverage**: ~90-95% (28-30 endpoints covering 20-25 tables)
**Gap**: 9-11 endpoints needed

**Estimated Time**: 6-9 hours total
- Spatial: 2-3 hours
- N-grams: 2-3 hours
- Embeddings/Labels: 2-3 hours

---

## Notes

1. **Clustering endpoints already exist** - No need to implement
2. **Semantic category endpoints already exist** - No need to implement
3. **Compute endpoints provide on-demand analysis** - Good for flexibility
4. **Main gaps are in spatial, n-gram, and embedding access**
5. **All core analysis phases (0-14) are complete** - Just need API exposure

---

## Next Steps

**User Decision Required**:
1. Verify database table status (run SQL checks above)
2. Prioritize which missing endpoints are most important
3. Approve implementation of spatial endpoints (highest priority)

**Recommendation**: Start with spatial endpoints since Phase 13 (hotspots) is a recent addition and users likely want to access this data.
