# Spatial-Tendency Integration Skill

## Description

Integrate regional tendency analysis with spatial clustering to identify geographic patterns in village naming preferences. This skill combines two completed analyses (Phase 1: Tendency Analysis and Phase 13: Spatial Clustering) to reveal how naming patterns vary across the geographic landscape of Guangdong Province.

## When to Use

Use this skill when you want to:
- Identify where specific characters are geographically concentrated
- Discover natural geographic boundaries of naming traditions
- Analyze naming patterns that transcend administrative divisions
- Visualize the geographic distribution of character preferences
- Measure spatial coherence of naming patterns

## Prerequisites

1. **Completed Tendency Analysis** with run ID (e.g., `test_sig_1771260439`)
2. **Completed Spatial Clustering** with run ID (e.g., `spatial_001`)
3. **Database tables initialized** (run `scripts/init_spatial_tendency_tables.py`)

## Quick Start

### Initialize Tables (First Time Only)

```bash
python scripts/init_spatial_tendency_tables.py
```

### Run Integration Analysis

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

### Query Results

```bash
# View summary
python scripts/query_spatial_tendency.py --run-id integration_001

# Filter by character
python scripts/query_spatial_tendency.py --run-id integration_001 --char 田

# Significant results only
python scripts/query_spatial_tendency.py \
  --run-id integration_001 \
  --significant-only \
  --top-n 20
```

### Generate Interactive Map

```bash
python scripts/spatial_tendency_integration.py \
  --char 田 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_003 \
  --generate-map \
  --output-map results/spatial_tendency_田.html
```

## Parameters

### Integration Script

**Required:**
- `--tendency-run-id`: Run ID from tendency analysis
- `--spatial-run-id`: Run ID from spatial clustering
- `--output-run-id`: Unique ID for this integration run

**Character Selection (one required):**
- `--char`: Single character (e.g., `--char 田`)
- `--chars`: Comma-separated list (e.g., `--chars 田,水,山`)

**Optional:**
- `--region-level`: Region level (`city`, `county`, `township`). Default: `county`
- `--db-path`: Database path. Default: `data/villages.db`
- `--generate-map`: Generate interactive HTML map
- `--output-map`: Output path for map file

### Query Script

**Required:**
- `--run-id`: Integration run ID

**Filters:**
- `--char`: Filter by character
- `--significant-only`: Only significant results
- `--city`: Filter by city
- `--county`: Filter by county
- `--min-cluster-size`: Minimum cluster size
- `--top-n`: Top N by character density

**Output:**
- `--output`: Export to CSV
- `--no-summary`: Skip summary statistics

## Output

### Console Output

```
SPATIAL-TENDENCY INTEGRATION SUMMARY
====================================
Run ID: integration_001
Characters analyzed: 1
Total clusters: 45
Total records: 45

Top 10 clusters by character density:
character  cluster_id  n_villages_with_char  cluster_size  dominant_city  dominant_county  spatial_coherence
田         15          156                   234           梅州市         梅县区           0.85
田         23          89                    145           河源市         龙川县           0.78
...
```

### Database Records

Results are stored in `spatial_tendency_integration` table:

| Column | Description |
|--------|-------------|
| `character` | Analyzed character |
| `cluster_id` | Spatial cluster ID |
| `cluster_size` | Total villages in cluster |
| `n_villages_with_char` | Villages with character |
| `char_density_pct` | Percentage with character |
| `cluster_tendency_mean` | Average tendency value |
| `spatial_coherence` | Geographic tightness (0-1) |
| `dominant_city`, `dominant_county` | Main region |
| `is_significant` | Statistical significance |

### Interactive Map

HTML map with:
- **Circle markers** for each cluster
- **Color coding**: Red (over-represented), Blue (under-represented)
- **Size**: Proportional to village count
- **Popups**: Detailed cluster information
- **Legend**: Explains visualization

## Examples

### Example 1: Analyze "田" (Field) Character

