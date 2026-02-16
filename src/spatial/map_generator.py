"""
Interactive Map Generation using Folium.

Creates HTML maps for spatial visualization.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    import folium
    from folium import plugins
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    logger.warning("folium not installed. Map generation will be disabled.")


class MapGenerator:
    """Generate interactive maps for spatial data."""

    def __init__(self, center_lat: float = 23.5, center_lon: float = 113.5, zoom_start: int = 8):
        """
        Initialize map generator.

        Args:
            center_lat: Map center latitude (default: Guangdong center)
            center_lon: Map center longitude (default: Guangdong center)
            zoom_start: Initial zoom level (default: 8)
        """
        if not FOLIUM_AVAILABLE:
            raise ImportError("folium is required for map generation. Install with: pip install folium")

        self.center_lat = center_lat
        self.center_lon = center_lon
        self.zoom_start = zoom_start

    def create_cluster_map(
        self,
        features_df: pd.DataFrame,
        output_path: str,
        max_points: int = 10000
    ):
        """
        Create map showing spatial clusters.

        Args:
            features_df: DataFrame with spatial features and cluster labels
            output_path: Output HTML file path
            max_points: Maximum number of points to plot (for performance)
        """
        logger.info(f"Creating cluster map with {len(features_df)} villages")

        # Sample if too many points
        if len(features_df) > max_points:
            logger.warning(f"Sampling {max_points} villages for visualization")
            features_df = features_df.sample(n=max_points, random_state=42)

        # Create base map
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom_start,
            tiles='OpenStreetMap'
        )

        # Get unique clusters (excluding noise -1)
        clusters = sorted([c for c in features_df['spatial_cluster_id'].unique() if c != -1])

        # Color palette
        colors = self._get_color_palette(len(clusters))

        # Add cluster points
        for i, cluster_id in enumerate(clusters):
            cluster_df = features_df[features_df['spatial_cluster_id'] == cluster_id]

            for _, row in cluster_df.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=3,
                    color=colors[i],
                    fill=True,
                    fillColor=colors[i],
                    fillOpacity=0.6,
                    popup=f"{row['village_name']}<br>Cluster: {cluster_id}<br>Size: {row['cluster_size']}",
                    tooltip=row['village_name']
                ).add_to(m)

        # Add noise points (if any)
        noise_df = features_df[features_df['spatial_cluster_id'] == -1]
        if len(noise_df) > 0:
            for _, row in noise_df.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=2,
                    color='gray',
                    fill=True,
                    fillColor='gray',
                    fillOpacity=0.3,
                    popup=f"{row['village_name']}<br>Noise point",
                    tooltip=row['village_name']
                ).add_to(m)

        # Save map
        m.save(output_path)
        logger.info(f"Cluster map saved to {output_path}")

    def create_density_heatmap(
        self,
        features_df: pd.DataFrame,
        output_path: str,
        max_points: int = 50000
    ):
        """
        Create density heatmap.

        Args:
            features_df: DataFrame with spatial features
            output_path: Output HTML file path
            max_points: Maximum number of points for heatmap
        """
        logger.info(f"Creating density heatmap with {len(features_df)} villages")

        # Sample if too many points
        if len(features_df) > max_points:
            logger.warning(f"Sampling {max_points} villages for heatmap")
            features_df = features_df.sample(n=max_points, random_state=42)

        # Create base map
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom_start,
            tiles='OpenStreetMap'
        )

        # Prepare heatmap data
        heat_data = [[row['latitude'], row['longitude']] for _, row in features_df.iterrows()]

        # Add heatmap layer
        plugins.HeatMap(
            heat_data,
            min_opacity=0.2,
            max_zoom=13,
            radius=15,
            blur=20,
            gradient={0.4: 'blue', 0.65: 'lime', 0.8: 'yellow', 1.0: 'red'}
        ).add_to(m)

        # Save map
        m.save(output_path)
        logger.info(f"Density heatmap saved to {output_path}")

    def create_hotspot_map(
        self,
        hotspots_df: pd.DataFrame,
        output_path: str
    ):
        """
        Create map showing hotspots.

        Args:
            hotspots_df: DataFrame with hotspot information
            output_path: Output HTML file path
        """
        logger.info(f"Creating hotspot map with {len(hotspots_df)} hotspots")

        # Create base map
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom_start,
            tiles='OpenStreetMap'
        )

        # Color by hotspot type
        type_colors = {
            'high_density': 'red',
            'naming_hotspot': 'blue',
            'combined_hotspot': 'purple'
        }

        # Add hotspot circles
        for _, hotspot in hotspots_df.iterrows():
            color = type_colors.get(hotspot['hotspot_type'], 'orange')

            # Create popup text
            popup_text = f"""
            <b>Hotspot {hotspot['hotspot_id']}</b><br>
            Type: {hotspot['hotspot_type']}<br>
            Villages: {hotspot['village_count']}<br>
            Radius: {hotspot['radius_km']:.2f} km<br>
            City: {hotspot.get('city', 'N/A')}<br>
            County: {hotspot.get('county', 'N/A')}
            """

            if pd.notna(hotspot.get('semantic_category')):
                popup_text += f"<br>Category: {hotspot['semantic_category']}"

            folium.Circle(
                location=[hotspot['center_lat'], hotspot['center_lon']],
                radius=hotspot['radius_km'] * 1000,  # Convert to meters
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.2,
                popup=popup_text,
                tooltip=f"Hotspot {hotspot['hotspot_id']}"
            ).add_to(m)

            # Add center marker
            folium.CircleMarker(
                location=[hotspot['center_lat'], hotspot['center_lon']],
                radius=5,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.8
            ).add_to(m)

        # Save map
        m.save(output_path)
        logger.info(f"Hotspot map saved to {output_path}")

    def _get_color_palette(self, n_colors: int) -> list:
        """
        Generate color palette for clusters.

        Args:
            n_colors: Number of colors needed

        Returns:
            List of color hex codes
        """
        # Use a predefined palette for small n
        if n_colors <= 10:
            return ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
                   '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5'][:n_colors]

        # Generate colors using HSV for larger n
        import colorsys
        colors = []
        for i in range(n_colors):
            hue = i / n_colors
            rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
            hex_color = '#{:02x}{:02x}{:02x}'.format(
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255)
            )
            colors.append(hex_color)

        return colors
