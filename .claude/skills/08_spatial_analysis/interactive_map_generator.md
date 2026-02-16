# Skill 14: Interactive Map Generator (Folium Visualization)

## Skill Name
interactive_map_generator

## Purpose
Generate interactive HTML maps using folium for visualizing:
- Spatial clusters (colored by cluster_id)
- Density heatmaps (KDE visualization)
- Hotspot locations (circles with radius)

Offline generation, lightweight HTML output for web viewing.

---

# Part A: Map Types

**1️⃣ Cluster Map**
- Villages colored by spatial cluster assignment
- Markers with village names on hover/click
- Legend showing cluster IDs and colors
- Noise points shown in gray

**2️⃣ Density Heatmap**
- Heat gradient visualization (blue → yellow → red)
- KDE-based density estimation
- Intensity shows village concentration
- Smooth interpolation across regions

**3️⃣ Hotspot Map**
- Circles showing hotspot locations
- Radius proportional to hotspot size/intensity
- Color-coded by hotspot type (semantic/spatial)
- Popup info with hotspot statistics

---

# Part B: Implementation

**Module:** `src/spatial/map_generator.py`
**Class:** `MapGenerator`

**Script:** `scripts/generate_spatial_maps.py`

**Key Methods:**
- `generate_cluster_map()` - Create cluster visualization
- `generate_density_heatmap()` - Create KDE heatmap
- `generate_hotspot_map()` - Create hotspot circles
- `add_legend()` - Add color legend to map
- `add_layer_control()` - Enable layer toggling

**Dependencies:**
- `folium` - Interactive map generation
- `folium.plugins.HeatMap` - Heatmap plugin
- `matplotlib.cm` - Color mapping for clusters

---

# Part C: Performance Optimization

**For Large Datasets (>10k villages):**

**Strategy 1: Sampling**
- Default: Sample 10k villages max
- Stratified sampling by cluster (preserve distribution)
- Random sampling for noise points

**Strategy 2: Marker Clustering**
- Use `folium.plugins.MarkerCluster`
- Groups nearby markers at low zoom levels
- Expands to individual markers at high zoom

**Strategy 3: Simplify Geometries**
- Reduce coordinate precision (5 decimal places)
- Skip very small clusters (<5 villages)
- Aggregate nearby points

**Output Size Targets:**
- Cluster map: ~2-5 MB (with sampling)
- Heatmap: ~1-3 MB (lightweight plugin)
- Hotspot map: ~500 KB (circles only)

---

# Part D: CLI Usage

**Generate All Map Types:**
```bash
python scripts/generate_spatial_maps.py \
  --run-id spatial_v1 \
  --output-dir results/spatial_v1/maps/
```

**Generate Specific Map Type:**
```bash
python scripts/generate_spatial_maps.py \
  --map-type cluster \
  --sample-size 5000 \
  --run-id spatial_v1
```

**Advanced Options:**
```bash
python scripts/generate_spatial_maps.py \
  --map-type density \
  --region-filter "广州市" \
  --zoom-start 10 \
  --output-dir results/guangzhou_maps/
```

**Parameter Flags:**
- `--map-type` - Type: cluster, density, hotspot, or all
- `--sample-size` - Max villages to plot (default: 10000)
- `--run-id` - Spatial clustering run ID to visualize
- `--region-filter` - Optional city/county filter
- `--zoom-start` - Initial zoom level (default: 9)
- `--output-dir` - Output directory for HTML files

---

# Part E: Output Files

**Directory Structure:**
```
results/<run_id>/maps/
├── cluster_map.html          # Cluster visualization
├── density_heatmap.html      # KDE heatmap
├── hotspot_map.html          # Hotspot circles
└── metadata.json             # Map generation metadata
```

**Metadata Contents:**
- Generation timestamp
- Sample size used
- Number of clusters visualized
- Coordinate bounds
- Run ID reference

---

# Part F: Viewing Maps

**Opening Maps:**
```bash
# Open in default browser (Windows)
start results/spatial_v1/maps/cluster_map.html

# Open in default browser (Linux/Mac)
open results/spatial_v1/maps/cluster_map.html
```

**Interactive Features:**
- Pan: Click and drag
- Zoom: Scroll wheel or +/- buttons
- Marker info: Click markers for details
- Layer control: Toggle layers on/off
- Full screen: Button in top-right corner

**Browser Compatibility:**
- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Responsive design

---

# Part G: Map Customization

**Color Schemes:**
- Cluster map: Categorical colors (tab20, Set3)
- Density heatmap: Sequential (YlOrRd, viridis)
- Hotspot map: Diverging (RdYlBu)

**Base Map Tiles:**
- Default: OpenStreetMap
- Alternative: CartoDB Positron (clean style)
- Satellite: Esri WorldImagery (optional)

**Legend Customization:**
- Position: top-right, bottom-right, etc.
- Font size: Adjustable
- Background: Semi-transparent white

---

# Part H: Troubleshooting

**Issue: Map file too large (>10 MB)**
- Solution: Reduce sample size (--sample-size 5000)
- Solution: Use marker clustering
- Solution: Filter to specific region

**Issue: Map loads slowly**
- Solution: Reduce marker count
- Solution: Simplify geometries
- Solution: Use lighter base map tiles

**Issue: Markers not showing**
- Check coordinate validity (longitude, latitude)
- Verify data loaded from correct run_id
- Check browser console for JavaScript errors

**Issue: Colors not distinct**
- Use different color scheme (--color-scheme)
- Reduce number of clusters visualized
- Increase color contrast

---

# Acceptance Criteria

1. ✅ Maps generated successfully for all types
2. ✅ HTML files under 10 MB each
3. ✅ Interactive features working (pan, zoom, click)
4. ✅ Sampling applied automatically for large datasets
5. ✅ Color legends included and readable
6. ✅ Metadata file generated with run info
7. ✅ Maps viewable in standard web browsers