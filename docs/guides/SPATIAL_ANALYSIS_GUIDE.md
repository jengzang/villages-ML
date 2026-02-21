# Phase 13: Spatial Analysis - Usage Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install scipy>=1.10.0 folium>=0.14.0
```

### 2. Run Spatial Analysis

```bash
# Basic analysis
python scripts/run_spatial_analysis.py --run-id spatial_001

# With custom parameters
python scripts/run_spatial_analysis.py \
    --run-id spatial_002 \
    --eps-km 3.0 \
    --min-samples 10

# Full analysis with maps
python scripts/run_spatial_analysis.py \
    --run-id spatial_003 \
    --feature-run-id run_002 \
    --output-dir results/spatial_003 \
    --generate-maps \
    --verbose
```

### 3. Generate Maps

```bash
# Generate all map types
python scripts/generate_spatial_maps.py \
    --run-id spatial_001 \
    --output-dir maps

# Generate specific maps
python scripts/generate_spatial_maps.py \
    --run-id spatial_001 \
    --output-dir maps \
    --map-types clusters,density
```

## Python API Usage

### Load Coordinates

```python
import sqlite3
from src.spatial.coordinate_loader import CoordinateLoader

conn = sqlite3.connect('data/villages.db')
loader = CoordinateLoader()

# Load coordinates
coords_df = loader.load_coordinates(conn)
print(f"Loaded {len(coords_df)} villages")

# Get coordinate array
coords = loader.get_coordinate_array(coords_df)
print(f"Coordinate array shape: {coords.shape}")
```

### Calculate Distances

```python
from src.spatial.distance_calculator import DistanceCalculator

calc = DistanceCalculator()

# Build BallTree
calc.build_tree(coords)

# Find k-nearest neighbors
distances, indices = calc.nearest_neighbors(coords, k=10)
print(f"Average distance to nearest neighbor: {distances[:, 0].mean():.2f} km")

# Find neighbors within radius
distances_list, indices_list = calc.radius_neighbors(coords, radius_km=5.0)
avg_neighbors = sum(len(idx) for idx in indices_list) / len(indices_list)
print(f"Average neighbors within 5km: {avg_neighbors:.1f}")
```

### Run Spatial Clustering

```python
from src.spatial.spatial_clustering import SpatialClusterer

clusterer = SpatialClusterer(eps_km=2.0, min_samples=5)

# Run DBSCAN
labels = clusterer.fit(coords)

n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
n_noise = list(labels).count(-1)

print(f"Found {n_clusters} spatial clusters")
print(f"Noise points: {n_noise} ({n_noise/len(labels)*100:.1f}%)")

# Get cluster profiles
clusters_df = clusterer.get_cluster_profiles(coords, labels, coords_df)
print(clusters_df.head())
```

### Extract Spatial Features

```python
from src.spatial.spatial_features import SpatialFeatureExtractor
from src.spatial.density_analyzer import DensityAnalyzer

# Calculate local density
density_analyzer = DensityAnalyzer()
local_density = density_analyzer.calculate_local_density(calc, coords, radii_km=[1, 5, 10])

# Extract features
feature_extractor = SpatialFeatureExtractor()
features_df = feature_extractor.extract_features(
    coords_df, coords, labels, distances, local_density
)

print(features_df.head())
print(f"\nIsolated villages: {features_df['is_isolated'].sum()}")
```

### Detect Hotspots

```python
from src.spatial.hotspot_detector import HotspotDetector

detector = HotspotDetector(bandwidth_km=5.0, threshold_percentile=95)

# Detect density hotspots
hotspots_df = detector.detect_density_hotspots(coords, coords_df)

print(f"Detected {len(hotspots_df)} density hotspots")
print(hotspots_df[['center_lat', 'center_lon', 'village_count', 'city']].head())
```

### Generate Maps

```python
from src.spatial.map_generator import MapGenerator

map_gen = MapGenerator()

