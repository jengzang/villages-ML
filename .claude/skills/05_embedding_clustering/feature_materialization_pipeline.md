# Skill 15: Feature Materialization Pipeline (Phase 10)

## Skill Name
feature_materialization_pipeline

## Purpose
Materialize all computed features for villages into a single denormalized database table.
Combines character frequency, semantic indices, morphological patterns, spatial features, and cluster assignments.
Strictly offline computation. Enables fast online queries without joins or aggregations.

---

# Part A: Feature Categories

**1️⃣ Character Features**
- High-frequency characters present (top 100)
- Character diversity score (unique chars / total chars)
- Rare character count (frequency < 0.001)
- Character category distribution (water, mountain, direction)

**2️⃣ Semantic Features**
- Water index (0-1): 水, 河, 江, 湖, 海, 溪, 涌
- Mountain index (0-1): 山, 岭, 峰, 坡, 岗, 岩
- Settlement index (0-1): 村, 庄, 寨, 围, 堡, 屋
- Direction index (0-1): 东, 南, 西, 北, 上, 下, 前, 后

**3️⃣ Morphological Features**
- Prefix pattern (first 1-2 characters)
- Suffix pattern (last 1-2 characters)
- Name length (character count)
- Structure type (prefix+core+suffix classification)

**4️⃣ Spatial Features**
- Nearest neighbor distances (1st, 5th, 10th)
- Local density (1km, 5km, 10km radius)
- Isolation score (distance to nearest cluster)
- Spatial cluster assignment

**5️⃣ Cluster Features**
- Semantic cluster ID (from KMeans/GMM)
- Spatial cluster ID (from DBSCAN)
- Cluster confidence score
- Cluster centroid distance

---

# Part B: Output Schema

**Table:** `village_features_materialized`

**Primary Key:**
- `village_id` (INTEGER) - Unique identifier

**Basic Info:**
- `village_name` (TEXT) - Natural village name
- `city` (TEXT) - City level (市级)
- `county` (TEXT) - County level (县区级)
- `township` (TEXT) - Township (乡镇)

**Character Features:**
- `char_diversity_score` (REAL) - 0-1 scale
- `rare_char_count` (INTEGER)
- `name_length` (INTEGER)

**Semantic Indices:**
- `water_index` (REAL) - 0-1 scale
- `mountain_index` (REAL) - 0-1 scale
- `settlement_index` (REAL) - 0-1 scale
- `direction_index` (REAL) - 0-1 scale

**Morphological Patterns:**
- `prefix_pattern` (TEXT) - e.g., "大", "新", "上"
- `suffix_pattern` (TEXT) - e.g., "村", "庄", "围"
- `structure_type` (TEXT) - e.g., "prefix+core+suffix"

**Spatial Features:**
- `nn_distance_1` (REAL) - Distance to nearest neighbor (km)
- `nn_distance_5` (REAL) - Distance to 5th nearest neighbor (km)
- `local_density_1km` (INTEGER) - Villages within 1km
- `local_density_5km` (INTEGER) - Villages within 5km
- `isolation_score` (REAL) - Normalized isolation metric

**Cluster Assignments:**
- `semantic_cluster_id` (INTEGER) - From KMeans/GMM
- `spatial_cluster_id` (INTEGER) - From DBSCAN (-1 if noise)
- `cluster_confidence` (REAL) - 0-1 scale

**Metadata:**
- `run_id` (TEXT) - Reproducibility tracking
- `created_at` (REAL) - Unix timestamp

---

# Part C: Implementation Strategy

**Step-by-Step Process:**

1. **Load Base Village Data**
   - Read from `广东省自然村` table
   - Extract village_id, name, administrative divisions

2. **Join Character Frequency Results**
   - Load from `character_frequency` table
   - Compute diversity score
   - Count rare characters

3. **Join Semantic Indices**
   - Load from `semantic_indices` table
   - Normalize to 0-1 scale
   - Handle missing values (default: 0)

4. **Join Morphological Patterns**
   - Load from `morphological_patterns` table
   - Extract prefix/suffix patterns
   - Classify structure types

5. **Join Spatial Features**
   - Load from `village_spatial_features` table
   - Compute nearest neighbor distances
   - Calculate local density metrics

6. **Join Cluster Assignments**
   - Load from `semantic_clusters` table
   - Load from `spatial_clusters` table
   - Merge cluster IDs

7. **Write to Materialized Table**
   - Create single denormalized table
   - Add indexes for fast queries
   - Validate data completeness

---

# Part D: Performance Characteristics

**Computation Time:**
- Full dataset (285k villages): ~2-5 minutes
- Regional subset (50k villages): ~30-60 seconds

