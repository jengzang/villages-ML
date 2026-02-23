"""
Region Similarity API Endpoints

Provides endpoints for querying region similarity metrics.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import sqlite3
import json

router = APIRouter(prefix="/regions", tags=["regions"])

DB_PATH = "data/villages.db"


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


@router.get("/similarity/search")
async def search_similar_regions(
    region: str = Query(..., description="目标区域名称"),
    top_k: int = Query(10, ge=1, le=50, description="返回相似区域数量"),
    metric: str = Query("cosine", regex="^(cosine|jaccard)$", description="相似度指标"),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0, description="最小相似度阈值")
):
    """
    查找与目标区域相似的其他区域

    Find regions similar to a target region.

    Args:
        region: Target region name
        top_k: Number of similar regions to return (1-50)
        metric: Similarity metric ('cosine' or 'jaccard')
        min_similarity: Minimum similarity threshold (0.0-1.0)

    Returns:
        List of similar regions with scores and common characters
    """
    conn = get_db()
    cursor = conn.cursor()

    # Determine which similarity column to use
    sim_column = f"{metric}_similarity"

    # Query similar regions (check both region1 and region2)
    query = f"""
    SELECT
        CASE
            WHEN region1 = ? THEN region2
            ELSE region1
        END as similar_region,
        {sim_column} as similarity,
        common_high_tendency_chars,
        CASE
            WHEN region1 = ? THEN distinctive_chars_r2
            ELSE distinctive_chars_r1
        END as distinctive_chars
    FROM region_similarity
    WHERE (region1 = ? OR region2 = ?)
    AND {sim_column} >= ?
    ORDER BY {sim_column} DESC
    LIMIT ?
    """

    cursor.execute(query, (region, region, region, region, min_similarity, top_k))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found or no similar regions")

    results = []
    for row in rows:
        results.append({
            "region": row[0],
            "similarity": round(row[1], 4),
            "common_chars": json.loads(row[2]) if row[2] else [],
            "distinctive_chars": json.loads(row[3]) if row[3] else []
        })

    return {
        "target_region": region,
        "metric": metric,
        "count": len(results),
        "similar_regions": results
    }


@router.get("/similarity/pair")
async def get_pair_similarity(
    region1: str = Query(..., description="区域1名称"),
    region2: str = Query(..., description="区域2名称")
):
    """
    获取两个区域之间的相似度指标

    Get similarity metrics between two specific regions.

    Args:
        region1: First region name
        region2: Second region name

    Returns:
        All similarity metrics, common chars, and distinctive chars
    """
    conn = get_db()
    cursor = conn.cursor()

    # Query (handle both orderings)
    query = """
    SELECT
        region1, region2,
        cosine_similarity, jaccard_similarity, euclidean_distance,
        common_high_tendency_chars,
        distinctive_chars_r1, distinctive_chars_r2,
        feature_dimension
    FROM region_similarity
    WHERE (region1 = ? AND region2 = ?) OR (region1 = ? AND region2 = ?)
    """

    cursor.execute(query, (region1, region2, region2, region1))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Similarity data not found for regions '{region1}' and '{region2}'"
        )

    # Determine correct ordering
    r1_is_first = (row[0] == region1)

    return {
        "region1": region1,
        "region2": region2,
        "cosine_similarity": round(row[2], 4),
        "jaccard_similarity": round(row[3], 4),
        "euclidean_distance": round(row[4], 4),
        "common_chars": json.loads(row[5]) if row[5] else [],
        "distinctive_chars_r1": json.loads(row[6] if r1_is_first else row[7]) if row[6] else [],
        "distinctive_chars_r2": json.loads(row[7] if r1_is_first else row[6]) if row[7] else [],
        "feature_dimension": row[8]
    }


@router.get("/similarity/matrix")
async def get_similarity_matrix(
    regions: Optional[str] = Query(None, description="逗号分隔的区域名称列表"),
    metric: str = Query("cosine", regex="^(cosine|jaccard)$", description="相似度指标")
):
    """
    获取多个区域的相似度矩阵

    Get similarity matrix for multiple regions.

    Args:
        regions: Comma-separated region names (optional, default: top 20 by village count)
        metric: Similarity metric ('cosine' or 'jaccard')

    Returns:
        Similarity matrix as 2D array with region labels
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get region list
    if regions:
        region_list = [r.strip() for r in regions.split(',')]
    else:
        # Get top 20 regions by village count
        cursor.execute("""
        SELECT region_name, COUNT(*) as count
        FROM 广东省自然村_预处理
        GROUP BY region_name
        ORDER BY count DESC
        LIMIT 20
        """)
        region_list = [row[0] for row in cursor.fetchall()]

    if not region_list:
        raise HTTPException(status_code=400, detail="No regions specified")

    # Build similarity matrix
    n = len(region_list)
    matrix = [[0.0] * n for _ in range(n)]

    sim_column = f"{metric}_similarity"

    for i, r1 in enumerate(region_list):
        for j, r2 in enumerate(region_list):
            if i == j:
                matrix[i][j] = 1.0
            elif i < j:
                # Query database
                cursor.execute(f"""
                SELECT {sim_column}
                FROM region_similarity
                WHERE (region1 = ? AND region2 = ?) OR (region1 = ? AND region2 = ?)
                """, (r1, r2, r2, r1))
                row = cursor.fetchone()
                if row:
                    matrix[i][j] = round(row[0], 4)
                    matrix[j][i] = round(row[0], 4)

    conn.close()

    return {
        "regions": region_list,
        "metric": metric,
        "matrix": matrix
    }


@router.get("/list")
async def list_regions(
    region_level: str = Query("county", description="区域级别")
):
    """
    获取所有可用区域列表

    Get list of all available regions.

    Args:
        region_level: Region level (default: 'county')

    Returns:
        List of region names with village counts
    """
    conn = get_db()
    cursor = conn.cursor()

    # Map region_level to column name
    level_map = {
        "city": "市级",
        "county": "区县级",
        "township": "乡镇级"
    }

    column = level_map.get(region_level, "区县级")

    cursor.execute(f"""
    SELECT {column} as region_name, COUNT(*) as village_count
    FROM 广东省自然村_预处理
    GROUP BY {column}
    ORDER BY village_count DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return {
        "region_level": region_level,
        "count": len(rows),
        "regions": [
            {"region_name": row[0], "village_count": row[1]}
            for row in rows
        ]
    }