# Cluster map
map_gen.create_cluster_map(
    features_df,
    'spatial_clusters.html'
)

# Density heatmap
map_gen.create_density_heatmap(
    features_df,
    'density_heatmap.html'
)

# Hotspot map
map_gen.create_hotspot_map(
    hotspots_df,
    'spatial_hotspots.html'
)

print("Maps generated! Open HTML files in browser.")
```

### Run Complete Pipeline

```python
from src.pipelines.spatial_pipeline import run_spatial_analysis_pipeline

stats = run_spatial_analysis_pipeline(
    db_path='data/villages.db',
    run_id='spatial_001',
    eps_km=2.0,
    min_samples=5,
    feature_run_id='run_002',  # Optional: integrate with semantic features
    output_dir='results/spatial_001',
    generate_maps=True
)

print(f"Analysis complete!")
print(f"Villages: {stats['n_villages']}")
print(f"Clusters: {stats['n_clusters']}")
print(f"Hotspots: {stats['n_hotspots']}")
print(f"Time: {stats['elapsed_time']:.1f}s")
```

## Query Spatial Results

### Query Village Spatial Features

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/villages.db')

# Get spatial features for a city
query = """
    SELECT village_name, longitude, latitude,
           nn_distance_1, local_density_5km,
           isolation_score, spatial_cluster_id
    FROM village_spatial_features
    WHERE run_id = 'spatial_001'
      AND city = '广州市'
    LIMIT 100
"""
df = pd.read_sql_query(query, conn)
print(df.head())

# Get isolated villages
query = """
    SELECT village_name, city, county,
           nn_distance_1, isolation_score
    FROM village_spatial_features
    WHERE run_id = 'spatial_001'
      AND is_isolated = 1
    ORDER BY isolation_score DESC
    LIMIT 20
"""
isolated_df = pd.read_sql_query(query, conn)
print(f"\nMost isolated villages:")
print(isolated_df)
```

### Query Spatial Clusters

```python
# Get cluster profiles
query = """
    SELECT cluster_id, cluster_size,
           centroid_lon, centroid_lat,
           dominant_city, dominant_county
    FROM spatial_clusters
    WHERE run_id = 'spatial_001'
    ORDER BY cluster_size DESC
    LIMIT 10
"""
clusters_df = pd.read_sql_query(query, conn)
print("Top 10 largest spatial clusters:")
print(clusters_df)

# Get villages in a specific cluster
query = """
    SELECT village_name, city, county,
           longitude, latitude
    FROM village_spatial_features
    WHERE run_id = 'spatial_001'
      AND spatial_cluster_id = 0
    LIMIT 100
"""
cluster_villages_df = pd.read_sql_query(query, conn)
print(f"\nVillages in cluster 0: {len(cluster_villages_df)}")
```

### Query Spatial Hotspots

```python
# Get all hotspots
query = """
    SELECT hotspot_id, hotspot_type,
           center_lon, center_lat,
           radius_km, village_count,
           city, county
    FROM spatial_hotspots
    WHERE run_id = 'spatial_001'
    ORDER BY village_count DESC
"""
hotspots_df = pd.read_sql_query(query, conn)
print(f"Total hotspots: {len(hotspots_df)}")
print(hotspots_df.head())

# Get density hotspots only
query = """
    SELECT *
    FROM spatial_hotspots
    WHERE run_id = 'spatial_001'
      AND hotspot_type = 'high_density'
    ORDER BY density_score DESC
    LIMIT 10
"""
density_hotspots_df = pd.read_sql_query(query, conn)
print("\nTop 10 density hotspots:")
print(density_hotspots_df)
```

### Query Regional Aggregates

