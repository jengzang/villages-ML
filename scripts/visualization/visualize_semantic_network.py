#!/usr/bin/env python3
"""
Visualize semantic network.

Usage:
    python scripts/visualize_semantic_network.py \\
        --network-json results/semantic_network/network_001/network.json \\
        --output results/semantic_network/network_001/network.html

    # With custom layout
    python scripts/visualize_semantic_network.py \\
        --network-json results/semantic_network/network_001/network.json \\
        --layout spring \\
        --output results/semantic_network/network_001/network_spring.html
"""

import argparse
import json
from pathlib import Path

import plotly.graph_objects as go
import networkx as nx
import numpy as np


def load_network_from_json(json_path: str) -> nx.Graph:
    """Load network from JSON export."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    G = nx.Graph()

    # Add nodes
    for node in data['nodes']:
        G.add_node(
            node['id'],
            label=node['label'],
            degree=node['degree'],
            centrality=node['centrality'],
            community=node.get('community')
        )

    # Add edges
    for edge in data['edges']:
        G.add_edge(
            edge['source'],
            edge['target'],
            weight=edge['weight'],
            cooccurrence=edge['cooccurrence']
        )

    return G


def compute_layout(G: nx.Graph, layout: str = 'spring') -> dict:
    """Compute node positions using specified layout algorithm."""
    if layout == 'spring':
        pos = nx.spring_layout(G, weight='weight', iterations=50, seed=42)
    elif layout == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(G, weight='weight')
    elif layout == 'circular':
        pos = nx.circular_layout(G)
    elif layout == 'spectral':
        pos = nx.spectral_layout(G, weight='weight')
    else:
        raise ValueError(f"Unknown layout: {layout}")

    return pos


def create_network_visualization(
    G: nx.Graph,
    layout: str = 'spring',
    color_by: str = 'community',
    size_by: str = 'degree'
) -> go.Figure:
    """Create interactive network visualization."""

    # Compute layout
    pos = compute_layout(G, layout)

    # Prepare edge traces
    edge_x = []
    edge_y = []
    edge_weights = []

    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_weights.append(edge[2].get('weight', 1.0))

    # Normalize edge weights for opacity
    max_weight = max(edge_weights) if edge_weights else 1.0
    edge_opacities = [w / max_weight * 0.5 + 0.1 for w in edge_weights]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # Prepare node traces
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_sizes = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        # Node label
        node_data = G.nodes[node]
        label = node_data.get('label', node)
        degree = node_data.get('degree', 0)
        centrality = node_data.get('centrality', {})
        community = node_data.get('community', -1)

        hover_text = (
            f"<b>{label}</b><br>"
            f"Degree: {G.degree(node)}<br>"
            f"Community: {community}<br>"
            f"Degree Centrality: {centrality.get('degree', 0):.4f}<br>"
            f"Betweenness: {centrality.get('betweenness', 0):.4f}<br>"
            f"Closeness: {centrality.get('closeness', 0):.4f}"
        )
        node_text.append(hover_text)

        # Node color
        if color_by == 'community':
            node_colors.append(community if community is not None else -1)
        elif color_by == 'degree':
            node_colors.append(G.degree(node))
        elif color_by == 'betweenness':
            node_colors.append(centrality.get('betweenness', 0))
        else:
            node_colors.append(0)

        # Node size
        if size_by == 'degree':
            node_sizes.append(G.degree(node) * 5 + 10)
        elif size_by == 'betweenness':
            node_sizes.append(centrality.get('betweenness', 0) * 100 + 10)
        else:
            node_sizes.append(15)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=[G.nodes[node].get('label', node) for node in G.nodes()],
        textposition='top center',
        textfont=dict(size=10),
        hovertext=node_text,
        hoverinfo='text',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(
                title=color_by.capitalize(),
                thickness=15,
                len=0.7
            ),
            line=dict(width=2, color='white')
        )
    )

    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text=f'Semantic Network ({layout} layout)',
                x=0.5,
                xanchor='center'
            ),
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            width=1200,
            height=800
        )
    )

    return fig


def main():
    parser = argparse.ArgumentParser(
        description="Visualize semantic network"
    )
    parser.add_argument(
        '--network-json',
        required=True,
        help='Path to network JSON file'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output HTML file path'
    )
    parser.add_argument(
        '--layout',
        choices=['spring', 'kamada_kawai', 'circular', 'spectral'],
        default='spring',
        help='Layout algorithm'
    )
    parser.add_argument(
        '--color-by',
        choices=['community', 'degree', 'betweenness'],
        default='community',
        help='Node coloring scheme'
    )
    parser.add_argument(
        '--size-by',
        choices=['degree', 'betweenness', 'fixed'],
        default='degree',
        help='Node sizing scheme'
    )

    args = parser.parse_args()

    # Load network
    print(f"Loading network from {args.network_json}...")
    G = load_network_from_json(args.network_json)
    print(f"Loaded network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Create visualization
    print(f"Creating visualization (layout={args.layout})...")
    fig = create_network_visualization(
        G,
        layout=args.layout,
        color_by=args.color_by,
        size_by=args.size_by
    )

    # Save to HTML
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving visualization to {output_path}...")
    fig.write_html(str(output_path))

    print(f"\nVisualization saved successfully!")
    print(f"Open {output_path} in a web browser to view.")


if __name__ == '__main__':
    main()