**Memory Usage:**
- Peak memory: ~1-2 GB
- Intermediate joins: ~500 MB per join

**Output Table Size:**
- Row count: 285k+ villages
- Disk size: ~50-100 MB (uncompressed)
- Indexed size: ~150-200 MB

**Deployment Constraint:**
- ⚠️ **Offline only** - Never run on 2-core/2GB server
- Precompute features and save to database
- Online queries only read precomputed table

---

# Part E: Online Query Strategy

**Before Materialization (Slow):**
```sql
-- Multiple joins, aggregations, heavy computation
SELECT v.自然村,
       COUNT(DISTINCT cf.character) as diversity,
       AVG(si.water_index) as water_score,
       MIN(sf.nn_distance_1) as isolation
FROM 广东省自然村 v
LEFT JOIN character_frequency cf ON v.id = cf.village_id
LEFT JOIN semantic_indices si ON v.id = si.village_id
LEFT JOIN village_spatial_features sf ON v.id = sf.village_id
WHERE v.县区级 = '广州市'
GROUP BY v.id
LIMIT 100;
```

**After Materialization (Fast):**
```sql
-- Single table, indexed lookup, no joins
SELECT village_name, char_diversity_score, water_index, nn_distance_1
FROM village_features_materialized
WHERE county = '广州市'
  AND water_index > 0.5
  AND spatial_cluster_id = 42
LIMIT 100;
```

**Query Performance:**
- Before: 5-10 seconds (multiple joins)
- After: <100ms (indexed single table)

---

# Part F: Indexing Strategy

**Primary Index:**
- `village_id` (PRIMARY KEY)

**Secondary Indexes:**
- `(city, county)` - Regional filtering
- `(semantic_cluster_id)` - Cluster queries
- `(spatial_cluster_id)` - Spatial cluster queries
- `(water_index, mountain_index)` - Semantic filtering

**Composite Indexes:**
- `(county, water_index, spatial_cluster_id)` - Common query pattern

**Index Creation:**
```sql
CREATE INDEX idx_region ON village_features_materialized(city, county);
CREATE INDEX idx_semantic_cluster ON village_features_materialized(semantic_cluster_id);
CREATE INDEX idx_spatial_cluster ON village_features_materialized(spatial_cluster_id);
CREATE INDEX idx_water ON village_features_materialized(water_index);
```

---

# Part G: CLI Usage

**Script:** `scripts/materialize_features.py`

**Basic Usage:**
```bash
python scripts/materialize_features.py \
  --run-id features_v1 \
  --include-spatial \
  --include-semantic \
  --include-clusters
```

**Advanced Options:**
```bash
python scripts/materialize_features.py \
  --run-id features_v2 \
  --include-all \
  --region-filter "广州市" \
  --output-table village_features_guangzhou \
  --create-indexes
```

**Parameter Flags:**
- `--run-id` - Unique identifier for this materialization
- `--include-spatial` - Include spatial features
- `--include-semantic` - Include semantic indices
- `--include-clusters` - Include cluster assignments
- `--include-all` - Include all feature categories
- `--region-filter` - Optional city/county filter
- `--output-table` - Custom table name (default: village_features_materialized)
- `--create-indexes` - Automatically create indexes

---

# Part H: Data Quality Checks

**Before Materialization:**
1. Verify all source tables exist
2. Check for missing run_ids
3. Validate coordinate data completeness
4. Confirm cluster assignments computed

**After Materialization:**
1. Check row count matches source table
2. Verify no null values in critical columns
3. Validate index creation
4. Test query performance (<100ms)

**Expected Results:**
- 285k+ rows materialized
- <5% missing values in optional features
- All indexes created successfully
- Query performance <100ms for typical queries

---

# Part I: Deployment Integration

**Offline Workflow:**
1. Run all feature extraction pipelines
2. Run clustering algorithms
3. Materialize features into single table
4. Create indexes
5. Export table to production database

**Online Workflow:**
1. Load materialized table (read-only)
2. Execute indexed queries
3. Return results (no computation)
4. No joins, no aggregations, no heavy operations

**Resource Usage (Online):**
- Memory: <200 MB (table loaded in memory)
- CPU: Minimal (indexed lookups only)
- Disk: ~150 MB (table + indexes)

---

# Acceptance Criteria

1. ✅ All feature categories materialized into single table
2. ✅ Single denormalized table created (no joins required)
3. ✅ Indexes created for fast queries (<100ms)
4. ✅ Run ID tracked for reproducibility
5. ✅ No online heavy computation required
6. ✅ Data quality checks passed (completeness, validity)
7. ✅ Query performance validated (<100ms for typical queries)