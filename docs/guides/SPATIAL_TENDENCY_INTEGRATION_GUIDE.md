# Spatial-Tendency Integration Guide

## Overview

The Spatial-Tendency Integration feature combines regional tendency analysis with spatial clustering to identify **geographic patterns in village naming preferences**. This allows you to answer questions like:

- Where are villages with "田" (field) names geographically concentrated?
- Do naming patterns form spatially coherent regions?
- Which geographic clusters show significant over/under-representation of specific characters?
- How do naming preferences vary across the geographic landscape of Guangdong?

## Key Concepts

### What is Spatial-Tendency Integration?

**Tendency Analysis** identifies which characters are preferred or avoided in specific administrative regions (cities, counties, townships).

**Spatial Clustering** groups villages based on geographic proximity, independent of administrative boundaries.

**Integration** combines these two analyses to:
1. Map character preferences onto geographic clusters
2. Calculate cluster-level tendency statistics
3. Identify spatially coherent naming regions
4. Visualize geographic distribution of naming patterns

### Why is this useful?

- **Geographic Patterns**: Discover natural geographic boundaries of naming traditions
- **Cross-boundary Analysis**: Identify naming patterns that transcend administrative divisions
- **Spatial Coherence**: Measure how tightly naming patterns are geographically clustered
- **Visualization**: Generate maps showing where specific naming preferences occur

## Prerequisites

Before using spatial-tendency integration, you must have:

1. **Completed Tendency Analysis** (Phase 1)
   - Run ID from tendency analysis with significance testing
   - Example: `test_sig_1771260439`

2. **Completed Spatial Analysis** (Phase 13)
   - Run ID from spatial clustering analysis
   - Example: `spatial_001`

3. **Database Tables Initialized**
   - Run `scripts/init_spatial_tendency_tables.py` to create tables

## Quick Start

### Step 1: Initialize Database Tables

```bash
python scripts/init_spatial_tendency_tables.py
```

This creates the `spatial_tendency_integration` table and indexes.

### Step 2: Run Integration Analysis

**Single Character:**
```bash
python scripts/spatial_tendency_integration.py \
  --char 田 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_001
```

**Multiple Characters:**
```bash
python scripts/spatial_tendency_integration.py \
  --chars 田,水,山,村,新 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_002
```

### Step 3: Query Results

**View Summary:**
```bash
python scripts/query_spatial_tendency.py --run-id integration_001
```

**Filter by Character:**
```bash
python scripts/query_spatial_tendency.py --run-id integration_001 --char 田
```

**Significant Results Only:**
```bash
python scripts/query_spatial_tendency.py \
  --run-id integration_001 \
  --significant-only \
  --top-n 20
```

### Step 4: Generate Map

```bash
python scripts/spatial_tendency_integration.py \
  --char 田 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_003 \
  --generate-map \
  --output-map results/spatial_tendency_田.html
```

Open `results/spatial_tendency_田.html` in a web browser to view the interactive map.

## Detailed Usage

### Integration Script Parameters

**Required:**
- `--tendency-run-id`: Run ID from tendency analysis
- `--spatial-run-id`: Run ID from spatial clustering
- `--output-run-id`: Unique ID for this integration run

**Character Selection (one required):**
- `--char`: Single character to analyze (e.g., `--char 田`)
- `--chars`: Comma-separated list (e.g., `--chars 田,水,山`)

**Optional:**
- `--region-level`: Region level for tendency data (`city`, `county`, `township`). Default: `county`
- `--db-path`: Database path. Default: `data/villages.db`
- `--generate-map`: Generate interactive HTML map
- `--output-map`: Output path for map file

### Query Script Parameters

**Required:**
- `--run-id`: Integration run ID to query

**Filters:**
- `--char`: Filter by specific character
- `--significant-only`: Only show statistically significant results
- `--city`: Filter by city name
- `--county`: Filter by county name
- `--min-cluster-size`: Minimum cluster size threshold
- `--top-n`: Return top N clusters by character density

**Output:**
- `--output`: Export results to CSV file
- `--no-summary`: Skip summary statistics (show only detailed results)

## Understanding the Results

### Output Columns

| Column | Description |
|--------|-------------|
| `character` | The analyzed character |
| `cluster_id` | Spatial cluster ID |
| `cluster_size` | Total villages in cluster |
| `n_villages_with_char` | Villages containing the character |
| `char_density_pct` | Percentage of villages with character |
| `cluster_tendency_mean` | Average tendency value for cluster's region |
| `spatial_coherence` | How tightly clustered (0-1, higher = tighter) |
| `centroid_lon`, `centroid_lat` | Cluster center coordinates |
| `avg_distance_km` | Average distance between villages in cluster |
| `dominant_city`, `dominant_county` | Most common administrative region |
| `is_significant` | Whether tendency is statistically significant |
| `avg_p_value` | Average p-value from significance testing |

### Interpreting Results