```bash
# Run integration
python scripts/spatial_tendency_integration.py \
  --char 田 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_tian_001

# Query significant clusters
python scripts/query_spatial_tendency.py \
  --run-id integration_tian_001 \
  --significant-only \
  --top-n 10

# Generate map
python scripts/spatial_tendency_integration.py \
  --char 田 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_tian_002 \
  --generate-map \
  --output-map results/tian_spatial_map.html
```

### Example 2: Batch Analysis of Water-Related Characters

```bash
# Analyze multiple water-related characters
python scripts/spatial_tendency_integration.py \
  --chars 水,河,江,湖,海,溪,泉,池 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_water_001

# Query results for specific city
python scripts/query_spatial_tendency.py \
  --run-id integration_water_001 \
  --city 梅州市 \
  --output results/water_chars_meizhou.csv
```

### Example 3: Compare Spatial Coherence

```bash
# Analyze characters with different expected patterns
python scripts/spatial_tendency_integration.py \
  --chars 山,村,新 \
  --tendency-run-id test_sig_1771260439 \
  --spatial-run-id spatial_001 \
  --output-run-id integration_compare_001

# Query and compare coherence
python scripts/query_spatial_tendency.py \
  --run-id integration_compare_001 \
  --output results/coherence_comparison.csv

# Analyze in Python
python -c "
import pandas as pd
df = pd.read_csv('results/coherence_comparison.csv')
print(df.groupby('character')['spatial_coherence'].describe())
"
```

## Interpretation Guide

### High Character Density + High Tendency
- Character is both geographically concentrated AND regionally preferred
- Strong naming pattern in this area

### High Spatial Coherence (>0.8)
- Naming pattern forms tight geographic cluster
- Suggests strong local tradition or geographic influence

### Low Spatial Coherence (<0.5)
- Naming pattern is geographically dispersed
- May follow linear features (rivers, roads) or span multiple sub-regions

### Significant Results (is_significant=1)
- Tendency value is statistically significant (p < 0.05)
- Pattern is unlikely due to chance

## Performance

- **Single character**: ~5-10 seconds
- **10 characters**: ~30-60 seconds
- **100 characters**: ~5-10 minutes

## Troubleshooting

**"No tendency data found"**
- Check that character exists in tendency analysis results
- Verify tendency_run_id is correct

**"No villages in spatial clusters"**
- All villages with character are noise points (cluster_id=-1)
- Adjust spatial clustering parameters

**"folium not installed"**
- Install with: `pip install folium`

## Related Skills

- **Tendency Analysis** (`tendency-analysis`): Generate tendency analysis results
- **Spatial Clustering** (Phase 13): Generate spatial cluster assignments
- **Semantic Analysis** (Phase 4): Analyze semantic categories
- **Query Tendency** (`scripts/query_tendency.py`): Query tendency results

## Files

- **Integration Script**: `scripts/spatial_tendency_integration.py`
- **Query Script**: `scripts/query_spatial_tendency.py`
- **Initialization**: `scripts/init_spatial_tendency_tables.py`
- **Database Writer**: `src/data/db_writer.py`
- **Documentation**: `docs/SPATIAL_TENDENCY_INTEGRATION_GUIDE.md`

## Database Schema

```sql
CREATE TABLE spatial_tendency_integration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    tendency_run_id TEXT NOT NULL,
    spatial_run_id TEXT NOT NULL,
    character TEXT NOT NULL,
    cluster_id INTEGER NOT NULL,
    cluster_tendency_mean REAL,
    cluster_size INTEGER NOT NULL,
    n_villages_with_char INTEGER NOT NULL,
    centroid_lon REAL,
    centroid_lat REAL,
    spatial_coherence REAL,
    dominant_city TEXT,
    dominant_county TEXT,
    is_significant INTEGER,
    avg_p_value REAL,
    created_at REAL NOT NULL
);
```

## Notes

- Results are persisted to database for efficient querying
- Integration preserves both tendency and spatial run IDs for traceability
- Spatial coherence is calculated using distance standard deviation
- Noise points (cluster_id=-1) are excluded from analysis
- Map generation requires `folium` package

---

**Phase**: 2 (Spatial-Tendency Integration)
**Status**: Production Ready
**Last Updated**: 2026-02-17
