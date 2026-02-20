"""
空间热点API
Spatial Hotspots API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import sqlite3

from ..dependencies import get_db, execute_query, execute_single
from ..config import DEFAULT_RUN_ID

router = APIRouter(prefix="/spatial", tags=["spatial"])


@router.get("/hotspots")
def get_spatial_hotspots(
    run_id: str = Query("spatial_001", description="空间分析运行ID"),
    min_density: Optional[float] = Query(None, description="最小密度阈值"),
    min_village_count: Optional[int] = Query(None, ge=1, description="最小村庄数量"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取空间密度热点
    Get spatial density hotspots (KDE analysis results)

    Args:
        run_id: 空间分析运行ID
        min_density: 最小密度阈值（可选）
        min_village_count: 最小村庄数量（可选）

    Returns:
        List[dict]: 热点列表
    """
    query = """
        SELECT
            hotspot_id,
            center_lon,
            center_lat,
            density_peak,
            village_count,
            radius_km,
            representative_villages
        FROM spatial_hotspots
        WHERE run_id = ?
    """
    params = [run_id]

    # 现场过滤：最小密度
    if min_density is not None:
        query += " AND density_peak >= ?"
        params.append(min_density)

    # 现场过滤：最小村庄数
    if min_village_count is not None:
        query += " AND village_count >= ?"
        params.append(min_village_count)

    query += " ORDER BY density_peak DESC"

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No spatial hotspots found for run_id: {run_id}"
        )

    return results


@router.get("/hotspots/{hotspot_id}")
def get_hotspot_detail(
    hotspot_id: int,
    run_id: str = Query("spatial_001", description="空间分析运行ID"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取单个热点详情
    Get details for a specific hotspot

    Args:
        hotspot_id: 热点ID
        run_id: 空间分析运行ID

    Returns:
        dict: 热点详情
    """
    query = """
        SELECT
            hotspot_id,
            center_lon,
            center_lat,
            density_peak,
            village_count,
            radius_km,
            representative_villages
        FROM spatial_hotspots
        WHERE run_id = ? AND hotspot_id = ?
    """

    result = execute_single(db, query, (run_id, hotspot_id))

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Hotspot {hotspot_id} not found"
        )

    return result


@router.get("/clusters")
def get_spatial_clusters(
    run_id: str = Query("spatial_001", description="空间分析运行ID"),
    cluster_id: Optional[int] = Query(None, description="聚类ID过滤"),
    min_size: Optional[int] = Query(None, ge=1, description="最小聚类大小"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取DBSCAN空间聚类结果
    Get DBSCAN spatial clustering results

    Args:
        run_id: 空间分析运行ID
        cluster_id: 聚类ID（可选，-1表示噪声点）
        min_size: 最小聚类大小（可选）
        limit: 返回记录数

    Returns:
        List[dict]: 聚类结果列表
    """
    query = """
        SELECT
            village_id,
            cluster_id,
            is_core_point,
            neighbor_count
        FROM spatial_clusters
        WHERE run_id = ?
    """
    params = [run_id]

    # 现场过滤：聚类ID
    if cluster_id is not None:
        query += " AND cluster_id = ?"
        params.append(cluster_id)

    # 现场过滤：最小聚类大小（需要子查询）
    if min_size is not None:
        query = f"""
        SELECT * FROM (
            {query}
        ) WHERE cluster_id IN (
            SELECT cluster_id
            FROM spatial_clusters
            WHERE run_id = ?
            GROUP BY cluster_id
            HAVING COUNT(*) >= ?
        )
        """
        params.extend([run_id, min_size])

    query += " ORDER BY cluster_id, village_id LIMIT ?"
    params.append(limit)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No spatial clusters found for run_id: {run_id}"
        )

    return results


@router.get("/clusters/summary")
def get_cluster_summary(
    run_id: str = Query("spatial_001", description="空间分析运行ID"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取聚类汇总统计
    Get clustering summary statistics

    Args:
        run_id: 空间分析运行ID

    Returns:
        dict: 聚类汇总信息
    """
    query = """
        SELECT
            cluster_id,
            COUNT(*) as size,
            SUM(CASE WHEN is_core_point = 1 THEN 1 ELSE 0 END) as core_points,
            AVG(neighbor_count) as avg_neighbors
        FROM spatial_clusters
        WHERE run_id = ?
        GROUP BY cluster_id
        ORDER BY size DESC
    """

    results = execute_query(db, query, (run_id,))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No cluster summary found for run_id: {run_id}"
        )

    return {
        "run_id": run_id,
        "total_clusters": len([r for r in results if r["cluster_id"] != -1]),
        "noise_points": next((r["size"] for r in results if r["cluster_id"] == -1), 0),
        "clusters": results
    }

