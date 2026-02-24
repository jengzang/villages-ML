"""
N-gram分析API
N-gram Analysis API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import sqlite3

from ..dependencies import get_db, execute_query
from ..config import DEFAULT_RUN_ID
from ..run_id_manager import run_id_manager

router = APIRouter(prefix="/ngrams", tags=["ngrams"])


@router.get("/frequency")
def get_ngram_frequency(
    n: int = Query(..., ge=2, le=4, description="N-gram大小 (2=bigram, 3=trigram)"),
    top_k: int = Query(100, ge=1, le=1000, description="返回前K个n-grams"),
    min_frequency: Optional[int] = Query(None, ge=1, description="最小频次过滤"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取全局N-gram频率
    Get global n-gram frequencies

    Args:
        n: N-gram大小 (2, 3, 或 4)
        top_k: 返回前K个高频n-grams
        min_frequency: 最小频次阈值（可选）

    Returns:
        List[dict]: N-gram频率列表
    """
    query = """
        SELECT
            ngram,
            frequency,
            percentage
        FROM ngram_frequency
        WHERE n = ?
    """
    params = [n]

    # 现场过滤：最小频次
    if min_frequency is not None:
        query += " AND frequency >= ?"
        params.append(min_frequency)

    query += " ORDER BY frequency DESC LIMIT ?"
    params.append(top_k)

    # Debug: print the query
    print(f"DEBUG: Query = {query}")
    print(f"DEBUG: Params = {params}")

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No {n}-grams found"
        )

    return results


