#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新生成 spatial_tendency_integration 表

改进点：
1. 扩展字符范围：从5个扩展到45个
2. 使用新的空间聚类：spatial_hdbscan_v1
3. 改进显著性检验：使用 Mann-Whitney U test + FDR 校正
4. 添加字符分类维度
5. 添加对比分析字段
"""

import sqlite3
import time
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

# 推荐的45个字符（方案A）
SELECTED_CHARACTERS = [
    # 优先级1：核心高频字符（15个）
    '村', '屋', '围', '岗', '里', '寨', '南', '坡',
    '塘', '下', '坑', '山', '头', '上', '垌',
    # 优先级2：高频+区域倾向（15个）
    '园', '楼', '湖', '仔', '西', '新', '大', '子',
    '田', '岭', '龙', '水', '东', '尾', '黄',
    # 优先级3：语义代表字符（15个）
    '竹', '安', '边', '旺', '前', '一', '美', '二',
    '队', '北', '顶', '埇', '埔', '庄', '蔡'
]

# 字符语义分类
CHARACTER_CATEGORIES = {
    # 聚落
    'settlement': ['村', '屋', '围', '寨', '头', '楼', '尾', '庄'],
    # 地形地貌
    'terrain': ['山', '岗', '坑', '坡', '岭', '顶'],
    # 水系
    'water': ['塘', '水', '湖', '埇'],
    # 方位
    'direction': ['上', '下', '东', '西', '南', '北', '前', '边'],
    # 植物
    'vegetation': ['竹'],
    # 宗族
    'clan': ['黄', '蔡'],
    # 农业
    'agriculture': ['田', '园', '垌', '埔'],
    # 规模/修饰
    'modifier': ['新', '大', '里', '仔', '子', '旺', '安', '美', '一', '二', '队'],
    # 象征
    'symbolic': ['龙']
}

def get_character_category(char):
    """获取字符的语义类别"""
    for category, chars in CHARACTER_CATEGORIES.items():
        if char in chars:
            return category
    return 'other'

def calculate_mann_whitney_u(cluster_values, global_values):
    """
    使用 Mann-Whitney U test 检验聚类内倾向性是否显著不同于全局

    Returns:
        u_statistic, p_value
    """
    try:
        if len(cluster_values) < 3 or len(global_values) < 3:
            return None, 1.0

        u_stat, p_val = stats.mannwhitneyu(
            cluster_values,
            global_values,
            alternative='two-sided'
        )
        return u_stat, p_val
    except Exception as e:
        print(f"[WARNING] Mann-Whitney U test failed: {e}")
        return None, 1.0

def regenerate_spatial_tendency_integration():
    """重新生成 spatial_tendency_integration 表"""

    # 可配置的空间聚类 run_id
    SPATIAL_RUN_ID = 'spatial_hdbscan_v1'  # 使用 HDBSCAN 聚类（7213个聚类，平均27.7个村庄）

    print("=" * 80)
    print("重新生成 spatial_tendency_integration 表")
    print("=" * 80)
    print(f"字符数量: {len(SELECTED_CHARACTERS)}")
    print(f"空间聚类: {SPATIAL_RUN_ID}")
    print(f"显著性检验: Mann-Whitney U test + FDR correction")
    print()

    conn = sqlite3.connect('data/villages.db')
    cursor = conn.cursor()

    # Step 1: 删除旧表并创建新表
    print("Step 1: 创建新表结构...")
    cursor.execute('DROP TABLE IF EXISTS spatial_tendency_integration')
    cursor.execute('''
        CREATE TABLE spatial_tendency_integration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            tendency_run_id TEXT NOT NULL,
            spatial_run_id TEXT NOT NULL,

            -- 分析维度
            character TEXT NOT NULL,
            character_category TEXT,
            cluster_id INTEGER NOT NULL,

            -- 倾向性指标
            cluster_tendency_mean REAL,
            cluster_tendency_std REAL,
            global_tendency_mean REAL,
            tendency_deviation REAL,
            n_villages_with_char INTEGER,

            -- 空间指标
            cluster_size INTEGER,
            centroid_lon REAL,
            centroid_lat REAL,
            avg_distance_km REAL,
            spatial_coherence REAL,
            spatial_specificity REAL,

            -- 地理信息
            dominant_city TEXT,
            dominant_county TEXT,

            -- 统计显著性
            is_significant INTEGER,
            p_value REAL,
            u_statistic REAL,

            -- 元数据
            created_at REAL NOT NULL
        )
    ''')
    print("[OK] 表结构创建完成")

    # Step 2: 获取全局倾向性数据
    print("\nStep 2: 加载全局倾向性数据...")
    cursor.execute('''
        SELECT char, frequency
        FROM char_frequency_global
        WHERE char IN ({})
    '''.format(','.join(['?'] * len(SELECTED_CHARACTERS))), SELECTED_CHARACTERS)

    global_tendency = {}
    for char, freq in cursor.fetchall():
        global_tendency[char] = freq

    print(f"[OK] 加载了 {len(global_tendency)} 个字符的全局倾向性")

    # Step 3: 获取空间聚类信息
    print("\nStep 3: 加载空间聚类信息...")
    cursor.execute('''
        SELECT cluster_id, cluster_size, centroid_lon, centroid_lat,
               avg_distance_km, dominant_city, dominant_county
        FROM spatial_clusters
        WHERE run_id = ?
        ORDER BY cluster_id
    ''', (SPATIAL_RUN_ID,))

    clusters = {}
    for row in cursor.fetchall():
        cluster_id, size, lon, lat, dist, city, county = row
        clusters[cluster_id] = {
            'size': size,
            'centroid_lon': lon,
            'centroid_lat': lat,
            'avg_distance_km': dist,
            'dominant_city': city,
            'dominant_county': county
        }

    print(f"[OK] 加载了 {len(clusters)} 个空间聚类")

    # Step 4: 获取每个聚类中的村庄
    print("\nStep 4: 加载聚类-村庄映射...")
    cursor.execute('''
        SELECT cluster_id, village_id
        FROM village_cluster_assignments
        WHERE run_id = ?
    ''', (SPATIAL_RUN_ID,))

    cluster_villages = {}
    for cluster_id, village_id in cursor.fetchall():
        if cluster_id not in cluster_villages:
            cluster_villages[cluster_id] = []
        cluster_villages[cluster_id].append(village_id)

    total_villages = sum(len(v) for v in cluster_villages.values())
    print(f"[OK] 加载了 {total_villages} 个村庄的聚类分配")

    # Step 5: 计算每个字符在每个聚类中的倾向性
    print("\nStep 5: 计算字符-聚类倾向性...")

    records = []
    p_values_for_correction = []

    for char_idx, char in enumerate(SELECTED_CHARACTERS, 1):
        print(f"  处理字符 {char_idx}/{len(SELECTED_CHARACTERS)}: {char}")

        # 获取包含该字符的所有村庄
        # 注意：village_spatial_features 使用 village_id (如 "v_1")
        # 而不是 ROWID，所以需要转换
        cursor.execute('''
            SELECT 'v_' || ROWID as village_id
            FROM 广东省自然村_预处理
            WHERE 字符集 LIKE ?
        ''', (f'%"{char}"%',))

        villages_with_char = set(row[0] for row in cursor.fetchall())

        for cluster_id in clusters.keys():
            if cluster_id not in cluster_villages:
                continue

            cluster_info = clusters[cluster_id]
            villages_in_cluster = set(cluster_villages[cluster_id])

            # 聚类中包含该字符的村庄数
            n_villages_with_char = len(villages_in_cluster & villages_with_char)

            # 聚类内倾向性
            cluster_tendency = n_villages_with_char / len(villages_in_cluster) if len(villages_in_cluster) > 0 else 0

            # 全局倾向性
            global_tend = global_tendency.get(char, 0)

            # 倾向性偏差
            tendency_deviation = cluster_tendency - global_tend

            # 空间特异性（归一化的倾向性偏差）
            spatial_specificity = abs(tendency_deviation) / (global_tend + 0.001)

            # 显著性检验（稍后批量进行FDR校正）
            # 这里先计算 p-value
            cluster_values = [1] * n_villages_with_char + [0] * (len(villages_in_cluster) - n_villages_with_char)
            global_values = [1] * len(villages_with_char) + [0] * (total_villages - len(villages_with_char))

            u_stat, p_val = calculate_mann_whitney_u(cluster_values, global_values)

            record = {
                'character': char,
                'character_category': get_character_category(char),
                'cluster_id': cluster_id,
                'cluster_tendency_mean': cluster_tendency,
                'cluster_tendency_std': 0,  # 简化处理
                'global_tendency_mean': global_tend,
                'tendency_deviation': tendency_deviation,
                'n_villages_with_char': n_villages_with_char,
                'cluster_size': cluster_info['size'],
                'centroid_lon': cluster_info['centroid_lon'],
                'centroid_lat': cluster_info['centroid_lat'],
                'avg_distance_km': cluster_info['avg_distance_km'],
                'spatial_coherence': 1.0 / (cluster_info['avg_distance_km'] + 0.1),  # 简化计算
                'spatial_specificity': spatial_specificity,
                'dominant_city': cluster_info['dominant_city'],
                'dominant_county': cluster_info['dominant_county'],
                'p_value': p_val,
                'u_statistic': u_stat if u_stat is not None else 0
            }

            records.append(record)
            p_values_for_correction.append(p_val)

    print(f"[OK] 生成了 {len(records)} 条记录")

    # Step 6: FDR 校正
    print("\nStep 6: 进行 FDR 多重检验校正...")
    if len(p_values_for_correction) > 0:
        reject, pvals_corrected, _, _ = multipletests(
            p_values_for_correction,
            alpha=0.05,
            method='fdr_bh'
        )

        for i, record in enumerate(records):
            record['is_significant'] = 1 if reject[i] else 0
            record['p_value'] = pvals_corrected[i]

        n_significant = sum(reject)
        print(f"[OK] FDR 校正完成，{n_significant}/{len(records)} 条记录显著 ({n_significant*100/len(records):.1f}%)")

    # Step 7: 插入数据
    print("\nStep 7: 插入数据到数据库...")

    run_id = f'integration_{SPATIAL_RUN_ID}_001'
    tendency_run_id = 'freq_final_001'
    spatial_run_id = SPATIAL_RUN_ID
    created_at = time.time()

    for record in records:
        cursor.execute('''
            INSERT INTO spatial_tendency_integration (
                run_id, tendency_run_id, spatial_run_id,
                character, character_category, cluster_id,
                cluster_tendency_mean, cluster_tendency_std,
                global_tendency_mean, tendency_deviation,
                n_villages_with_char, cluster_size,
                centroid_lon, centroid_lat, avg_distance_km,
                spatial_coherence, spatial_specificity,
                dominant_city, dominant_county,
                is_significant, p_value, u_statistic,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run_id, tendency_run_id, spatial_run_id,
            record['character'], record['character_category'], record['cluster_id'],
            record['cluster_tendency_mean'], record['cluster_tendency_std'],
            record['global_tendency_mean'], record['tendency_deviation'],
            record['n_villages_with_char'], record['cluster_size'],
            record['centroid_lon'], record['centroid_lat'], record['avg_distance_km'],
            record['spatial_coherence'], record['spatial_specificity'],
            record['dominant_city'], record['dominant_county'],
            record['is_significant'], record['p_value'], record['u_statistic'],
            created_at
        ))

    conn.commit()
    print(f"[OK] 插入了 {len(records)} 条记录")

    # Step 8: 创建索引
    print("\nStep 8: 创建索引...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sti_character ON spatial_tendency_integration(character)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sti_cluster ON spatial_tendency_integration(cluster_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sti_category ON spatial_tendency_integration(character_category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sti_significant ON spatial_tendency_integration(is_significant)')
    print("[OK] 索引创建完成")

    # Step 9: 生成统计报告
    print("\n" + "=" * 80)
    print("统计报告")
    print("=" * 80)

    cursor.execute('SELECT COUNT(*) FROM spatial_tendency_integration')
    total_records = cursor.fetchone()[0]
    print(f"总记录数: {total_records}")

    cursor.execute('SELECT COUNT(*) FROM spatial_tendency_integration WHERE is_significant = 1')
    significant_records = cursor.fetchone()[0]
    print(f"显著记录数: {significant_records} ({significant_records*100/total_records:.1f}%)")

    cursor.execute('''
        SELECT character_category, COUNT(*) as count
        FROM spatial_tendency_integration
        GROUP BY character_category
        ORDER BY count DESC
    ''')
    print("\n按语义类别分布:")
    for category, count in cursor.fetchall():
        print(f"  {category}: {count} 条记录")

    cursor.execute('''
        SELECT character, COUNT(*) as count, SUM(is_significant) as sig_count
        FROM spatial_tendency_integration
        GROUP BY character
        ORDER BY sig_count DESC
        LIMIT 10
    ''')
    print("\n显著性最高的10个字符:")
    for char, count, sig_count in cursor.fetchall():
        print(f"  {char}: {sig_count}/{count} 显著 ({sig_count*100/count:.1f}%)")

    conn.close()

    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)

if __name__ == "__main__":
    regenerate_spatial_tendency_integration()
