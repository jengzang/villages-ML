#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取分析结果用于中文展示文档
Extract analysis results for Chinese showcase document
"""

import sqlite3
import pandas as pd
import json
from pathlib import Path

def safe_query(conn, query, params=None, description=""):
    """安全执行查询，如果失败返回空列表"""
    try:
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        return df.to_dict('records') if len(df) > 0 else []
    except Exception as e:
        print(f"  警告: {description} 查询失败 - {str(e)}")
        return []

def main():
    conn = sqlite3.connect('data/villages.db')
    results = {}

    # 1. 数据概览
    print("提取数据概览...")
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM 广东省自然村')
    total_villages = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM 广东省自然村_预处理 WHERE 有效=1')
    valid_villages = cursor.fetchone()[0]

    results['overview'] = {
        'total_villages': total_villages,
        'valid_villages': valid_villages,
        'preprocessed_count': total_villages - valid_villages
    }

    # 2. 全局高频字符 Top 20
    print("提取全局高频字符...")
    results['global_top_chars'] = safe_query(conn, '''
        SELECT char, frequency, village_count
        FROM char_frequency_global
        ORDER BY frequency DESC
        LIMIT 20
    ''', description="全局高频字符")

    # 3. 区域倾向性 - 各城市高倾向字符
    print("提取区域倾向性...")
    cities = ['广州市', '深圳市', '汕头市', '佛山市', '韶关市', '湛江市', '梅州市']
    results['regional_tendency'] = {}

    for city in cities:
        data = safe_query(conn, '''
            SELECT char, lift, log_lift, frequency, village_count, z_score
            FROM regional_tendency
            WHERE region_name = ? AND region_level = 'city'
            ORDER BY lift DESC
            LIMIT 10
        ''', params=(city,), description=f"{city}倾向性")
        if data:
            results['regional_tendency'][city] = data

    # 4. 字符相似性示例
    print("提取字符相似性...")
    test_chars = ['山', '水', '村', '围', '寨', '坑', '岗']
    results['char_similarity'] = {}

    for char in test_chars:
        data = safe_query(conn, '''
            SELECT char2 as similar_char, cosine_similarity
            FROM char_similarity
            WHERE char1 = ?
            ORDER BY cosine_similarity DESC
            LIMIT 15
        ''', params=(char,), description=f"字符{char}相似性")
        if data:
            results['char_similarity'][char] = data

    # 5. 聚类结果
    print("提取聚类结果...")
    results['clustering_metrics'] = safe_query(conn, '''
        SELECT algorithm, k, silhouette_score, davies_bouldin_index
        FROM clustering_metrics
        ORDER BY silhouette_score DESC
    ''', description="聚类指标")

    # 6. 聚类大小
    print("提取聚类大小...")
    results['cluster_sizes'] = safe_query(conn, '''
        SELECT cluster_id, COUNT(*) as village_count
        FROM cluster_assignments
        WHERE algorithm = 'kmeans'
        GROUP BY cluster_id
        ORDER BY cluster_id
    ''', description="聚类大小")

    # 7. N-gram模式
    print("提取N-gram模式...")
    results['top_bigrams'] = safe_query(conn, '''
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE ngram_type = 'bigram'
        ORDER BY frequency DESC
        LIMIT 20
    ''', description="高频bigram")

    results['top_trigrams'] = safe_query(conn, '''
        SELECT ngram, frequency
        FROM ngram_frequency
        WHERE ngram_type = 'trigram'
        ORDER BY frequency DESC
        LIMIT 20
    ''', description="高频trigram")

    # 8. 语义标签统计
    print("提取语义标签...")
    results['semantic_labels'] = safe_query(conn, '''
        SELECT label as semantic_label, COUNT(*) as count
        FROM semantic_indices
        GROUP BY label
        ORDER BY count DESC
    ''', description="语义标签")

    # 9. 统计显著性 - 高显著性字符
    print("提取统计显著性...")
    results['high_significance'] = safe_query(conn, '''
        SELECT region_name, char, z_score, lift
        FROM regional_tendency
        WHERE region_level = 'city' AND ABS(z_score) > 10
        ORDER BY ABS(z_score) DESC
        LIMIT 30
    ''', description="高显著性字符")

    # 10. 前缀清理统计
    print("提取前缀清理统计...")
    results['prefix_stats'] = safe_query(conn, '''
        SELECT 市级, COUNT(*) as count
        FROM 广东省自然村_预处理
        WHERE 前缀 IS NOT NULL AND 前缀 != ''
        GROUP BY 市级
        ORDER BY count DESC
    ''', description="前缀清理统计")

    conn.close()

    # 保存结果
    output_file = 'docs/analysis_results_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 结果已保存到: {output_file}")
    print(f"[OK] 包含 {len(results)} 个分析维度的数据")

    # 打印摘要
    print("\n数据摘要:")
    for key, value in results.items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)} 条记录")
        elif isinstance(value, dict):
            if key == 'overview':
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {len(value)} 个子项")

if __name__ == '__main__':
    main()
