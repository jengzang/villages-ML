# Spatial-Tendency Integration API Documentation

## Overview

The Spatial-Tendency Integration API provides endpoints to query the integration analysis results that combine spatial clustering with character tendency analysis. This integration reveals how character usage patterns correlate with geographic clusters.

**Module:** `api/spatial/integration.py`
**Router Prefix:** `/api/spatial`
**Tags:** `spatial-integration`

---

## Database Table

**Table:** `spatial_tendency_integration`
**Records:** 643 rows
**Run ID:** `integration_final_001`

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `run_id` | TEXT | Integration analysis run ID |
| `tendency_run_id` | TEXT | Source tendency analysis run ID |
| `spatial_run_id` | TEXT | Source spatial analysis run ID |
| `character` | TEXT | Character being analyzed |
| `cluster_id` | INTEGER | Spatial cluster ID |
| `cluster_tendency_mean` | REAL | Mean tendency value in cluster |
| `cluster_tendency_std` | REAL | Standard deviation of tendency |
| `cluster_size` | INTEGER | Number of villages in cluster |
| `n_villages_with_char` | INTEGER | Villages containing this character |
| `centroid_lon` | REAL | Cluster centroid longitude |
| `centroid_lat` | REAL | Cluster centroid latitude |
| `avg_distance_km` | REAL | Average distance from centroid (km) |
| `spatial_coherence` | REAL | Spatial coherence score (0-1) |
| `dominant_city` | TEXT | Most common city in cluster |
| `dominant_county` | TEXT | Most common county in cluster |
| `is_significant` | INTEGER | Statistical significance flag (0/1) |
| `avg_p_value` | REAL | Average p-value from significance tests |
| `created_at` | REAL | Timestamp |

---

## Endpoints

### 1. Get Integration Results

**GET** `/api/spatial/integration`

Get spatial-tendency integration analysis results with optional filters.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `run_id` | string | No | `integration_final_001` | Integration analysis run ID |
| `character` | string | No | null | Filter by specific character |
| `cluster_id` | integer | No | null | Filter by cluster ID |
| `min_cluster_size` | integer | No | null | Minimum cluster size (≥1) |
| `min_spatial_coherence` | float | No | null | Minimum spatial coherence (0-1) |
| `is_significant` | boolean | No | null | Show only significant results |
| `limit` | integer | No | 100 | Number of records to return (1-1000) |

**Response:** `List[dict]`

```json
[
  {
    "id": 1,
    "run_id": "integration_final_001",
    "character": "村",
    "cluster_id": 0,
    "cluster_tendency_mean": 4.559,
    "cluster_tendency_std": null,
    "cluster_size": 275842,
    "n_villages_with_char": 33438,
    "centroid_lon": 112.882,
    "centroid_lat": 22.762,
    "avg_distance_km": 224.63,
    "spatial_coherence": 0.471,
    "dominant_city": "广州市",
    "dominant_county": "天河区",
    "is_significant": 0,
    "avg_p_value": null
  }
]
```

**Example Requests:**

```bash
# Get all integration results
curl "http://localhost:8000/api/spatial/integration"

# Get results for character "村"
curl "http://localhost:8000/api/spatial/integration?character=村"

# Get results for cluster 0
curl "http://localhost:8000/api/spatial/integration?cluster_id=0"

# Get high-coherence clusters only
curl "http://localhost:8000/api/spatial/integration?min_spatial_coherence=0.8"

# Get significant results only
curl "http://localhost:8000/api/spatial/integration?is_significant=true"
```

**Error Responses:**
- `404`: No integration results found for specified run_id

**Performance:** <100ms

---

### 2. Get Integration by Character

**GET** `/api/spatial/integration/by-character/{character}`

Get spatial-tendency integration results for a specific character across all clusters.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `character` | string | Yes | Target character (e.g., "村") |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `run_id` | string | No | `integration_final_001` | Integration analysis run ID |
| `min_spatial_coherence` | float | No | null | Minimum spatial coherence (0-1) |

**Response:** `dict`

```json
{
  "character": "村",
  "run_id": "integration_final_001",
  "total_clusters": 128,
  "clusters": [
    {
      "cluster_id": 0,
      "cluster_tendency_mean": 4.559,
      "cluster_tendency_std": null,
      "cluster_size": 275842,
      "n_villages_with_char": 33438,
      "centroid_lon": 112.882,
      "centroid_lat": 22.762,
      "avg_distance_km": 224.63,
      "spatial_coherence": 0.471,
      "dominant_city": "广州市",
      "dominant_county": "天河区",
      "is_significant": 0,
      "avg_p_value": null
    }
  ]
}
```

**Example Requests:**

```bash
# Get all clusters for character "村"
curl "http://localhost:8000/api/spatial/integration/by-character/村"

# Get high-coherence clusters for character "新"
curl "http://localhost:8000/api/spatial/integration/by-character/新?min_spatial_coherence=0.9"
```

