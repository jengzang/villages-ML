"""
Semantic Network Centrality API Endpoints

Provides endpoints for querying semantic network centrality metrics.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import sqlite3

router = APIRouter(prefix="/semantic", tags=["semantic"])

DB_PATH = "data/villages.db"


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def get_latest_run_id(conn: sqlite3.Connection) -> str:
    """Get the latest run_id from semantic_network_stats."""
    cursor = conn.cursor()
    cursor.execute("""
    SELECT run_id FROM semantic_network_stats
    ORDER BY created_at DESC
    LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No semantic network data found")
    return row[0]


@router.get("/centrality/ranking")
async def get_centrality_ranking(
    metric: str = Query(
        "pagerank",
        regex="^(pagerank|degree|betweenness|closeness|eigenvector)$",
        description="中心性指标"
    ),
    top_k: Optional[int] = Query(None, ge=1, le=100, description="返回前K个类别")
):
    """
    获取按中心性指标排序的语义类别

    Get categories ranked by centrality metric.

    Args:
        metric: Centrality metric ('pagerank', 'degree', 'betweenness', 'closeness', 'eigenvector')
        top_k: Number of top categories to return (optional, default: all)

    Returns:
        Categories with centrality scores, sorted descending
    """
    conn = get_db()
    run_id = get_latest_run_id(conn)
    cursor = conn.cursor()

    # Map metric name to column
    metric_column = f"{metric}_centrality" if metric != "pagerank" else "pagerank"

    query = f"""
    SELECT
        category,
        degree_centrality,
        betweenness_centrality,
        closeness_centrality,
        eigenvector_centrality,
        pagerank,
        community_id
    FROM semantic_network_centrality
    WHERE run_id = ?
    ORDER BY {metric_column} DESC
    """

    if top_k:
        query += f" LIMIT {top_k}"

    cursor.execute(query, (run_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No centrality data found")

    return {
        "metric": metric,
        "count": len(rows),
        "categories": [
            {
                "category": row[0],
                "degree_centrality": round(row[1], 4),
                "betweenness_centrality": round(row[2], 4),
                "closeness_centrality": round(row[3], 4),
                "eigenvector_centrality": round(row[4], 4),
                "pagerank": round(row[5], 4),
                "community_id": row[6]
            }
            for row in rows
        ]
    }


@router.get("/centrality/category")
async def get_category_centrality(
    category: str = Query(..., description="语义类别名称")
):
    """
    获取特定语义类别的所有中心性指标

    Get all centrality metrics for a specific category.

    Args:
        category: Category name

    Returns:
        All 5 centrality metrics + community_id
    """
    conn = get_db()
    run_id = get_latest_run_id(conn)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        category,
        degree_centrality,
        betweenness_centrality,
        closeness_centrality,
        eigenvector_centrality,
        pagerank,
        community_id
    FROM semantic_network_centrality
    WHERE run_id = ? AND category = ?
    """, (run_id, category))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    return {
        "category": row[0],
        "degree_centrality": round(row[1], 4),
        "betweenness_centrality": round(row[2], 4),
        "closeness_centrality": round(row[3], 4),
        "eigenvector_centrality": round(row[4], 4),
        "pagerank": round(row[5], 4),
        "community_id": row[6]
    }


@router.get("/centrality/compare")
async def compare_centrality():
    """
    比较所有语义类别的中心性指标

    Compare centrality metrics across all categories.

    Returns:
        All categories with all metrics for comparison
    """
    conn = get_db()
    run_id = get_latest_run_id(conn)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        category,
        degree_centrality,
        betweenness_centrality,
        closeness_centrality,
        eigenvector_centrality,
        pagerank,
        community_id
    FROM semantic_network_centrality
    WHERE run_id = ?
    ORDER BY pagerank DESC
    """, (run_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No centrality data found")

    return {
        "count": len(rows),
        "categories": [
            {
                "category": row[0],
                "degree_centrality": round(row[1], 4),
                "betweenness_centrality": round(row[2], 4),
                "closeness_centrality": round(row[3], 4),
                "eigenvector_centrality": round(row[4], 4),
                "pagerank": round(row[5], 4),
                "community_id": row[6]
            }
            for row in rows
        ]
    }


@router.get("/network/stats")
async def get_network_stats():
    """
    获取语义网络统计信息

    Get network-level statistics.

    Returns:
        Nodes, edges, density, communities, modularity, etc.
    """
    conn = get_db()
    run_id = get_latest_run_id(conn)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        num_nodes, num_edges, density, is_connected,
        num_components, avg_clustering, diameter,
        avg_shortest_path, modularity, num_communities
    FROM semantic_network_stats
    WHERE run_id = ?
    """, (run_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No network stats found")

    return {
        "run_id": run_id,
        "num_nodes": row[0],
        "num_edges": row[1],
        "density": round(row[2], 4),
        "is_connected": bool(row[3]),
        "num_components": row[4],
        "avg_clustering": round(row[5], 4),
        "diameter": row[6],
        "avg_shortest_path": round(row[7], 4) if row[7] else None,
        "modularity": round(row[8], 4) if row[8] else None,
        "num_communities": row[9]
    }


@router.get("/communities")
async def get_communities():
    """
    获取语义网络社区结构

    Get community structure.

    Returns:
        Communities with member categories and sizes
    """
    conn = get_db()
    run_id = get_latest_run_id(conn)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT community_id, COUNT(*) as size,
           GROUP_CONCAT(category, ', ') as members
    FROM semantic_network_centrality
    WHERE run_id = ?
    GROUP BY community_id
    ORDER BY size DESC
    """, (run_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No community data found")

    return {
        "count": len(rows),
        "communities": [
            {
                "community_id": row[0],
                "size": row[1],
                "members": row[2].split(', ') if row[2] else []
            }
            for row in rows
        ]
    }
