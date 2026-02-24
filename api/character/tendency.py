"""
字符倾向性API
Character Tendency API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import sqlite3

from ..dependencies import get_db, execute_query
from ..config import DEFAULT_RUN_ID
from ..models import CharTendency, CharTendencyByRegion

router = APIRouter(prefix="/character/tendency", tags=["character"])


@router.get("/by-region", response_model=List[CharTendency])
def get_character_tendency_by_region(
    region_level: str = Query(..., description="区域级别", pattern="^(city|county|township)$"),
    region_name: Optional[str] = Query(None, description="区域名称（可选，用于向后兼容）"),
    city: Optional[str] = Query(None, description="市级（可选）"),
    county: Optional[str] = Query(None, description="区县级（可选）"),
    township: Optional[str] = Query(None, description="乡镇级（可选）"),
    top_n: int = Query(50, ge=1, le=500, description="返回前N个字符"),
    sort_by: str = Query("z_score", description="排序字段", pattern="^(z_score|lift|log_odds)$"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取指定区域的字符倾向性（支持层级查询）
    Get character tendency for a specific region with hierarchical filtering

    支持两种查询方式：
    1. 层级查询：使用 city/county/township 参数精确指定位置
    2. 名称查询：使用 region_name 参数（可能返回多个重复地名的数据）

    Args:
        region_level: 区域级别 (city/county/township)
        region_name: 区域名称（可选，向后兼容）
        city: 市级名称（可选）
        county: 区县级名称（可选）
        township: 乡镇级名称（可选）
        top_n: 返回前N个高倾向字符
        sort_by: 排序字段 (z_score/lift/log_odds)

    Returns:
        List[CharTendency]: 字符倾向性列表

    Examples:
        # 精确查询特定位置
        ?region_level=township&city=清远市&county=清新区&township=太平镇&top_n=50

        # 查询所有同名地点
        ?region_level=township&region_name=太平镇&top_n=50
    """
    query = f"""
        SELECT
            city,
            county,
            township,
            region_name,
            char as character,
            lift,
            log_odds,
            z_score,
            ROW_NUMBER() OVER (ORDER BY {sort_by} DESC) as rank
        FROM char_regional_analysis
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

    query += f" ORDER BY {sort_by} DESC LIMIT ?"
    params.append(top_n)

    results = execute_query(db, query, tuple(params))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No data found"
        )

    return results


@router.get("/by-char", response_model=List[CharTendencyByRegion])
def get_character_tendency_by_char(
    character: str = Query(..., description="字符", min_length=1, max_length=1),
    region_level: str = Query(..., description="区域级别", pattern="^(city|county|township)$"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    获取指定字符在各区域的倾向性（支持层级显示）
    Get tendency of a specific character across regions with hierarchical information

    Args:
        character: 字符
        region_level: 区域级别 (city/county/township)

    Returns:
        List[CharTendencyByRegion]: 各区域倾向性列表（包含层级信息）
    """
    query = """
        SELECT
            city,
            county,
            township,
            region_name,
            lift,
            z_score
        FROM char_regional_analysis
        WHERE char = ? AND region_level = ?
        ORDER BY z_score DESC
    """

    results = execute_query(db, query, (character, region_level))

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for character: {character}"
        )

    return results
