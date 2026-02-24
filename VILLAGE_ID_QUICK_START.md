# Village ID Implementation - Quick Reference

## Quick Start (Copy-Paste Commands)

```bash
# Step 1: Regenerate preprocessed table (10-15 min)
python scripts/preprocessing/create_preprocessed_table.py

# Step 2: Add village_id to main table (5 min)
python scripts/preprocessing/add_village_id_to_main_table.py

# Step 3: Regenerate village_ngrams (15-20 min)
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_ngrams;"
python -c "from src.ngram_schema import create_ngram_tables; create_ngram_tables()"
python scripts/core/populate_village_ngrams.py

# Step 4: Regenerate village_semantic_structure (30-45 min)
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_semantic_structure;"
python -c "from src.semantic_composition_schema import create_semantic_composition_tables; create_semantic_composition_tables()"
python scripts/core/phase14_semantic_composition.py

# Step 5: Regenerate village_features (60-90 min)
sqlite3 data/villages.db "DROP TABLE IF EXISTS village_features;"
python scripts/core/run_clustering_analysis.py

# Step 6: Verify (1 min)
python scripts/verification/verify_village_id.py

# Step 7: Benchmark (2-3 min)
python scripts/verification/benchmark_village_id.py

# Step 8: Test API (5 min)
python -m uvicorn api.main:app --reload
# In another terminal:
curl http://localhost:8000/village/ngrams/1
curl http://localhost:8000/village/semantic-structure/1
curl http://localhost:8000/village/features/1
curl http://localhost:8000/village/complete/1
```

## Total Time: 2-3 hours

## Files Changed

### Modified (7 files)
- scripts/preprocessing/create_preprocessed_table.py
- src/ngram_schema.py
- scripts/core/populate_village_ngrams.py
- src/semantic_composition_schema.py
- scripts/core/phase14_semantic_composition.py
- src/pipelines/feature_materialization_pipeline.py
- api/village/data.py

### Created (4 files)
- scripts/preprocessing/add_village_id_to_main_table.py
- scripts/verification/verify_village_id.py
- scripts/verification/benchmark_village_id.py
- docs/guides/VILLAGE_ID_IMPLEMENTATION_GUIDE.md

## Key Changes

- **ID Format**: `'v_' || ROWID` (e.g., v_1, v_2, v_285860)
- **Source**: Preprocessed table ROWID (single source of truth)
- **Tables**: 6 tables now have village_id
- **API**: Simplified from 2-step to 1-step queries
- **Performance**: Expected 50-80% improvement

## Verification Checklist

- [ ] All 6 tables have village_id column
- [ ] village_id format is correct (v_<ROWID>)
- [ ] village_id is unique
- [ ] Coverage >99%
- [ ] Indexes exist
- [ ] API works
- [ ] Performance improved

## Rollback

```bash
# Restore from backup if needed
sqlite3 data/villages.db ".restore data/villages_backup.db"
```

## Documentation

- Full guide: `docs/guides/VILLAGE_ID_IMPLEMENTATION_GUIDE.md`
- Summary: `docs/guides/VILLAGE_ID_IMPLEMENTATION_SUMMARY.md`
- This file: Quick reference for execution
