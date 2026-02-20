"""
Spatial-Tendency Integration Analysis.

This script integrates tendency analysis results with spatial clustering to identify
geographic patterns in village naming preferences.

Key Features:
- Combines character tendency values with spatial cluster assignments
- Calculates cluster-level tendency statistics
- Identifies spatially coherent naming regions
- Generates interactive maps showing geographic distribution of naming patterns
- Stores results in database for querying

Usage:
    python scripts/spatial_tendency_integration.py \\
        --char 田 \\
        --tendency-run-id test_sig_1771260439 \\
        --spatial-run-id spatial_001 \\
        --output-run-id integration_001

    # Multiple characters
    python scripts/spatial_tendency_integration.py \\
        --chars 田,水,山,村,新 \\
        --tendency-run-id test_sig_1771260439 \\
        --spatial-run-id spatial_001 \\
        --output-run-id integration_002

    # Generate map
    python scripts/spatial_tendency_integration.py \\
        --char 田 \\
        --tendency-run-id test_sig_1771260439 \\
        --spatial-run-id spatial_001 \\
        --output-run-id integration_001 \\
        --generate-map \\
        --output-map results/spatial_tendency_田.html
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.db_writer import (
    create_spatial_tendency_table,
    create_spatial_tendency_indexes,
    write_spatial_tendency_integration
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_tendency_results(
    conn: sqlite3.Connection,
    tendency_run_id: str,
    region_level: str = 'county'
) -> pd.DataFrame:
    """
    Load tendency analysis results from database.

    Args:
        conn: Database connection
        tendency_run_id: Run ID for tendency analysis
        region_level: Region level ('city', 'county', 'township')

    Returns:
        DataFrame with tendency results including significance
    """
    logger.info(f"Loading tendency results for run_id={tendency_run_id}, level={region_level}")

    query = """
        SELECT
            t.region_name,
            t.char,
            t.frequency as regional_frequency,
            t.global_frequency,
            t.lift,
            t.log_lift,
            t.log_odds,
            t.z_score,
            t.village_count,
            t.total_villages,
            s.p_value,
            s.is_significant,
            s.effect_size,
            s.significance_level
        FROM regional_tendency t
        LEFT JOIN tendency_significance s
            ON t.run_id = s.run_id
            AND t.region_level = s.region_level
            AND t.region_name = s.region_name
            AND t.char = s.char
        WHERE t.run_id = ? AND t.region_level = ?
    """

    df = pd.read_sql_query(query, conn, params=[tendency_run_id, region_level])
    logger.info(f"Loaded {len(df)} tendency records")

    return df


def load_spatial_features(
    conn: sqlite3.Connection,
    spatial_run_id: str
) -> pd.DataFrame:
    """
    Load spatial features from database.

    Args:
        conn: Database connection
        spatial_run_id: Run ID for spatial analysis

    Returns:
        DataFrame with spatial features
    """
    logger.info(f"Loading spatial features for run_id={spatial_run_id}")

    query = """
        SELECT
            village_id,
            village_name,
            city,
            county,
            town,
            longitude,
            latitude,
            spatial_cluster_id,
            cluster_size,
            nn_distance_1,
            local_density_1km,
            isolation_score,
            is_isolated
        FROM village_spatial_features
        WHERE run_id = ?
    """

    df = pd.read_sql_query(query, conn, params=[spatial_run_id])
    logger.info(f"Loaded {len(df)} village spatial features")

    return df


def load_villages_with_chars(
    conn: sqlite3.Connection,
    db_path: str
) -> pd.DataFrame:
    """
    Load village data with character sets.

    Args:
        conn: Database connection
        db_path: Path to database

    Returns:
        DataFrame with village names and their character sets
    """
    logger.info("Loading village data with character sets")

    query = """
        SELECT
            ROWID as row_id,
            自然村_去前缀 as village_name,
            市级 as city,
            区县级 as county,
            乡镇级 as town
        FROM 广东省自然村_预处理
        WHERE 有效 = 1
    """

    df = pd.read_sql_query(query, conn)
    logger.info(f"Loaded {len(df)} villages")

    # Generate village_id to match spatial_features table format
    df['village_id'] = 'v_' + df['row_id'].astype(str)
    df = df.drop(columns=['row_id'])  # Clean up temporary column

    # Extract character sets
    df['char_set'] = df['village_name'].apply(lambda x: set(x) if pd.notna(x) else set())

    return df


def calculate_spatial_coherence(coords: np.ndarray) -> float:
    """
    Calculate spatial coherence of a cluster.

    Coherence is measured as the inverse of the normalized standard deviation
    of distances from the centroid. Higher values indicate tighter clustering.

    Args:
        coords: Array of shape (n, 2) with [longitude, latitude]

    Returns:
        Coherence score (0-1, higher is more coherent)
    """
    if len(coords) < 2:
        return 1.0

    # Calculate centroid
    centroid = coords.mean(axis=0)

    # Calculate distances from centroid (in degrees, approximate)
    distances = np.linalg.norm(coords - centroid, axis=1)

    # Calculate standard deviation
    std = distances.std()

    # Convert to coherence score (inverse relationship)
    # Use sigmoid-like transformation to map to 0-1
    coherence = 1 / (1 + std)

    return coherence


def integrate_spatial_tendency(
    tendency_df: pd.DataFrame,
    spatial_df: pd.DataFrame,
    villages_df: pd.DataFrame,
    character: str,
    tendency_run_id: str,
    spatial_run_id: str
) -> pd.DataFrame:
    """
    Integrate spatial and tendency data for a specific character.

    Args:
        tendency_df: Tendency analysis results
        spatial_df: Spatial features
        villages_df: Village data with character sets
        character: Character to analyze
        tendency_run_id: Tendency analysis run ID
        spatial_run_id: Spatial analysis run ID

    Returns:
        DataFrame with integrated results
    """
    logger.info(f"Integrating spatial-tendency data for character '{character}'")

    # Filter tendency data for this character
    char_tendency = tendency_df[tendency_df['char'] == character].copy()

    if len(char_tendency) == 0:
        logger.warning(f"No tendency data found for character '{character}'")
        return pd.DataFrame()

    # Find villages containing this character
    villages_with_char = villages_df[
        villages_df['char_set'].apply(lambda s: character in s)
    ].copy()

    logger.info(f"Found {len(villages_with_char)} villages with character '{character}'")

    # Merge with spatial features using unique village_id
    char_spatial = villages_with_char.merge(
        spatial_df,
        on='village_id',
        how='inner',
        suffixes=('_village', '_spatial')
    )

    logger.info(f"Matched {len(char_spatial)} villages with spatial features")

    # Filter out noise points (cluster_id = -1)
    char_spatial = char_spatial[char_spatial['spatial_cluster_id'] != -1]

    logger.info(f"After removing noise: {len(char_spatial)} villages in clusters")

    if len(char_spatial) == 0:
        logger.warning(f"No villages with character '{character}' in spatial clusters")
        return pd.DataFrame()

    # Group by cluster
    cluster_stats = []
    n_clusters = char_spatial['spatial_cluster_id'].nunique()
    logger.info(f"Processing {n_clusters} clusters...")

    for idx, (cluster_id, cluster_df) in enumerate(char_spatial.groupby('spatial_cluster_id')):
        if idx % 100 == 0:
            logger.info(f"  Processed {idx}/{n_clusters} clusters...")

        # Get cluster coordinates
        coords = cluster_df[['longitude', 'latitude']].values

        # Calculate centroid
        centroid_lon = coords[:, 0].mean()
        centroid_lat = coords[:, 1].mean()

        # Calculate spatial coherence
        coherence = calculate_spatial_coherence(coords)

        # Get dominant region
        city_mode = cluster_df['city_spatial'].mode()
        dominant_city = city_mode.iloc[0] if len(city_mode) > 0 else None

        county_mode = cluster_df['county_spatial'].mode()
        dominant_county = county_mode.iloc[0] if len(county_mode) > 0 else None

        # Get tendency values for this region (use county as primary)
        region_tendency = char_tendency[char_tendency['region_name'] == dominant_county]

        if len(region_tendency) > 0:
            tendency_mean = region_tendency['lift'].mean()
            p_value = region_tendency['p_value'].mean() if 'p_value' in region_tendency.columns else None
            is_significant = region_tendency['is_significant'].any() if 'is_significant' in region_tendency.columns else False
        else:
            tendency_mean = None
            p_value = None
            is_significant = False

        # Calculate average distance within cluster (optimized)
        if len(coords) > 1:
            # Use vectorized calculation: distance from each point to centroid
            # This is O(n) instead of O(n^2) for pairwise distances
            centroid = np.array([centroid_lon, centroid_lat])
            distances_from_centroid = np.linalg.norm(coords - centroid, axis=1) * 111  # km
            # Average distance from centroid is a good proxy for cluster spread
            avg_distance_km = distances_from_centroid.mean()
        else:
            avg_distance_km = 0

        cluster_stats.append({
            'tendency_run_id': tendency_run_id,
            'spatial_run_id': spatial_run_id,
            'character': character,
            'cluster_id': int(cluster_id),
            'cluster_size': int(cluster_df['cluster_size'].iloc[0]),
            'n_villages_with_char': len(cluster_df),
            'cluster_tendency_mean': tendency_mean,
            'cluster_tendency_std': None,  # Would need multiple regions per cluster
            'centroid_lon': centroid_lon,
            'centroid_lat': centroid_lat,
            'avg_distance_km': avg_distance_km,
            'spatial_coherence': coherence,
            'dominant_city': dominant_city,
            'dominant_county': dominant_county,
            'is_significant': is_significant,
            'avg_p_value': p_value
        })

    result_df = pd.DataFrame(cluster_stats)
    logger.info(f"Generated {len(result_df)} cluster-level integration records")

    return result_df


def main():
    parser = argparse.ArgumentParser(
        description='Integrate spatial clustering with tendency analysis'
    )
    parser.add_argument(
        '--char',
        type=str,
        help='Single character to analyze'
    )
    parser.add_argument(
        '--chars',
        type=str,
        help='Comma-separated list of characters to analyze'
    )
    parser.add_argument(
        '--tendency-run-id',
        type=str,
        required=True,
        help='Run ID for tendency analysis'
    )
    parser.add_argument(
        '--spatial-run-id',
        type=str,
        required=True,
        help='Run ID for spatial analysis'
    )
    parser.add_argument(
        '--output-run-id',
        type=str,
        required=True,
        help='Run ID for this integration analysis'
    )
    parser.add_argument(
        '--region-level',
        type=str,
        default='county',
        choices=['city', 'county', 'township'],
        help='Region level for tendency analysis (default: county)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/villages.db',
        help='Path to database (default: data/villages.db)'
    )
    parser.add_argument(
        '--generate-map',
        action='store_true',
        help='Generate interactive map visualization'
    )
    parser.add_argument(
        '--output-map',
        type=str,
        help='Output path for map HTML file'
    )

    args = parser.parse_args()

    # Determine characters to analyze
    if args.char:
        characters = [args.char]
    elif args.chars:
        characters = [c.strip() for c in args.chars.split(',')]
    else:
        parser.error("Must specify either --char or --chars")

    logger.info(f"Starting spatial-tendency integration for {len(characters)} character(s)")
    logger.info(f"Tendency run: {args.tendency_run_id}")
    logger.info(f"Spatial run: {args.spatial_run_id}")
    logger.info(f"Output run: {args.output_run_id}")

    start_time = time.time()

    # Connect to database
    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    try:
        # Create tables if they don't exist
        logger.info("Creating spatial-tendency integration tables...")
        create_spatial_tendency_table(conn)
        create_spatial_tendency_indexes(conn)

        # Load data
        logger.info("Loading tendency results...")
        tendency_df = load_tendency_results(conn, args.tendency_run_id, args.region_level)

        logger.info("Loading spatial features...")
        spatial_df = load_spatial_features(conn, args.spatial_run_id)

        logger.info("Loading village data...")
        villages_df = load_villages_with_chars(conn, args.db_path)

        # Process each character
        all_results = []

        for char in characters:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing character: {char}")
            logger.info(f"{'='*60}")

            result_df = integrate_spatial_tendency(
                tendency_df=tendency_df,
                spatial_df=spatial_df,
                villages_df=villages_df,
                character=char,
                tendency_run_id=args.tendency_run_id,
                spatial_run_id=args.spatial_run_id
            )

            if len(result_df) > 0:
                all_results.append(result_df)

        # Combine all results
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            logger.info(f"\nTotal integration records: {len(combined_df)}")

            # Write to database
            logger.info("Writing results to database...")
            write_spatial_tendency_integration(conn, args.output_run_id, combined_df)

            # Print summary
            print("\n" + "="*60)
            print("SPATIAL-TENDENCY INTEGRATION SUMMARY")
            print("="*60)
            print(f"Run ID: {args.output_run_id}")
            print(f"Characters analyzed: {len(characters)}")
            print(f"Total clusters: {combined_df['cluster_id'].nunique()}")
            print(f"Total records: {len(combined_df)}")
            print(f"\nTop 10 clusters by character density:")
            print(combined_df.nlargest(10, 'n_villages_with_char')[
                ['character', 'cluster_id', 'n_villages_with_char', 'cluster_size',
                 'dominant_city', 'dominant_county', 'spatial_coherence']
            ].to_string(index=False))

            # Generate map if requested
            if args.generate_map:
                if not args.output_map:
                    logger.error("--output-map required when --generate-map is specified")
                else:
                    logger.info(f"\nGenerating map: {args.output_map}")
                    generate_map(combined_df, args.output_map, characters[0] if len(characters) == 1 else None)

        else:
            logger.warning("No integration results generated")

        elapsed = time.time() - start_time
        logger.info(f"\nIntegration completed in {elapsed:.2f}s")

    except Exception as e:
        logger.error(f"Error during integration: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


def generate_map(df: pd.DataFrame, output_path: str, character: Optional[str] = None):
    """
    Generate interactive map visualization.

    Args:
        df: Integration results DataFrame
        output_path: Output HTML file path
        character: Optional character to highlight (if analyzing single character)
    """
    try:
        import folium
        from folium import plugins
    except ImportError:
        logger.error("folium not installed. Install with: pip install folium")
        return

    logger.info("Generating interactive map...")

    # Filter for specific character if provided
    if character:
        df = df[df['character'] == character]

    # Create map centered on Guangdong
    m = folium.Map(
        location=[23.5, 113.5],
        zoom_start=7,
        tiles='OpenStreetMap'
    )

    # Add cluster markers
    for _, row in df.iterrows():
        # Color by tendency (if available)
        if pd.notna(row['cluster_tendency_mean']):
            if row['cluster_tendency_mean'] > 0:
                color = 'red'  # Over-represented
            else:
                color = 'blue'  # Under-represented
        else:
            color = 'gray'

        # Size by number of villages
        radius = min(max(row['n_villages_with_char'] / 10, 5), 20)

        # Create popup text
        popup_text = f"""
        <b>Character:</b> {row['character']}<br>
        <b>Cluster ID:</b> {row['cluster_id']}<br>
        <b>Villages with char:</b> {row['n_villages_with_char']}/{row['cluster_size']}<br>
        <b>Tendency:</b> {row['cluster_tendency_mean']:.2f if pd.notna(row['cluster_tendency_mean']) else 'N/A'}<br>
        <b>Coherence:</b> {row['spatial_coherence']:.3f}<br>
        <b>City:</b> {row['dominant_city']}<br>
        <b>County:</b> {row['dominant_county']}<br>
        <b>Significant:</b> {'Yes' if row['is_significant'] else 'No'}
        """

        folium.CircleMarker(
            location=[row['centroid_lat'], row['centroid_lon']],
            radius=radius,
            popup=folium.Popup(popup_text, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.6
        ).add_to(m)

    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 120px;
                background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                padding: 10px">
    <p><b>Tendency Legend</b></p>
    <p><span style="color:red;">●</span> Over-represented</p>
    <p><span style="color:blue;">●</span> Under-represented</p>
    <p><span style="color:gray;">●</span> No data</p>
    <p><i>Size = # villages</i></p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save map
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))

    logger.info(f"Map saved to: {output_path}")


if __name__ == '__main__':
    main()