**High Character Density + High Tendency:**
- Character is both geographically concentrated AND regionally preferred
- Strong naming pattern in this geographic area

**High Character Density + Low Tendency:**
- Character is geographically concentrated but not regionally preferred overall
- May indicate a localized sub-regional pattern

**High Spatial Coherence:**
- Naming pattern forms a tight geographic cluster
- Suggests strong local tradition or geographic influence

**Low Spatial Coherence:**
- Naming pattern is geographically dispersed
- May span multiple sub-regions or follow linear features (rivers, roads)

### Example Interpretation

```
character: 田
cluster_id: 15
cluster_size: 234
n_villages_with_char: 156
char_density_pct: 66.67
cluster_tendency_mean: 45.2
spatial_coherence: 0.85
dominant_city: 梅州市
dominant_county: 梅县区
is_significant: 1
avg_p_value: 0.001
```

**Interpretation:**
- In spatial cluster #15 (梅州市梅县区 area), 66.67% of villages contain "田"
- This is 45.2% higher than the provincial average (statistically significant, p=0.001)
- The cluster is geographically tight (coherence=0.85)
- This suggests a strong, localized tradition of using "田" in village names in this area

## Database Schema

### Table: `spatial_tendency_integration`

```sql
CREATE TABLE spatial_tendency_integration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    tendency_run_id TEXT NOT NULL,
    spatial_run_id TEXT NOT NULL,

    character TEXT NOT NULL,
    cluster_id INTEGER NOT NULL,

    -- Cluster-level statistics
    cluster_tendency_mean REAL,
    cluster_tendency_std REAL,
    cluster_size INTEGER NOT NULL,
    n_villages_with_char INTEGER NOT NULL,

    -- Spatial features
    centroid_lon REAL,
    centroid_lat REAL,
    avg_distance_km REAL,
    spatial_coherence REAL,

    -- Regional information
    dominant_city TEXT,
    dominant_county TEXT,

    -- Significance
    is_significant INTEGER,
    avg_p_value REAL,

    created_at REAL NOT NULL
);
```

### Indexes

- `idx_spatial_tendency_run`: Query by run_id
- `idx_spatial_tendency_char`: Query by character
- `idx_spatial_tendency_cluster`: Query by cluster_id
- `idx_spatial_tendency_significant`: Filter significant results
- `idx_spatial_tendency_city`: Filter by city

## Advanced Usage

### Programmatic Access

```python
import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect('data/villages.db')

# Query integration results
query = """
    SELECT *
    FROM spatial_tendency_integration
    WHERE run_id = ?
      AND character = ?
      AND is_significant = 1
    ORDER BY n_villages_with_char DESC
    LIMIT 10
"""

df = pd.read_sql_query(query, conn, params=['integration_001', '田'])

# Analyze results
print(f"Top 10 clusters for '田':")
print(df[['cluster_id', 'n_villages_with_char', 'cluster_size',
          'dominant_city', 'spatial_coherence']])

conn.close()
```

### Batch Processing

Process multiple characters in parallel:

```bash
# Create a list of characters
echo "田,水,山,村,新,大,小,上,下,东" > chars.txt

# Run integration for each
python scripts/spatial_tendency_integration.py \
  --chars $(cat chars.txt) \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_batch_001
```

### Custom Analysis

Combine with other analyses:

```python
# Load integration results
integration_df = pd.read_sql_query(
    "SELECT * FROM spatial_tendency_integration WHERE run_id = ?",
    conn, params=['integration_001']
)

# Load semantic indices
semantic_df = pd.read_sql_query(
    "SELECT * FROM semantic_indices WHERE run_id = ?",
    conn, params=['semantic_001']
)

# Join on region
combined = integration_df.merge(
    semantic_df,
    left_on='dominant_county',
    right_on='region_name',
    how='inner'
)

# Analyze correlation between spatial patterns and semantic categories
print(combined.groupby('category')['spatial_coherence'].mean())
```

## Visualization

### Interactive Map Features

The generated HTML map includes:

- **Circle Markers**: Each cluster is represented by a circle
  - **Color**: Red (over-represented), Blue (under-represented), Gray (no data)
  - **Size**: Proportional to number of villages with the character
  - **Opacity**: Indicates confidence (more opaque = more significant)

- **Popups**: Click on a marker to see:
  - Character and cluster ID
  - Village counts
  - Tendency value
  - Spatial coherence
  - Administrative region
  - Statistical significance

- **Legend**: Bottom-left corner explains colors and sizing

### Map Customization

To customize the map, modify the `generate_map()` function in `scripts/spatial_tendency_integration.py`:

```python
# Change base map
m = folium.Map(
    location=[23.5, 113.5],
    zoom_start=7,
    tiles='CartoDB positron'  # or 'Stamen Terrain', 'OpenStreetMap'
)

# Adjust marker size
radius = min(max(row['n_villages_with_char'] / 5, 3), 30)  # Larger markers

# Change color scheme
if row['cluster_tendency_mean'] > 50:
    color = 'darkred'
elif row['cluster_tendency_mean'] > 0:
    color = 'orange'
else:
    color = 'lightblue'
```

