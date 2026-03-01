#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 17: LLM 辅助语义子类别验证（改进版）

使用 DeepSeek LLM 对 v3_expanded 中的所有字符进行子类别标注验证。

改进：
- 直接基于 v3_expanded 的完整类别体系
- 让 LLM 从所有可能的子类别中选择
- 覆盖所有 331 个字符

作者：Claude Code
日期：2026-02-25
"""

import os
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "villages.db"
LEXICON_V3_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v3_expanded.json"
LEXICON_V4_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v4_pilot.json"

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


def load_lexicon(path: Path) -> Dict:
    """加载语义词典"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def call_deepseek_api(prompt: str, max_retries: int = 3) -> Optional[str]:
    """调用 DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        print("[ERROR] DEEPSEEK_API_KEY not found in .env file")
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"[WARNING] API failed (attempt {attempt + 1}/{max_retries}): {response.status_code}")
                time.sleep(2 ** attempt)

        except Exception as e:
            print(f"[ERROR] API exception (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)

    return None


def create_subcategory_prompt_v2(char: str, all_subcategories: List[str]) -> str:
    """
    创建子类别标注的 prompt（改进版）

    让 LLM 从所有可能的子类别中选择，而不是限定在某个父类别内
    """
    # 按父类别分组显示
    grouped = defaultdict(list)
    for subcat in all_subcategories:
        if "_" in subcat:
            parent = subcat.split("_")[0]
            grouped[parent].append(subcat)
        else:
            grouped["other"].append(subcat)

    subcats_str = ""
    for parent, subcats in sorted(grouped.items()):
        subcats_str += f"\n{parent.upper()}:\n"
        for sc in subcats:
            subcats_str += f"  - {sc}\n"

    prompt = f"""你是一个专业的语言学家，专门研究中国地名命名规律。

任务：为广东省自然村名中的字符"{char}"分配一个最合适的子类别。

可选的子类别（共 {len(all_subcategories)} 个）：
{subcats_str}

请分析字符"{char}"在村名中的最常见语义，选择最合适的子类别。

要求：
1. 只返回一个子类别名称（英文，如 mountain_peak）
2. 选择最常见、最典型的语义
3. 不要添加任何解释或额外文字

