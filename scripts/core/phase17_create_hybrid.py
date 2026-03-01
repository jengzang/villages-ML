#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 17: 生成智能混合版本词典

策略：
1. 姓氏优先：李、黄、杨、武等 → 采用 LLM 的 clan 标注
2. 数字修正：六、七、八、九、十 → 保留 v3 的 number_large
3. 其他情况：根据语义合理性判断

作者：Claude Code
日期：2026-02-25
"""

import json
import time
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent.parent
LEXICON_V3_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v3_expanded.json"
LEXICON_V4_LLM_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v4_pilot.json"
LEXICON_V4_HYBRID_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v4_hybrid.json"
REPORT_V2_PATH = PROJECT_ROOT / "docs" / "reports" / "PHASE_17_LLM_VALIDATION_REPORT_V2.md"


def load_lexicon(path: Path):
    """加载词典"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_hybrid_lexicon():
    """创建智能混合版本词典"""
    print("=" * 60)
    print("创建智能混合版本词典")
    print("=" * 60)

    # 加载 v3 和 v4_llm
    v3 = load_lexicon(LEXICON_V3_PATH)
    v4_llm = load_lexicon(LEXICON_V4_LLM_PATH)

    # 构建字符到子类别的映射
    v3_char_to_subcat = {}
    for subcat, chars in v3["categories"].items():
        for char in chars:
            v3_char_to_subcat[char] = subcat

    v4_llm_char_to_subcat = {}
    for subcat, chars in v4_llm["subcategories"].items():
        for char in chars:
            v4_llm_char_to_subcat[char] = subcat

    # 定义混合规则
    hybrid_rules = {
        # 1. 姓氏优先（LLM 更准确）
        "李": ("clan_li", "LLM", "在村名中更可能是姓氏而非水果"),
        "黄": ("clan_huang", "LLM", "在村名中更可能是姓氏而非颜色"),
        "杨": ("clan_other", "LLM", "在村名中更可能是姓氏而非植物"),
        "武": ("clan_wu", "LLM", "在村名中更可能是姓氏而非美德"),
        "高": ("clan_other", "LLM", "在村名中更可能是姓氏而非大小"),
        "郭": ("clan_other", "LLM", "在村名中更可能是姓氏而非堡垒"),

        # 2. 数字修正（v3 更准确）
        "六": ("number_large", "v3", "数值大于5应为 large"),
        "七": ("number_large", "v3", "数值大于5应为 large"),
        "八": ("number_large", "v3", "数值大于5应为 large"),
        "九": ("number_large", "v3", "数值大于5应为 large"),
        "十": ("number_large", "v3", "数值大于5应为 large"),
        "二": ("number_small", "v3", "数值小于等于5应为 small"),

        # 3. 跨类别合理调整
        "港": ("water_port", "v3", "在村名中主要指水运港口"),
        "堤": ("agriculture_irrigation", "v3", "堤坝主要用于农业水利"),
        "圳": ("water_stream", "v3", "圳在广东指水渠"),
        "渠": ("agriculture_irrigation", "LLM", "渠主要用于农业灌溉"),
        "坝": ("agriculture_irrigation", "v3", "坝主要用于农业水利"),
        "畔": ("agriculture_field", "v3", "畔指田边"),

        # 4. 象征类细分
        "堂": ("symbolic_religion", "v3", "堂多指祠堂、庙堂"),
        "灵": ("symbolic_religion", "v3", "灵多指神灵"),
        "圣": ("symbolic_virtue", "v3", "圣指圣贤美德"),

        # 5. 方位类细分
        "前": ("direction_horizontal", "v3", "前后是水平方位"),
        "后": ("direction_horizontal", "v3", "前后是水平方位"),
        "左": ("direction_horizontal", "v3", "左右是水平方位"),
        "右": ("direction_horizontal", "v3", "左右是水平方位"),

        # 6. 山地类细分（保留 v3）
        "岭": ("mountain_peak", "v3", "岭通常指山峰"),
        "岗": ("mountain_slope", "v3", "岗通常指山坡"),
        "冈": ("mountain_slope", "v3", "冈通常指山坡"),
        "坳": ("mountain_slope", "v3", "坳通常指山坡凹处"),
        "坎": ("mountain_slope", "v3", "坎通常指山坡"),

        # 7. 水系类细分（保留 v3）
        "溪": ("water_river", "v3", "溪是小河流"),
        "涧": ("water_river", "v3", "涧是山间小河"),
        "浦": ("water_bay", "v3", "浦指水湾"),
        "滘": ("water_bay", "v3", "滘在广东指水湾"),
        "濠": ("water_bay", "v3", "濠指护城河或水湾"),

        # 8. 聚落类细分
        "里": ("direction_inside", "v3", "里主要表示方位"),
        "巷": ("infrastructure_road", "v3", "巷是道路"),
        "街": ("infrastructure_road", "v3", "街是道路"),
        "亭": ("infrastructure_station", "v3", "亭是驿站建筑"),

        # 9. 其他合理调整
        "金": ("color", "v3", "金在村名中多指颜色"),
        "银": ("color", "v3", "银在村名中多指颜色"),
        "铁": ("infrastructure_transport", "v3", "铁多指交通设施"),
        "平": ("shape", "v3", "平指形状"),
        "直": ("shape", "v3", "直指形状"),
        "方": ("shape", "v3", "方指形状"),
        "尖": ("shape", "v3", "尖指形状"),
    }

    # 创建混合词典
    hybrid_subcategories = defaultdict(list)
    decisions = []

    # 获取所有唯一字符
    all_chars = set(v3_char_to_subcat.keys()) | set(v4_llm_char_to_subcat.keys())

    for char in sorted(all_chars):
        v3_subcat = v3_char_to_subcat.get(char)
        llm_subcat = v4_llm_char_to_subcat.get(char)

        # 应用混合规则
        if char in hybrid_rules:
            chosen_subcat, source, reason = hybrid_rules[char]
            decisions.append({
                "char": char,
                "v3": v3_subcat,
                "llm": llm_subcat,
                "chosen": chosen_subcat,
                "source": source,
                "reason": reason
            })
        elif v3_subcat == llm_subcat:
            # 两者一致，使用任一
            chosen_subcat = v3_subcat
            decisions.append({
                "char": char,
                "v3": v3_subcat,
                "llm": llm_subcat,
                "chosen": chosen_subcat,
                "source": "both",
                "reason": "LLM 与 v3 一致"
            })
        elif llm_subcat is None:
            # 仅 v3 有标注
            chosen_subcat = v3_subcat
            decisions.append({
                "char": char,
                "v3": v3_subcat,
                "llm": None,
                "chosen": chosen_subcat,
                "source": "v3",
                "reason": "仅 v3 标注"
            })
        elif v3_subcat is None:
            # 仅 LLM 有标注
            chosen_subcat = llm_subcat
            decisions.append({
                "char": char,
                "v3": None,
                "llm": llm_subcat,
                "chosen": chosen_subcat,
                "source": "LLM",
                "reason": "仅 LLM 标注"
            })
        else:
            # 两者不一致，默认使用 v3（更保守）
            chosen_subcat = v3_subcat
            decisions.append({
                "char": char,
                "v3": v3_subcat,
                "llm": llm_subcat,
                "chosen": chosen_subcat,
                "source": "v3",
                "reason": "默认保留 v3（未在规则中指定）"
            })

        hybrid_subcategories[chosen_subcat].append(char)

    # 创建 v4_hybrid 词典
    v4_hybrid = {
        "version": "4.0.0-hybrid",
        "created_at": time.strftime("%Y-%m-%d"),
        "description": "Hybrid semantic lexicon combining LLM validation and v3 expertise",
        "subcategories": dict(hybrid_subcategories),
        "metadata": {
            "base_v3": str(LEXICON_V3_PATH),
            "base_llm": str(LEXICON_V4_LLM_PATH),
            "total_chars": len(all_chars),
            "hybrid_rules": len(hybrid_rules),
            "llm_adopted": sum(1 for d in decisions if d["source"] == "LLM"),
            "v3_retained": sum(1 for d in decisions if d["source"] == "v3"),
            "both_agreed": sum(1 for d in decisions if d["source"] == "both"),
        }
    }

    # 保存混合词典
    with open(LEXICON_V4_HYBRID_PATH, 'w', encoding='utf-8') as f:
        json.dump(v4_hybrid, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 混合词典已创建：{LEXICON_V4_HYBRID_PATH}")
    print(f"   - {len(v4_hybrid['subcategories'])} 个子类别")
    print(f"   - {sum(len(chars) for chars in v4_hybrid['subcategories'].values())} 个字符")
    print(f"\n决策统计：")
    print(f"   - LLM 采用：{v4_hybrid['metadata']['llm_adopted']} 个字符")
    print(f"   - v3 保留：{v4_hybrid['metadata']['v3_retained']} 个字符")
    print(f"   - 两者一致：{v4_hybrid['metadata']['both_agreed']} 个字符")

    # 生成决策报告
    report_path = PROJECT_ROOT / "docs" / "reports" / "PHASE_17_HYBRID_DECISIONS.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Phase 17: 智能混合决策报告\n\n")
        f.write(f"**生成时间：** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        f.write("## 决策统计\n\n")
        f.write(f"- **总字符数**：{len(all_chars)} 个\n")
        f.write(f"- **LLM 采用**：{v4_hybrid['metadata']['llm_adopted']} 个字符\n")
        f.write(f"- **v3 保留**：{v4_hybrid['metadata']['v3_retained']} 个字符\n")
        f.write(f"- **两者一致**：{v4_hybrid['metadata']['both_agreed']} 个字符\n")
        f.write(f"- **混合规则**：{len(hybrid_rules)} 条\n\n")

        f.write("---\n\n")
        f.write("## 关键决策（应用混合规则）\n\n")
        f.write("| 字符 | v3 标注 | LLM 标注 | 最终选择 | 来源 | 理由 |\n")
        f.write("|------|---------|----------|----------|------|------|\n")

        for d in decisions:
            if d["char"] in hybrid_rules:
                f.write(f"| {d['char']} | {d['v3'] or 'N/A'} | {d['llm'] or 'N/A'} | {d['chosen']} | {d['source']} | {d['reason']} |\n")

        f.write("\n---\n\n")
        f.write("## 不一致但未指定规则（默认保留 v3）\n\n")
        f.write("| 字符 | v3 标注 | LLM 标注 | 最终选择 |\n")
        f.write("|------|---------|----------|----------|\n")

        for d in decisions:
            if d["char"] not in hybrid_rules and d["v3"] and d["llm"] and d["v3"] != d["llm"]:
                f.write(f"| {d['char']} | {d['v3']} | {d['llm']} | {d['chosen']} |\n")

    print(f"\n[OK] 决策报告已生成：{report_path}")

    return v4_hybrid


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Phase 17: 智能混合词典生成")
    print("=" * 60)

    start_time = time.time()

    v4_hybrid = create_hybrid_lexicon()

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[OK] 智能混合完成！")
    print(f"[TIME] 总耗时：{elapsed:.2f} 秒")
    print("=" * 60)

    print("\n下一步：")
    print("1. 查看混合词典：data/semantic_lexicon_v4_hybrid.json")
    print("2. 查看决策报告：docs/reports/PHASE_17_HYBRID_DECISIONS.md")
    print("3. 运行 phase17_semantic_subcategory.py 更新数据库")


if __name__ == "__main__":
    main()
