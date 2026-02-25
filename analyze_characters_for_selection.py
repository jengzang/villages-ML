#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析字符，为 spatial_tendency_integration 表选择合适的字符
"""

import sqlite3
import json
from collections import defaultdict

def analyze_characters():
    conn = sqlite3.connect('data/villages.db')
    cursor = conn.cursor()

    # 1. 高频字符（TOP 50）
    print("=" * 80)
    print("1. 高频字符 TOP 50")
    print("=" * 80)
    cursor.execute('''
        SELECT DISTINCT char, village_count, frequency, rank
        FROM char_frequency_global
        WHERE rank <= 50
        ORDER BY rank
    ''')
    high_freq_chars = {}
    for char, count, freq, rank in cursor.fetchall():
        if char not in high_freq_chars:
            high_freq_chars[char] = {
                'village_count': count,
                'frequency': freq,
                'rank': rank,
                'category': 'high_frequency'
            }
            print(f"{rank:2d}. {char} - {count:5d} 村庄 ({freq*100:.2f}%)")

    # 2. 区域倾向性强的字符
    print("\n" + "=" * 80)
    print("2. 具有强区域倾向性的字符（lift > 1.5, 至少100个村庄）")
    print("=" * 80)
    cursor.execute('''
        SELECT char, MAX(ABS(lift)) as max_lift,
               MAX(village_count) as max_count,
               COUNT(DISTINCT region_name) as num_regions
        FROM char_regional_analysis
        WHERE ABS(lift) > 1.5 AND village_count >= 100
        GROUP BY char
        HAVING num_regions >= 3
        ORDER BY max_lift DESC
        LIMIT 50
    ''')
    regional_chars = {}
    for char, lift, count, regions in cursor.fetchall():
        regional_chars[char] = {
            'max_lift': lift,
            'max_count': count,
            'num_regions': regions,
            'category': 'regional_tendency'
        }
        print(f"{char} - lift={lift:.2f}, 最多{count}村庄, {regions}个区域")

    # 3. 语义类别统计
    print("\n" + "=" * 80)
    print("3. 语义类别分布")
    print("=" * 80)
    cursor.execute('''
        SELECT category, vtf_count, frequency, rank
        FROM semantic_vtf_global
        ORDER BY rank
    ''')
    semantic_categories = {}
    for cat, count, freq, rank in cursor.fetchall():
        semantic_categories[cat] = {
            'vtf_count': count,
            'frequency': freq,
            'rank': rank
        }
        print(f"{rank}. {cat}: {count} 村庄 ({freq*100:.2f}%)")

    # 4. 根据语义类别获取代表字符
    print("\n" + "=" * 80)
    print("4. 按语义类别选择代表字符")
    print("=" * 80)

    # 定义语义类别到字符的映射（基于文档和常识）
    semantic_char_mapping = {
        'settlement': ['村', '庄', '寨', '围', '堡', '厝', '屋', '楼', '头', '尾'],
        'direction': ['东', '西', '南', '北', '上', '下', '前', '后', '左', '右', '中'],
        'mountain': ['山', '岭', '岗', '坡', '坑', '峰', '岩', '崖', '嶂'],
        'water': ['水', '河', '江', '湖', '塘', '涌', '溪', '泉', '海', '港', '洲', '沙'],
        'vegetation': ['竹', '松', '榕', '樟', '梅', '柳', '桃', '李', '杨', '柏'],
        'clan': ['陈', '李', '王', '张', '刘', '黄', '林', '吴', '周', '郑'],
        'symbolic': ['龙', '凤', '虎', '狮', '鹤', '鹿', '马', '牛'],
        'agriculture': ['田', '园', '场', '坝', '埔', '畲', '垌'],
        'infrastructure': ['桥', '路', '街', '巷', '门', '关', '站']
    }

    semantic_chars = {}
    for category, chars in semantic_char_mapping.items():
        print(f"\n【{category}】")
        for char in chars:
            if char in high_freq_chars:
                info = high_freq_chars[char]
                semantic_chars[char] = {**info, 'semantic_category': category}
                print(f"  {char} - 排名{info['rank']}, {info['village_count']}村庄")

    # 5. 综合评分选择字符
    print("\n" + "=" * 80)
    print("5. 综合评分与推荐")
    print("=" * 80)

    all_chars = {}

    # 合并所有字符信息
    for char, info in high_freq_chars.items():
        all_chars[char] = info.copy()
        all_chars[char]['score'] = 0
        all_chars[char]['reasons'] = []

    for char, info in regional_chars.items():
        if char not in all_chars:
            all_chars[char] = {
                'village_count': info['max_count'],
                'frequency': 0,
                'rank': 999,
                'category': 'regional_tendency',
                'score': 0,
                'reasons': []
            }
        all_chars[char]['max_lift'] = info['max_lift']
        all_chars[char]['num_regions'] = info['num_regions']

    for char, info in semantic_chars.items():
        if char in all_chars:
            all_chars[char]['semantic_category'] = info['semantic_category']

    # 计算综合评分
    for char, info in all_chars.items():
        score = 0
        reasons = []

        # 高频字符加分
        if info['rank'] <= 10:
            score += 10
            reasons.append(f"TOP10高频(排名{info['rank']})")
        elif info['rank'] <= 30:
            score += 5
            reasons.append(f"TOP30高频(排名{info['rank']})")
        elif info['rank'] <= 50:
            score += 3
            reasons.append(f"TOP50高频(排名{info['rank']})")

        # 区域倾向性加分
        if 'max_lift' in info:
            if info['max_lift'] > 10:
                score += 10
                reasons.append(f"强区域倾向(lift={info['max_lift']:.1f})")
            elif info['max_lift'] > 5:
                score += 7
                reasons.append(f"中等区域倾向(lift={info['max_lift']:.1f})")
            elif info['max_lift'] > 2:
                score += 5
                reasons.append(f"弱区域倾向(lift={info['max_lift']:.1f})")

        # 语义类别加分
        if 'semantic_category' in info:
            score += 3
            reasons.append(f"语义类别:{info['semantic_category']}")

        all_chars[char]['score'] = score
        all_chars[char]['reasons'] = reasons

    # 按评分排序
    sorted_chars = sorted(all_chars.items(), key=lambda x: x[1]['score'], reverse=True)

    print("\n综合评分 TOP 50:")
    print(f"{'排名':<4} {'字符':<4} {'评分':<6} {'村庄数':<8} {'频率':<8} {'原因'}")
    print("-" * 80)
    for i, (char, info) in enumerate(sorted_chars[:50], 1):
        reasons_str = "; ".join(info['reasons'])
        print(f"{i:<4} {char:<4} {info['score']:<6} {info['village_count']:<8} "
              f"{info['frequency']*100:>6.2f}% {reasons_str}")

    # 6. 按类别推荐
    print("\n" + "=" * 80)
    print("6. 按类别推荐字符")
    print("=" * 80)

    recommendations = {
        '核心高频字符（必选）': [],
        '地形地貌字符': [],
        '水系字符': [],
        '方位字符': [],
        '聚落字符': [],
        '植物字符': [],
        '宗族字符': [],
        '区域特征字符': []
    }

    for char, info in sorted_chars:
        if info['score'] >= 15:
            recommendations['核心高频字符（必选）'].append(char)

        if 'semantic_category' in info:
            cat = info['semantic_category']
            if cat == 'mountain' and len(recommendations['地形地貌字符']) < 10:
                recommendations['地形地貌字符'].append(char)
            elif cat == 'water' and len(recommendations['水系字符']) < 10:
                recommendations['水系字符'].append(char)
            elif cat == 'direction' and len(recommendations['方位字符']) < 10:
                recommendations['方位字符'].append(char)
            elif cat == 'settlement' and len(recommendations['聚落字符']) < 10:
                recommendations['聚落字符'].append(char)
            elif cat == 'vegetation' and len(recommendations['植物字符']) < 8:
                recommendations['植物字符'].append(char)
            elif cat == 'clan' and len(recommendations['宗族字符']) < 8:
                recommendations['宗族字符'].append(char)

        if 'max_lift' in info and info['max_lift'] > 10:
            if len(recommendations['区域特征字符']) < 15:
                recommendations['区域特征字符'].append(char)

    for category, chars in recommendations.items():
        print(f"\n【{category}】({len(chars)}个)")
        print(", ".join(chars))

    # 7. 最终推荐列表
    print("\n" + "=" * 80)
    print("7. 最终推荐字符列表（按优先级）")
    print("=" * 80)

    final_recommendations = []

    # 优先级1: 核心高频字符（评分>=15）
    tier1 = [char for char, info in sorted_chars if info['score'] >= 15]
    final_recommendations.extend(tier1[:15])

    # 优先级2: 高频+区域倾向性（评分10-14）
    tier2 = [char for char, info in sorted_chars if 10 <= info['score'] < 15]
    final_recommendations.extend(tier2[:15])

    # 优先级3: 语义代表字符（评分5-9）
    tier3 = [char for char, info in sorted_chars if 5 <= info['score'] < 10]
    final_recommendations.extend(tier3[:20])

    # 去重
    final_recommendations = list(dict.fromkeys(final_recommendations))

    print(f"\n推荐选择 {len(final_recommendations)} 个字符:")
    print("\n优先级1（核心高频，15个）:")
    print(", ".join(final_recommendations[:15]))
    print("\n优先级2（高频+区域倾向，15个）:")
    print(", ".join(final_recommendations[15:30]))
    print("\n优先级3（语义代表，20个）:")
    print(", ".join(final_recommendations[30:50]))

    print(f"\n总计: {len(final_recommendations)} 个字符")

    # 保存到JSON文件
    output = {
        'final_recommendations': final_recommendations,
        'tier1': final_recommendations[:15],
        'tier2': final_recommendations[15:30],
        'tier3': final_recommendations[30:50],
        'all_chars_with_scores': {char: info for char, info in sorted_chars[:100]},
        'recommendations_by_category': recommendations
    }

    with open('character_selection_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n分析结果已保存到: character_selection_analysis.json")

    conn.close()

if __name__ == "__main__":
    analyze_characters()
