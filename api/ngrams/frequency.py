"""
N-gram分析API
N-gram Analysis API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import sqlite3

from ..dependencies import get_db, execute_query
from ..config import DEFAULT_RUN_ID

router = APIRouter(prefix="/ngrams", tags=["ngrams"])


@router.get("/frequency")
def get_ngram_frequency(
    n: int = Query(..., ge=2, le=4, description="N-gram大小 (2=bigram, 3=trigram)"),
    run_id: str = Query("ngram_001", description="N-gram分析运行ID"),
    top_k: int = Query(100, ge=1, le=1000, description="返回前K个n-grams"),
    min_frequency: Optional[int] = Query(None, ge=1, description="最小频次过滤"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取全局N-gram频率
    Get global n-gram frequencies

    Args:
        n: N-gram大小 (2, 3, 或 4)
        run_id: N-gram分析运行ID
        top_k: 返回前K个高频n-grams
        min_frequency: 最小频次阈值（可选）

    Returns:
        List[dict]: N-gram频率列表
    """
    query = """
        SELECT
            ngram,
            frequency,
            village_count
        FROM ngram_frequency
        WHERE run_id = ? AND n = ?
    """
    params = [run_id, n]

    # 现场过滤：最小频次
    if min_frequency is not None:
        query += " AND frequency >= ?"
        params.append(min_frequency)

    query += " ORDER BY frequency DESC LIMIT ?"
    params.append(top_k)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No {n}-grams found for run_id: {run_id}"
        )

    return results


@router.get("/regional")
def get_regional_ngram_frequency(
    n: int = Query(..., ge=2, le=4, description="N-gram大小"),
    run_id: str = Query("ngram_001", description="N-gram分析运行ID"),
    region_level: str = Query(..., description="区域级别", pattern="^(city|county|township)$"),
    region_name: Optional[str] = Query(None, description="区域名称（不指定返回所有区域）"),
    top_k: int = Query(50, ge=1, le=500, description="每个区域返回前K个n-grams"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取区域N-gram频率
    Get regional n-gram frequencies

    Args:
        n: N-gram大小
        run_id: N-gram分析运行ID
        region_level: 区域级别 (city/county/township)
        region_name: 区域名称（可选）
        top_k: 每个区域返回前K个n-grams

    Returns:
        List[dict]: 区域N-gram频率列表
    """
    query = """
        SELECT
            region_name,
            ngram,
            frequency,
            rank_within_region as rank
        FROM regional_ngram_frequency
        WHERE run_id = ? AND n = ? AND region_level = ?
    """
    params = [run_id, n, region_level]

    # 现场过滤：区域名称
    if region_name is not None:
        query += " AND region_name = ?"
        params.append(region_name)

    # 现场排序和限制（每个区域前K个）
    query += " AND rank_within_region <= ? ORDER BY region_name, rank_within_region"
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
    run_id: str = Query("ngram_001", description="N-gram分析运行ID"),
    pattern_type: Optional[str] = Query(None, description="模式类型过滤"),
    min_frequency: Optional[int] = Query(None, ge=1, description="最小频次过滤"),
    limit: int = Query(100, ge=1, le=500, description="返回记录数"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取结构化命名模式
    Get structural naming patterns

    Args:
        run_id: N-gram分析运行ID
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
            example_villages
        FROM structural_patterns
        WHERE run_id = ?
    """
    params = [run_id]

    # 现场过滤：模式类型
    if pattern_type is not None:
        query += " AND pattern_type = ?"
        params.append(pattern_type)

    # 现场过滤：最小频次
    if min_frequency is not None:
        query += " AND frequency >= ?"
        params.append(min_frequency)

    query += " ORDER BY frequency DESC LIMIT ?"
    params.append(limit)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No structural patterns found for run_id: {run_id}"
        )

    return results


@router.get("/tendency")
def get_ngram_tendency(
    ngram: Optional[str] = Query(None, description="N-gram"),
    region_level: str = Query("county", description="区域级别"),
    min_tendency: Optional[float] = Query(None, description="最小倾向值"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取N-gram倾向性
    Get n-gram tendency scores
    """
    query = """
        SELECT
            region_level,
            region_name,
            ngram,
            n,
            tendency_score,
            frequency,
            expected_frequency
        FROM ngram_tendency
        WHERE region_level = ?
    """
    params = [region_level]

    if ngram is not None:
        query += " AND ngram = ?"
        params.append(ngram)

    if min_tendency is not None:
        query += " AND tendency_score >= ?"
        params.append(min_tendency)

    query += " ORDER BY tendency_score DESC LIMIT ?"
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
    region_level: str = Query("county", description="区域级别"),
    is_significant: Optional[bool] = Query(None, description="仅显示显著结果"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取N-gram显著性
    Get n-gram significance test results
    """
    query = """
        SELECT
            region_level,
            region_name,
            ngram,
            n,
            z_score,
            p_value,
            is_significant,
            lift
        FROM ngram_significance
        WHERE region_level = ?
    """
    params = [region_level]

    if ngram is not None:
        query += " AND ngram = ?"
        params.append(ngram)

    if is_significant is not None:
        query += " AND is_significant = ?"
        params.append(1 if is_significant else 0)

    query += " ORDER BY ABS(z_score) DESC LIMIT ?"
    params.append(limit)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No n-gram significance data found"
        )

    return results