**Error Responses:**
- `404`: No integration results found for specified character

**Performance:** <50ms

---

### 3. Get Integration by Cluster

**GET** `/api/spatial/integration/by-cluster/{cluster_id}`

Get spatial-tendency integration results for a specific cluster across all characters.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cluster_id` | integer | Yes | Spatial cluster ID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `run_id` | string | No | `integration_final_001` | Integration analysis run ID |
| `min_tendency` | float | No | null | Minimum tendency value |

**Response:** `dict`

```json
{
  "cluster_id": 0,
  "run_id": "integration_final_001",
  "total_characters": 5,
  "characters": [
    {
      "character": "村",
      "cluster_tendency_mean": 4.559,
      "cluster_tendency_std": null,
      "cluster_size": 275842,
      "n_villages_with_char": 33438,
      "centroid_lon": 112.882,
      "centroid_lat": 22.762,
      "avg_distance_km": 224.63,
      "spatial_coherence": 0.471,
      "dominant_city": "广州市",
      "dominant_county": "天河区",
      "is_significant": 0,
      "avg_p_value": null
    }
  ]
}
```

**Example Requests:**

```bash
# Get all characters for cluster 0
curl "http://localhost:8000/api/spatial/integration/by-cluster/0"

# Get high-tendency characters for cluster 5
curl "http://localhost:8000/api/spatial/integration/by-cluster/5?min_tendency=2.0"
```

**Error Responses:**
- `404`: No integration results found for specified cluster_id

**Performance:** <50ms

---

### 4. Get Integration Summary

**GET** `/api/spatial/integration/summary`

Get summary statistics for the spatial-tendency integration analysis.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `run_id` | string | No | `integration_final_001` | Integration analysis run ID |

**Response:** `dict`

```json
{
  "run_id": "integration_final_001",
  "overall": {
    "total_records": 643,
    "unique_characters": 5,
    "unique_clusters": 234,
    "avg_tendency": 1.234,
    "avg_coherence": 0.567,
    "significant_count": 0
  },
  "top_characters": [
    {
      "character": "村",
      "cluster_count": 128,
      "avg_tendency": 4.559,
      "avg_coherence": 0.471,
      "total_villages": 33438
    }
  ],
  "top_clusters": [
    {
      "cluster_id": 0,
      "character_count": 5,
      "avg_tendency": 2.345,
      "avg_coherence": 0.678,
      "cluster_size": 275842,
      "dominant_city": "广州市",
      "dominant_county": "天河区"
    }
  ]
}
```

**Example Requests:**

```bash
# Get summary statistics
curl "http://localhost:8000/api/spatial/integration/summary"
```

**Error Responses:**
- `404`: No integration summary found for specified run_id

**Performance:** <100ms

---

## Use Cases

### 1. Find Characters with Strong Spatial Patterns

Identify characters that show high spatial coherence (clustered usage):

```bash
curl "http://localhost:8000/api/spatial/integration?min_spatial_coherence=0.9&limit=20"
```

### 2. Analyze Character Distribution Across Geography

See how a specific character's usage varies across different spatial clusters:

```bash
curl "http://localhost:8000/api/spatial/integration/by-character/村"
```

### 3. Identify Cluster Characteristics

Understand which characters are most prominent in a specific geographic cluster:

```bash
curl "http://localhost:8000/api/spatial/integration/by-cluster/0"
```

### 4. Get Overview Statistics

Get a high-level summary of the integration analysis:

```bash
curl "http://localhost:8000/api/spatial/integration/summary"
```

---

## Integration with Other Endpoints

The spatial-tendency integration endpoints complement other API endpoints:

- **Spatial Hotspots** (`/api/spatial/hotspots`): Density-based hotspot analysis
- **Spatial Clusters** (`/api/spatial/clusters`): DBSCAN clustering results
- **Character Tendency** (`/api/character/tendency/*`): Character tendency analysis
- **Character Frequency** (`/api/character/frequency/*`): Character frequency statistics

---

## Performance Notes

- All queries use indexed lookups on `run_id`, `character`, and `cluster_id`
- Response times are typically <100ms for most queries
- The `limit` parameter helps control response size
- Filters are applied at the database level for efficiency

---

## Data Quality

- **Coverage:** 643 integration records
- **Characters Analyzed:** 5 (村, 新, 大, 上, 下)
- **Clusters Processed:** 234 unique spatial clusters
- **Execution Time:** 7.49 seconds (offline processing)
- **Last Updated:** 2026-02-21

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Successful request
- `404 Not Found`: No data found for specified parameters
- `422 Unprocessable Entity`: Invalid parameter values
- `500 Internal Server Error`: Server error

Error response format:

```json
{
  "detail": "No integration results found for run_id: invalid_run_id"
}
```
