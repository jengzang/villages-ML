"""
语义类别API
Semantic Category API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import sqlite3

from ..dependencies import get_db, execute_query
from ..config import DEFAULT_RUN_ID, DEFAULT_SEMANTIC_RUN_ID
from ..models import SemanticCategory, SemanticVTF, RegionalSemanticVTF, SemanticTendency

router = APIRouter(prefix="/semantic/category", tags=["semantic"])


@router.get("/list", response_model=List[SemanticCategory])
def get_semantic_categories(db: sqlite3.Connection = Depends(get_db)):
    """
    获取所有语义类别
    Get all semantic categories

    Returns:
        List[SemanticCategory]: 语义类别列表
    """
    query = """
        SELECT
            category,
            category as description,
            vtf_count as character_count
        FROM semantic_vtf_global
        WHERE run_id = ?
        ORDER BY category
    """

    results = execute_query(db, query, (DEFAULT_SEMANTIC_RUN_ID,))

    if not results:
        raise HTTPException(status_code=404, detail="No semantic categories found")

    return results


@router.get("/vtf/global", response_model=List[SemanticVTF])
def get_global_semantic_vtf(
    run_id: str = Query(DEFAULT_SEMANTIC_RUN_ID, description="分析运行ID"),
    category: Optional[str] = Query(None, description="语义类别过滤"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取全局语义虚拟词频
    Get global semantic VTF (Virtual Term Frequency)

    Args:
        run_id: 分析运行ID
        category: 语义类别（可选）

    Returns:
        List[SemanticVTF]: 语义VTF列表
    """
    query = """
        SELECT
            category,
            vtf,
            character_count
        FROM semantic_vtf_global
        WHERE run_id = ?
    """
    params = [run_id]

    # 现场过滤：类别
    if category is not None:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY vtf DESC"

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(status_code=404, detail=f"No VTF data found for run_id: {run_id}")

    return results


@router.get("/vtf/regional", response_model=List[RegionalSemanticVTF])
def get_regional_semantic_vtf(
    region_level: str = Query(..., description="区域级别", pattern="^(city|county|township)$"),
    region_name: Optional[str] = Query(None, description="区域名称（可选，用于向后兼容）"),
    city: Optional[str] = Query(None, description="市级（可选）"),
    county: Optional[str] = Query(None, description="区县级（可选）"),
    township: Optional[str] = Query(None, description="乡镇级（可选）"),
    category: Optional[str] = Query(None, description="语义类别"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取区域语义虚拟词频（支持层级查询）
    Get regional semantic VTF with hierarchical filtering

    支持两种查询方式：
    1. 层级查询：使用 city/county/township 参数精确指定位置
    2. 名称查询：使用 region_name 参数（可能返回多个重复地名）

    Args:
        region_level: 区域级别 (city/county/township)
        region_name: 区域名称（可选，向后兼容）
        city: 市级名称（可选）
        county: 区县级名称（可选）
        township: 乡镇级名称（可选）
        category: 语义类别（可选）

    Returns:
        List[RegionalSemanticVTF]: 区域语义VTF列表

    Examples:
        # 精确查询特定位置
        ?region_level=township&city=清远市&county=清新区&township=太平镇

        # 查询所有同名地点（返回多条记录）
        ?region_level=township&region_name=太平镇
    """
    query = """
        SELECT
            city,
            county,
            township,
            region_name,
            category,
            frequency as vtf,
            lift as intensity_index
        FROM semantic_regional_analysis
        WHERE region_level = ?
    """
    params = [region_level]

    # 层级过滤（优先使用）
    if city is not None:
        query += " AND city = ?"
        params.append(city)

    if county is not None:
        query += " AND county = ?"
        params.append(county)

    if township is not None:
        query += " AND township = ?"
        params.append(township)

    # 名称过滤（向后兼容，可能返回多条记录）
    if region_name is not None:
        query += " AND region_name = ?"
        params.append(region_name)

    # 类别过滤
    if category is not None:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY city, county, township, frequency DESC"

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No regional VTF data found"
        )

    return results


@router.get("/tendency", response_model=List[SemanticTendency])
def get_semantic_tendency(
    region_level: str = Query(..., description="区域级别", pattern="^(city|county|township)$"),
    region_name: Optional[str] = Query(None, description="区域名称（可选，用于向后兼容）"),
    city: Optional[str] = Query(None, description="市级（可选）"),
    county: Optional[str] = Query(None, description="区县级（可选）"),
    township: Optional[str] = Query(None, description="乡镇级（可选）"),
    top_n: int = Query(9, ge=1, le=20, description="返回前N个类别"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取区域语义倾向性（支持层级查询）
    Get semantic tendency for a region with hierarchical filtering

    支持两种查询方式：
    1. 层级查询：使用 city/county/township 参数精确指定位置
    2. 名称查询：使用 region_name 参数（可能返回多个重复地名的数据）

    Args:
        region_level: 区域级别
        region_name: 区域名称（可选，向后兼容）
        city: 市级名称（可选）
        county: 区县级名称（可选）
        township: 乡镇级名称（可选）
        top_n: 返回前N个类别

    Returns:
        List[SemanticTendency]: 语义倾向性列表

    Examples:
        # 精确查询特定位置
        ?region_level=township&city=清远市&county=清新区&township=太平镇&top_n=9

        # 查询所有同名地点（返回多条记录）
        ?region_level=township&region_name=太平镇&top_n=9
    """
    query = """
        SELECT
            city,
            county,
            township,
            region_name,
            category,
            lift,
            z_score
        FROM semantic_regional_analysis
        WHERE region_level = ?
    """
    params = [region_level]

    # 层级过滤（优先使用）
    if city is not None:
        query += " AND city = ?"
        params.append(city)

    if county is not None:
        query += " AND county = ?"
        params.append(county)

    if township is not None:
        query += " AND township = ?"
        params.append(township)

    # 名称过滤（向后兼容）
    if region_name is not None:
        query += " AND region_name = ?"
        params.append(region_name)

    query += " ORDER BY z_score DESC LIMIT ?"
    params.append(top_n)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No semantic tendency data found"
        )

    return results
