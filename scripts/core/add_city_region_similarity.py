"""
补充 region_similarity 表的市级（city）数据

使用与 phase15 完全相同的算法和 RegionSimilarityAnalyzer，
只是将 region_level 从 'county' 改为 'city'。

预期输出：21 × 20 / 2 = 210 条记录
"""

import sqlite3
import time
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.region_similarity import RegionSimilarityAnalyzer

DB_PATH = project_root / "data" / "villages.db"
REGION_LEVEL = 'city'


def main():
    print("=" * 60)
    print("补充市级区域相似度数据")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查是否已有市级数据
    cursor.execute(
        "SELECT COUNT(*) FROM region_similarity WHERE region_level = ?",
        (REGION_LEVEL,)
    )
    existing = cursor.fetchone()[0]
    if existing > 0:
        print(f"[INFO] 已存在 {existing} 条市级数据，先删除...")
        cursor.execute(
            "DELETE FROM region_similarity WHERE region_level = ?",
            (REGION_LEVEL,)
        )
        conn.commit()

    analyzer = RegionSimilarityAnalyzer(str(DB_PATH))

    print("\n[Step 1] 加载市级字符数据...")
    df = analyzer.load_regional_data(
        region_level=REGION_LEVEL,
        top_k_global=100,
        z_score_threshold=2.0
    )
    print(f"  字符-区域记录数: {len(df)}")
    print(f"  特征字符数: {len(analyzer.feature_chars)}")

    print("\n[Step 2] 构建特征向量...")
    feature_matrix = analyzer.build_feature_vectors(df)
    print(f"  特征矩阵: {feature_matrix.shape}")
    print(f"  市级区域数: {len(analyzer.region_names)}")

    print("\n[Step 3] 计算相似度...")
    cosine_matrix = analyzer.compute_cosine_similarity()
    jaccard_matrix = analyzer.compute_jaccard_similarity(df, z_score_threshold=2.0)
    euclidean_matrix = analyzer.compute_euclidean_distance()

    print("\n[Step 4] 生成相似度记录...")
    records = analyzer.generate_similarity_pairs(
        cosine_matrix,
        jaccard_matrix,
        euclidean_matrix,
        df,
        REGION_LEVEL
    )
    print(f"  生成 {len(records)} 条记录（预期 210 条）")

    print("\n[Step 5] 写入数据库...")
    created_at = time.time()
    for record in records:
        cursor.execute("""
        INSERT INTO region_similarity (
            region_level, region1, region2,
            cosine_similarity, jaccard_similarity, euclidean_distance,
            common_high_tendency_chars, distinctive_chars_r1, distinctive_chars_r2,
            feature_dimension, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record['region_level'],
            record['region1'],
            record['region2'],
            record['cosine_similarity'],
            record['jaccard_similarity'],
            record['euclidean_distance'],
            record['common_high_tendency_chars'],
            record['distinctive_chars_r1'],
            record['distinctive_chars_r2'],
            record['feature_dimension'],
            created_at
        ))

    conn.commit()
    print(f"  已写入 {len(records)} 条")

    print("\n[Step 6] 验证结果...")
    cursor.execute("""
        SELECT region_level, COUNT(*) as pairs,
               ROUND(AVG(cosine_similarity), 4) as avg_cosine,
               ROUND(MIN(cosine_similarity), 4) as min_cosine,
               ROUND(MAX(cosine_similarity), 4) as max_cosine
        FROM region_similarity
        GROUP BY region_level
    """)
    print(f"\n{'层级':<10} {'对数':<8} {'平均余弦':<12} {'最小':<10} {'最大':<10}")
    print("-" * 55)
    for row in cursor.fetchall():
        print(f"{row[0]:<10} {row[1]:<8} {row[2]:<12} {row[3]:<10} {row[4]:<10}")

    print("\n[Top 5 最相似的市级对]")
    cursor.execute("""
        SELECT region1, region2, cosine_similarity, jaccard_similarity
        FROM region_similarity
        WHERE region_level = 'city'
        ORDER BY cosine_similarity DESC
        LIMIT 5
    """)
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {row[0]} <-> {row[1]}: cosine={row[2]:.4f}, jaccard={row[3]:.4f}")

    conn.close()
    print("\n[OK] 完成")


if __name__ == "__main__":
    main()