你的答案："""

    return prompt


def label_character_with_llm_v2(char: str, all_subcategories: List[str]) -> Optional[str]:
    """使用 LLM 为字符标注子类别（改进版）"""
    prompt = create_subcategory_prompt_v2(char, all_subcategories)
    response = call_deepseek_api(prompt)

    if response:
        response = response.strip().lower()
        # 检查响应是否在子类别列表中
        if response in [sc.lower() for sc in all_subcategories]:
            return response
        else:
            print(f"[WARNING] LLM returned invalid subcategory: {response}")
            return None

    return None


def llm_label_all_characters_v2(v3: Dict) -> Dict:
    """
    使用 LLM 标注所有字符（改进版）

    直接基于 v3 的完整类别体系
    """
    print("\n" + "=" * 60)
    print("Step 1: 使用 LLM 标注所有字符（基于 v3 完整类别）")
    print("=" * 60)

    # 获取所有子类别
    all_subcategories = list(v3["categories"].keys())
    print(f"\n可选子类别：{len(all_subcategories)} 个")

    # 构建字符到原始子类别的映射
    char_to_v3_subcat = {}
    for subcat, chars in v3["categories"].items():
        for char in chars:
            char_to_v3_subcat[char] = subcat

    # 获取所有唯一字符
    all_chars = list(char_to_v3_subcat.keys())
    print(f"总字符数：{len(all_chars)} 个")

    llm_labels = {}
    processed = 0

    for char in all_chars:
        processed += 1
        v3_subcat = char_to_v3_subcat[char]
        print(f"  [{processed}/{len(all_chars)}] 标注字符：{char} (v3={v3_subcat}) ... ", end="", flush=True)

        subcategory = label_character_with_llm_v2(char, all_subcategories)

        if subcategory:
            llm_labels[char] = {
                "subcategory": subcategory,
                "v3_subcategory": v3_subcat,
                "match": (subcategory == v3_subcat),
                "confidence": 1.0,
                "method": "llm"
            }
            status = "[OK]" if subcategory == v3_subcat else "[DIFF]"
            print(f"{status} {subcategory}")
        else:
            print("[FAILED]")

        # 避免 API 限流
        time.sleep(0.5)

    matches = sum(1 for label in llm_labels.values() if label["match"])
    print(f"\n[OK] 已标注 {len(llm_labels)}/{len(all_chars)} 个字符")
    print(f"匹配率：{matches}/{len(llm_labels)} ({matches/len(llm_labels)*100:.1f}%)")

    return llm_labels


def generate_validation_report_v2(llm_labels: Dict, output_path: Path):
    """生成验证报告（改进版）"""
    print("\n" + "=" * 60)
    print("Step 2: 生成验证报告")
    print("=" * 60)

    report = []
    report.append("# Phase 17: LLM 子类别标注验证报告（改进版）\n")
    report.append(f"**生成时间：** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("**改进：** 基于 v3_expanded 的完整类别体系（75 个子类别）\n")
    report.append("---\n\n")

    # 统计信息
    total = len(llm_labels)
    matches = sum(1 for label in llm_labels.values() if label["match"])
    mismatches = total - matches

    report.append("## 总体统计\n\n")
    report.append(f"- **总字符数**：{total} 个\n")
    report.append(f"- **匹配**：{matches} 个字符\n")
    report.append(f"- **不匹配**：{mismatches} 个字符\n")
    report.append(f"- **准确率**：{matches/total*100:.1f}%\n")
    report.append("\n---\n\n")

    # 不匹配的字符
    report.append("## 不匹配的字符\n\n")
    report.append("| 字符 | LLM 标注 | v3 标注 | 说明 |\n")
    report.append("|------|----------|---------|------|\n")

    mismatched_chars = [(char, data) for char, data in llm_labels.items() if not data["match"]]
    mismatched_chars.sort(key=lambda x: x[1]["subcategory"])

    for char, data in mismatched_chars:
        llm_subcat = data["subcategory"]
        v3_subcat = data["v3_subcategory"]

        # 判断是否跨父类别
        llm_parent = llm_subcat.split("_")[0] if "_" in llm_subcat else llm_subcat
        v3_parent = v3_subcat.split("_")[0] if "_" in v3_subcat else v3_subcat

        if llm_parent != v3_parent:
            note = "跨类别"
        else:
            note = "同类别内"

        report.append(f"| {char} | {llm_subcat} | {v3_subcat} | {note} |\n")

    report.append("\n---\n\n")

    # 按父类别统计准确率
    report.append("## 按父类别统计准确率\n\n")
    report.append("| 父类别 | 总字符数 | 匹配数 | 准确率 |\n")
    report.append("|--------|----------|--------|--------|\n")

    parent_stats = defaultdict(lambda: {"total": 0, "matches": 0})
    for char, data in llm_labels.items():
        v3_parent = data["v3_subcategory"].split("_")[0] if "_" in data["v3_subcategory"] else data["v3_subcategory"]
        parent_stats[v3_parent]["total"] += 1
        if data["match"]:
            parent_stats[v3_parent]["matches"] += 1

    for parent, stats in sorted(parent_stats.items()):
        total = stats["total"]
        matches = stats["matches"]
        accuracy = matches / total * 100 if total > 0 else 0
        report.append(f"| {parent} | {total} | {matches} | {accuracy:.1f}% |\n")

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"[OK] 验证报告已保存：{output_path}")


def update_v4_lexicon_with_llm_v2(llm_labels: Dict, v3: Dict):
    """基于 LLM 标注更新 v4 词典（改进版）"""
    print("\n" + "=" * 60)
    print("Step 3: 更新 v4_pilot 词典")
    print("=" * 60)

    # 创建新的 v4 词典
    v4 = {
        "version": "4.0.0-pilot-llm-v2",
        "created_at": time.strftime("%Y-%m-%d"),
        "description": "Pilot semantic lexicon with LLM validation (based on v3 complete categories)",
        "subcategories": defaultdict(list),
        "metadata": {
            "llm_model": "deepseek-chat",
            "validation_date": time.strftime("%Y-%m-%d"),
            "total_chars": len(llm_labels),
            "matches": sum(1 for label in llm_labels.values() if label["match"]),
            "mismatches": sum(1 for label in llm_labels.values() if not label["match"]),
            "accuracy": sum(1 for label in llm_labels.values() if label["match"]) / len(llm_labels) * 100
        }
    }

    # 填充子类别（优先使用 LLM 标注）
    for char, data in llm_labels.items():
        subcategory = data["subcategory"]
        v4["subcategories"][subcategory].append(char)

    # 转换为普通字典
    v4["subcategories"] = dict(v4["subcategories"])

    # 保存 v4 词典
    with open(LEXICON_V4_PATH, 'w', encoding='utf-8') as f:
        json.dump(v4, f, ensure_ascii=False, indent=2)

    print(f"[OK] v4_pilot 词典已更新：{LEXICON_V4_PATH}")
    print(f"   - {len(v4['subcategories'])} 个子类别")
    print(f"   - {sum(len(chars) for chars in v4['subcategories'].values())} 个字符")
    print(f"   - 准确率：{v4['metadata']['accuracy']:.1f}%")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Phase 17: LLM 辅助语义子类别验证（改进版）")
    print("=" * 60)
    print(f"词典 v3：{LEXICON_V3_PATH}")
    print(f"词典 v4：{LEXICON_V4_PATH}")
    print(f"LLM 模型：DeepSeek Chat")
    print(f"改进：基于 v3 的完整类别体系（75 个子类别）")
    print("=" * 60)

    if not DEEPSEEK_API_KEY:
        print("\n[ERROR] DEEPSEEK_API_KEY not found in .env file")
        return

    start_time = time.time()

    # 加载 v3 词典
    v3 = load_lexicon(LEXICON_V3_PATH)

    # Step 1: LLM 标注
    llm_labels = llm_label_all_characters_v2(v3)

    # Step 2: 生成报告
    report_path = PROJECT_ROOT / "docs" / "reports" / "PHASE_17_LLM_VALIDATION_REPORT_V2.md"
    generate_validation_report_v2(llm_labels, report_path)

    # Step 3: 更新 v4 词典
    update_v4_lexicon_with_llm_v2(llm_labels, v3)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[OK] LLM 验证完成（改进版）！")
    print(f"[TIME] 总耗时：{elapsed:.2f} 秒")
    print("=" * 60)

    print("\n下一步：")
    print(f"1. 查看验证报告：{report_path}")
    print(f"2. 查看更新后的词典：{LEXICON_V4_PATH}")
    print("3. 人工审核不匹配的字符")
    print("4. 重新运行 phase17_semantic_subcategory.py 更新数据库")


if __name__ == "__main__":
    main()
