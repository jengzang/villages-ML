"""
村庄级别数据API
Village-level Data API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import sqlite3

from ..dependencies import get_db, execute_query, execute_single

router = APIRouter(prefix="/village", tags=["village-data"])


@router.get("/ngrams/{village_id}")
def get_village_ngrams(
    village_id: str,
    n: Optional[int] = Query(None, ge=2, le=4, description="N-gram长度"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取特定村庄的N-gram
    Get n-grams for a specific village

    Args:
        village_id: 村庄ID
        n: N-gram长度（2-4）

    Returns:
        dict: 村庄N-gram信息
    """
    query = """
        SELECT
            village_id,
            village_name,
            bigrams,
            trigrams,
            quadgrams
        FROM village_ngrams
        WHERE village_id = ?
    """

    result = execute_single(db, query, (village_id,))

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Village {village_id} not found"
        )

    # Filter by n if specified
    if n is not None:
        if n == 2:
            result = {k: v for k, v in result.items() if k in ['village_id', 'village_name', 'bigrams']}
        elif n == 3:
            result = {k: v for k, v in result.items() if k in ['village_id', 'village_name', 'trigrams']}
        elif n == 4:
            result = {k: v for k, v in result.items() if k in ['village_id', 'village_name', 'quadgrams']}

    return result


@router.get("/semantic-structure/{village_id}")
def get_village_semantic_structure(
    village_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取特定村庄的语义结构
    Get semantic structure for a specific village

    Args:
        village_id: 村庄ID

    Returns:
        dict: 村庄语义结构
    """
    query = """
        SELECT
            village_id,
            village_name,
            semantic_categories,
            category_count,
            dominant_category,
            semantic_diversity,
            structure_pattern
        FROM village_semantic_structure
        WHERE village_id = ?
    """

    result = execute_single(db, query, (village_id,))

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Village {village_id} not found"
        )

    return result


@router.get("/features/{village_id}")
def get_village_features(
    village_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取特定村庄的特征向量
    Get feature vector for a specific village

    Args:
        village_id: 村庄ID

    Returns:
        dict: 村庄特征
    """
    query = """
        SELECT *
        FROM village_features
        WHERE village_id = ?
    """

    result = execute_single(db, query, (village_id,))

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Village {village_id} not found"
        )

    return result


@router.get("/spatial-features/{village_id}")
def get_village_spatial_features(
    village_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取特定村庄的空间特征
    Get spatial features for a specific village

    Args:
        village_id: 村庄ID

    Returns:
        dict: 村庄空间特征
    """
    query = """
        SELECT
            village_id,
            village_name,
            longitude,
            latitude,
            nearest_neighbors,
            avg_distance_to_neighbors,
            density_score,
            cluster_id,
            is_core_point
        FROM village_spatial_features
        WHERE village_id = ?
    """

    result = execute_single(db, query, (village_id,))

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Village {village_id} not found"
        )

    return result


@router.get("/complete/{village_id}")
def get_village_complete_profile(
    village_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取村庄的完整档案（所有数据）
    Get complete profile for a village (all available data)

    Args:
        village_id: 村庄ID

    Returns:
        dict: 村庄完整档案
    """
    # Get basic info
    basic_query = """
        SELECT *
        FROM 广东省自然村_预处理
        WHERE village_id = ?
    """
    basic_info = execute_single(db, basic_query, (village_id,))

    if not basic_info:
        raise HTTPException(
            status_code=404,
            detail=f"Village {village_id} not found"
        )

    # Get spatial features
    spatial_query = """
        SELECT *
        FROM village_spatial_features
        WHERE village_id = ?
    """
    spatial_features = execute_single(db, spatial_query, (village_id,))

    # Get semantic structure
    semantic_query = """
        SELECT *
        FROM village_semantic_structure
        WHERE village_id = ?
    """
    semantic_structure = execute_single(db, semantic_query, (village_id,))

    # Get n-grams
    ngrams_query = """
        SELECT *
        FROM village_ngrams
        WHERE village_id = ?
    """
    ngrams = execute_single(db, ngrams_query, (village_id,))

    return {
        "basic_info": basic_info,
        "spatial_features": spatial_features,
        "semantic_structure": semantic_structure,
        "ngrams": ngrams
    }