```python
# Get city-level spatial aggregates
query = """
    SELECT region_name, total_villages,
           avg_nn_distance, avg_local_density,
           n_isolated_villages, n_spatial_clusters
    FROM region_spatial_aggregates
    WHERE run_id = 'spatial_001'
      AND region_level = 'city'
    ORDER BY total_villages DESC
"""
city_agg_df = pd.read_sql_query(query, conn)
print("City-level spatial aggregates:")
print(city_agg_df.head())

# Get most dispersed regions
query = """
    SELECT region_name, spatial_dispersion,
           avg_nn_distance, n_isolated_villages
    FROM region_spatial_aggregates
    WHERE run_id = 'spatial_001'
      AND region_level = 'county'
    ORDER BY spatial_dispersion DESC
    LIMIT 10
"""
dispersed_df = pd.read_sql_query(query, conn)
print("\nMost spatially dispersed counties:")
print(dispersed_df)
```

## Integration with Semantic Features

### Spatial-Semantic Analysis

```python
# Join spatial and semantic features
query = """
    SELECT
        s.village_name,
        s.city, s.county,
        s.longitude, s.latitude,
        s.spatial_cluster_id,
        s.local_density_5km,
        f.dominant_semantic_category,
        f.suffix_2,
        f.sem_mountain, f.sem_water
    FROM village_spatial_features s
    JOIN village_features f
        ON s.village_name = f.village_name
        AND f.run_id = 'run_002'
    WHERE s.run_id = 'spatial_001'
    LIMIT 1000
"""
combined_df = pd.read_sql_query(query, conn)

# Analyze semantic distribution by spatial cluster
semantic_by_cluster = combined_df.groupby(['spatial_cluster_id', 'dominant_semantic_category']).size()
print("Semantic categories by spatial cluster:")
print(semantic_by_cluster.head(20))

# Find mountain villages in high-density areas
mountain_dense = combined_df[
    (combined_df['sem_mountain'] == 1) &
    (combined_df['local_density_5km'] > 50)
]
print(f"\nMountain villages in high-density areas: {len(mountain_dense)}")
```

## Performance Tips

### For Large Datasets

```python
# Use sampling for map generation
map_gen.create_cluster_map(
    features_df.sample(n=10000, random_state=42),  # Sample 10k villages
    'spatial_clusters.html'
)

# Use pagination for queries
offset = 0
limit = 1000
while True:
    query = f"""
        SELECT * FROM village_spatial_features
        WHERE run_id = 'spatial_001'
        LIMIT {limit} OFFSET {offset}
    """
    df = pd.read_sql_query(query, conn)
    if len(df) == 0:
        break

    # Process batch
    process_batch(df)

    offset += limit
```

### Memory Management

```python
# Use chunked processing
import pandas as pd

for chunk in pd.read_sql_query(
    "SELECT * FROM village_spatial_features WHERE run_id = 'spatial_001'",
    conn,
    chunksize=10000
):
    # Process chunk
    process_chunk(chunk)
```

## Troubleshooting

### Issue: "folium not installed"

```bash
pip install folium>=0.14.0
```

### Issue: "scipy not installed"

```bash
pip install scipy>=1.10.0
```

### Issue: "No spatial features found"

Make sure you've run the spatial analysis first:

```bash
python scripts/run_spatial_analysis.py --run-id spatial_001
```

### Issue: "Memory error"

Reduce the number of points for map generation:

```python
# In map_generator.py, reduce max_points
map_gen.create_cluster_map(features_df, 'map.html', max_points=5000)
```

### Issue: "DBSCAN finds no clusters"

Try adjusting parameters:

```bash
# Increase eps (larger neighborhood)
python scripts/run_spatial_analysis.py --run-id spatial_002 --eps-km 5.0

# Decrease min_samples (less strict)
python scripts/run_spatial_analysis.py --run-id spatial_003 --min-samples 3
```

## Next Steps

1. Run spatial analysis on full dataset
2. Generate maps and explore hotspots
3. Integrate with semantic features
4. Export results for further analysis
5. Build web API (Phase 14)
6. Create interactive dashboard (Phase 15)