@router.get("/regional")
def get_regional_ngram_frequency(
    n: int = Query(..., ge=2, le=4, description="N-gram大小"),
    region_level: str = Query(..., description="区域级别", pattern="^(city|county|township)$"),
    region_name: Optional[str] = Query(None, description="区域名称（可选，用于向后兼容）"),
    city: Optional[str] = Query(None, description="市级（可选）"),
    county: Optional[str] = Query(None, description="区县级（可选）"),
    township: Optional[str] = Query(None, description="乡镇级（可选）"),
    top_k: int = Query(50, ge=1, le=500, description="每个区域返回前K个n-grams"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取区域N-gram频率（支持层级查询）
    Get regional n-gram frequencies with hierarchical filtering

    支持两种查询方式：
    1. 层级查询：使用 city/county/township 参数精确指定位置
    2. 名称查询：使用 region_name 参数（可能返回多个重复地名的数据）

    Args:
        n: N-gram大小
        region_level: 区域级别 (city/county/township)
        region_name: 区域名称（可选，向后兼容）
        city: 市级名称（可选）
        county: 区县级名称（可选）
        township: 乡镇级名称（可选）
        top_k: 每个区域返回前K个n-grams

    Returns:
        List[dict]: 区域N-gram频率列表

    Examples:
        # 精确查询特定位置
        ?n=2&region_level=township&city=清远市&county=清新区&township=太平镇&top_k=50

        # 查询所有同名地点
        ?n=2&region_level=township&region_name=太平镇&top_k=50
    """
    query = """
        SELECT
            city,
            county,
            township,
            region as region_name,
            ngram,
            frequency,
            percentage
        FROM regional_ngram_frequency
        WHERE n = ? AND level = ?
    """
    params = [n, region_level]

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
        query += " AND region = ?"
        params.append(region_name)

    # 现场排序和限制
    query += " ORDER BY city, county, township, frequency DESC LIMIT ?"
    params.append(top_k)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No regional {n}-grams found"
        )

    return results


@router.get("/patterns")
def get_structural_patterns(
    pattern_type: Optional[str] = Query(None, description="模式类型过滤"),
    min_frequency: Optional[int] = Query(None, ge=1, description="最小频次过滤"),
    limit: int = Query(100, ge=1, le=500, description="返回记录数"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取结构化命名模式
    Get structural naming patterns

    Args:
        pattern_type: 模式类型（可选）
        min_frequency: 最小频次（可选）
        limit: 返回记录数

    Returns:
        List[dict]: 结构化模式列表
    """
    query = """
        SELECT
            pattern,
            pattern_type,
            frequency,
            example
        FROM structural_patterns
    """
    params = []

    # 现场过滤：模式类型
    conditions = []
    if pattern_type is not None:
        conditions.append("pattern_type = ?")
        params.append(pattern_type)

    # 现场过滤：最小频次
    if min_frequency is not None:
        conditions.append("frequency >= ?")
        params.append(min_frequency)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY frequency DESC LIMIT ?"
    params.append(limit)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No structural patterns found"
        )

    return results


@router.get("/tendency")
def get_ngram_tendency(
    ngram: Optional[str] = Query(None, description="N-gram"),
    region_level: str = Query("county", description="区域级别", pattern="^(city|county|township)$"),
    region_name: Optional[str] = Query(None, description="区域名称（可选，用于向后兼容）"),
    city: Optional[str] = Query(None, description="市级（可选）"),
    county: Optional[str] = Query(None, description="区县级（可选）"),
    township: Optional[str] = Query(None, description="乡镇级（可选）"),
    min_lift: Optional[float] = Query(None, description="最小lift值"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取N-gram倾向性（支持层级查询）
    Get n-gram tendency scores with hierarchical filtering

    支持两种查询方式：
    1. 层级查询：使用 city/county/township 参数精确指定位置
    2. 名称查询：使用 region_name 参数（可能返回多个重复地名的数据）

    Args:
        ngram: N-gram（可选）
        region_level: 区域级别
        region_name: 区域名称（可选，向后兼容）
        city: 市级名称（可选）
        county: 区县级名称（可选）
        township: 乡镇级名称（可选）
        min_lift: 最小lift值（可选）
        limit: 返回记录数

    Returns:
        List[dict]: N-gram倾向性列表
    """
    query = """
        SELECT
            level as region_level,
            city,
            county,
            township,
            region as region_name,
            ngram,
            n,
            lift,
            log_odds,
            z_score
        FROM ngram_tendency
        WHERE level = ?
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
        query += " AND region = ?"
        params.append(region_name)

    # N-gram 过滤
    if ngram is not None:
        query += " AND ngram = ?"
        params.append(ngram)

    # Lift 过滤
    if min_lift is not None:
        query += " AND lift >= ?"
        params.append(min_lift)

    query += " ORDER BY lift DESC LIMIT ?"
    params.append(limit)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No n-gram tendency data found"
        )

    return results


@router.get("/significance")
def get_ngram_significance(
    ngram: Optional[str] = Query(None, description="N-gram"),
    region_level: str = Query("county", description="区域级别", pattern="^(city|county|township)$"),
    region_name: Optional[str] = Query(None, description="区域名称（可选，用于向后兼容）"),
    city: Optional[str] = Query(None, description="市级（可选）"),
    county: Optional[str] = Query(None, description="区县级（可选）"),
    township: Optional[str] = Query(None, description="乡镇级（可选）"),
    is_significant: Optional[bool] = Query(None, description="仅显示显著结果"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取N-gram显著性（支持层级查询）
    Get n-gram significance test results with hierarchical filtering

    支持两种查询方式：
    1. 层级查询：使用 city/county/township 参数精确指定位置
    2. 名称查询：使用 region_name 参数（可能返回多个重复地名的数据）

    Args:
        ngram: N-gram（可选）
        region_level: 区域级别
        region_name: 区域名称（可选，向后兼容）
        city: 市级名称（可选）
        county: 区县级名称（可选）
        township: 乡镇级名称（可选）
        is_significant: 仅显示显著结果（可选）
        limit: 返回记录数

    Returns:
        List[dict]: N-gram显著性列表
    """
    query = """
        SELECT
            level as region_level,
            city,
            county,
            township,
            region as region_name,
            ngram,
            n,
            chi2,
            p_value,
            cramers_v,
            is_significant
        FROM ngram_significance
        WHERE level = ?
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
        query += " AND region = ?"
        params.append(region_name)

    # N-gram 过滤
    if ngram is not None:
        query += " AND ngram = ?"
        params.append(ngram)

    # 显著性过滤
    if is_significant is not None:
        query += " AND is_significant = ?"
        params.append(1 if is_significant else 0)

    query += " ORDER BY chi2 DESC LIMIT ?"
    params.append(limit)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No n-gram significance data found"
        )

    return results