## Performance Considerations

### Processing Time

- **Single character**: ~5-10 seconds
- **10 characters**: ~30-60 seconds
- **100 characters**: ~5-10 minutes

Processing time depends on:
- Number of spatial clusters
- Number of villages per cluster
- Database query performance

### Optimization Tips

1. **Use Indexes**: Ensure all indexes are created (run `init_spatial_tendency_tables.py`)

2. **Filter Early**: Use `--region-level county` instead of `township` for faster processing

3. **Batch Characters**: Process multiple characters in one run instead of separate runs

4. **Database Tuning**:
   ```sql
   PRAGMA cache_size = 10000;
   PRAGMA temp_store = MEMORY;
   ```

## Troubleshooting

### Common Issues

**Issue: "No tendency data found for character"**
- **Cause**: Character not in tendency analysis results
- **Solution**: Check that character exists in `regional_tendency` table for the specified run_id

**Issue: "No villages with character in spatial clusters"**
- **Cause**: All villages with character are noise points (cluster_id = -1)
- **Solution**: Adjust spatial clustering parameters (eps_km, min_samples) to create larger clusters

**Issue: "Database not found"**
- **Cause**: Incorrect database path
- **Solution**: Use `--db-path` to specify correct path

**Issue: "folium not installed" (when generating maps)**
- **Cause**: Missing dependency
- **Solution**: `pip install folium`

### Validation

Verify integration results:

```bash
# Check record count
sqlite3 data/villages.db \
  "SELECT COUNT(*) FROM spatial_tendency_integration WHERE run_id='integration_001';"

# Check character coverage
sqlite3 data/villages.db \
  "SELECT character, COUNT(*) as n_clusters
   FROM spatial_tendency_integration
   WHERE run_id='integration_001'
   GROUP BY character;"

# Check for NULL values
sqlite3 data/villages.db \
  "SELECT COUNT(*) FROM spatial_tendency_integration
   WHERE run_id='integration_001' AND cluster_tendency_mean IS NULL;"
```

## Best Practices

1. **Use Consistent Run IDs**: Use descriptive, timestamped run IDs (e.g., `integration_20260217_001`)

2. **Document Parameters**: Keep a log of which tendency and spatial run IDs were used

3. **Validate Results**: Always check summary statistics before detailed analysis

4. **Export Important Results**: Save significant findings to CSV for reporting

5. **Version Control**: Track changes to integration parameters and results

## Integration with Other Analyses

### Semantic Analysis

Combine spatial-tendency patterns with semantic categories:

```sql
SELECT
    st.character,
    st.cluster_id,
    st.dominant_county,
    st.spatial_coherence,
    si.category,
    si.normalized_index
FROM spatial_tendency_integration st
JOIN semantic_indices si
    ON st.dominant_county = si.region_name
WHERE st.run_id = 'integration_001'
  AND si.run_id = 'semantic_001'
  AND st.is_significant = 1
ORDER BY st.spatial_coherence DESC;
```

### Morphological Analysis

Analyze suffix patterns in spatial clusters:

```sql
SELECT
    st.cluster_id,
    st.dominant_city,
    vf.suffix_2,
    COUNT(*) as count
FROM spatial_tendency_integration st
JOIN village_spatial_features vsf
    ON st.cluster_id = vsf.spatial_cluster_id
JOIN village_features vf
    ON vsf.village_name = vf.village_name
WHERE st.run_id = 'integration_001'
  AND st.character = '田'
GROUP BY st.cluster_id, vf.suffix_2
ORDER BY count DESC;
```

## Future Enhancements

Potential improvements for future versions:

1. **Multi-level Tendency**: Calculate tendency at multiple administrative levels per cluster
2. **Temporal Analysis**: Track how spatial patterns change over time (if historical data available)
3. **Hotspot Detection**: Automatically identify statistically significant spatial hotspots
4. **Network Analysis**: Analyze connectivity between naming pattern clusters
5. **3D Visualization**: Add elevation data for topographic context

## References

- **Phase 1 Documentation**: `docs/PHASE_01_IMPLEMENTATION_SUMMARY.md` (Tendency Analysis)
- **Phase 13 Documentation**: `docs/PHASE_13_SPATIAL_ANALYSIS_GUIDE.md` (Spatial Clustering)
- **Database Schema**: `src/data/db_writer.py`
- **Integration Algorithm**: `scripts/spatial_tendency_integration.py`

## Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review the script's `--help` output
3. Examine log output for error messages
4. Verify database schema and data integrity

---

**Last Updated**: 2026-02-17
**Version**: 1.0.0
**Phase**: 2 (Spatial-Tendency Integration)
