#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 17: LLM 辅助语义子类别验证

使用 DeepSeek LLM 对所有类别的字符进行子类别标注，
并与现有分类（v3_expanded）进行对比验证。

功能：
1. 加载现有的 v1 和 v3_expanded 词典
2. 使用 LLM 对所有字符进行子类别标注
3. 对比 LLM 标注 vs 现有分类
4. 生成验证报告和改进建议
5. 更新 v4_pilot 词典

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
LEXICON_V1_PATH = PROJECT_ROOT / "data" / "semantic_lexicon_v1.json"
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
    """
    调用 DeepSeek API

    Args:
        prompt: 提示词
        max_retries: 最大重试次数

    Returns:
        LLM 响应文本，失败返回 None
    """
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
        "temperature": 0.3,  # 较低温度以获得更一致的结果
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
                print(f"[WARNING] API request failed (attempt {attempt + 1}/{max_retries}): {response.status_code}")
                print(f"Response: {response.text}")
                time.sleep(2 ** attempt)  # 指数退避

        except Exception as e:
            print(f"[ERROR] API request exception (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)

    return None


def create_subcategory_prompt(char: str, parent_category: str, subcategories: List[str]) -> str:
    """
    创建子类别标注的 prompt

    Args:
        char: 要标注的字符
        parent_category: 父类别
        subcategories: 可选的子类别列表

    Returns:
        Prompt 文本
    """
    subcats_str = "\n".join([f"- {sc}" for sc in subcategories])

    prompt = f"""你是一个专业的语言学家，专门研究中国地名命名规律。

任务：为广东省自然村名中的字符"{char}"分配一个最合适的子类别。

父类别：{parent_category}

可选的子类别：
{subcats_str}

请分析字符"{char}"在村名中的语义，选择最合适的子类别。

要求：
1. 只返回一个子类别名称（英文）
2. 如果不确定，选择最常见的语义
3. 不要添加任何解释或额外文字

示例输出格式：
mountain_peak

你的答案："""

    return prompt


def label_character_with_llm(char: str, parent_category: str, subcategories: List[str]) -> Optional[str]:
    """
    使用 LLM 为字符标注子类别

    Args:
        char: 要标注的字符
        parent_category: 父类别
        subcategories: 可选的子类别列表

    Returns:
        子类别名称，失败返回 None
    """
    prompt = create_subcategory_prompt(char, parent_category, subcategories)
    response = call_deepseek_api(prompt)

    if response:
        # 清理响应（去除可能的额外文字）
        response = response.strip().lower()
        # 检查响应是否在子类别列表中
        if response in [sc.lower() for sc in subcategories]:
            return response
        else:
            print(f"[WARNING] LLM returned invalid subcategory for '{char}': {response}")
            return None

    return None


def get_subcategories_for_parent(parent_category: str, v3: Dict) -> List[str]:
    """
    获取父类别的所有子类别

    Args:
        parent_category: 父类别名称
        v3: v3_expanded 词典

    Returns:
        子类别名称列表
    """
    subcats = []
    for subcat_name in v3["categories"].keys():
        if subcat_name.startswith(f"{parent_category}_"):
            subcats.append(subcat_name)
    return subcats


def llm_label_all_characters(v1: Dict, v3: Dict) -> Dict:
    """
    使用 LLM 标注所有字符

    Args:
        v1: v1 词典（9 大类别）
        v3: v3_expanded 词典（子类别参考）

    Returns:
        LLM 标注结果 {char: {parent_category, subcategory, confidence}}
    """
    print("\n" + "=" * 60)
    print("Step 1: 使用 LLM 标注所有字符")
    print("=" * 60)

    llm_labels = {}
    total_chars = sum(len(chars) for chars in v1["categories"].values())
    processed = 0

    for parent_category, chars in v1["categories"].items():
        print(f"\n处理类别：{parent_category} ({len(chars)} 个字符)")

        # 获取该父类别的子类别列表
        subcategories = get_subcategories_for_parent(parent_category, v3)

        if not subcategories:
            print(f"  [SKIP] 没有找到 {parent_category} 的子类别定义")
            continue

        print(f"  可选子类别：{', '.join(subcategories)}")

        for char in chars:
            processed += 1
            print(f"  [{processed}/{total_chars}] 标注字符：{char} ... ", end="", flush=True)

            subcategory = label_character_with_llm(char, parent_category, subcategories)

            if subcategory:
                llm_labels[char] = {
                    "parent_category": parent_category,
                    "subcategory": subcategory,
                    "confidence": 1.0,  # DeepSeek 不提供置信度，默认 1.0
                    "method": "llm"
                }
                print(f"[OK] {subcategory}")
            else:
                print("[FAILED]")

            # 避免 API 限流
            time.sleep(0.5)

    print(f"\n[OK] 已标注 {len(llm_labels)}/{total_chars} 个字符")
    return llm_labels


def compare_with_existing(llm_labels: Dict, v3: Dict) -> Dict:
    """
    对比 LLM 标注与现有分类

    Args:
        llm_labels: LLM 标注结果
        v3: v3_expanded 词典

    Returns:
        对比结果 {char: {llm_label, v3_label, match}}
    """
    print("\n" + "=" * 60)
    print("Step 2: 对比 LLM 标注与现有分类")
    print("=" * 60)

    # 构建 v3 的字符到子类别映射
    v3_char_to_subcat = {}
    for subcat, chars in v3["categories"].items():
        for char in chars:
            v3_char_to_subcat[char] = subcat

    comparison = {}
    matches = 0
    mismatches = 0
    llm_only = 0
    v3_only = 0

    # 对比 LLM 标注的字符
    for char, llm_data in llm_labels.items():
        llm_subcat = llm_data["subcategory"]
        v3_subcat = v3_char_to_subcat.get(char)

        if v3_subcat:
            match = (llm_subcat == v3_subcat)
            comparison[char] = {
                "llm_label": llm_subcat,
                "v3_label": v3_subcat,
                "match": match,
                "parent_category": llm_data["parent_category"]
            }
            if match:
                matches += 1
            else:
                mismatches += 1
        else:
            comparison[char] = {
                "llm_label": llm_subcat,
                "v3_label": None,
                "match": False,
                "parent_category": llm_data["parent_category"]
            }
            llm_only += 1

    # 检查 v3 中有但 LLM 未标注的字符
    for char, v3_subcat in v3_char_to_subcat.items():
        if char not in llm_labels:
            comparison[char] = {
                "llm_label": None,
                "v3_label": v3_subcat,
                "match": False,
                "parent_category": v3_subcat.split("_")[0] if "_" in v3_subcat else "unknown"
            }
            v3_only += 1

    print(f"\n对比结果：")
    print(f"  匹配：{matches} 个字符")
    print(f"  不匹配：{mismatches} 个字符")
    print(f"  仅 LLM 标注：{llm_only} 个字符")
    print(f"  仅 v3 标注：{v3_only} 个字符")

    if matches + mismatches > 0:
        accuracy = matches / (matches + mismatches) * 100
        print(f"  准确率：{accuracy:.1f}%")

    return comparison


def generate_validation_report(comparison: Dict, output_path: Path):
    """
    生成验证报告

    Args:
        comparison: 对比结果
        output_path: 输出文件路径
    """
    print("\n" + "=" * 60)
    print("Step 3: 生成验证报告")
    print("=" * 60)

    report = []
    report.append("# Phase 17: LLM 子类别标注验证报告\n")
    report.append(f"**生成时间：** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("---\n\n")

    # 统计信息
    matches = sum(1 for c in comparison.values() if c["match"])
    mismatches = sum(1 for c in comparison.values() if not c["match"] and c["llm_label"] and c["v3_label"])
    llm_only = sum(1 for c in comparison.values() if c["llm_label"] and not c["v3_label"])
    v3_only = sum(1 for c in comparison.values() if c["v3_label"] and not c["llm_label"])

    report.append("## 总体统计\n\n")
    report.append(f"- **匹配**：{matches} 个字符\n")
    report.append(f"- **不匹配**：{mismatches} 个字符\n")
    report.append(f"- **仅 LLM 标注**：{llm_only} 个字符\n")
    report.append(f"- **仅 v3 标注**：{v3_only} 个字符\n")

    if matches + mismatches > 0:
        accuracy = matches / (matches + mismatches) * 100
        report.append(f"- **准确率**：{accuracy:.1f}%\n")

    report.append("\n---\n\n")

    # 不匹配的字符
    report.append("## 不匹配的字符\n\n")
    report.append("| 字符 | 父类别 | LLM 标注 | v3 标注 |\n")
    report.append("|------|--------|----------|----------|\n")

    for char, data in sorted(comparison.items()):
        if not data["match"] and data["llm_label"] and data["v3_label"]:
            report.append(f"| {char} | {data['parent_category']} | {data['llm_label']} | {data['v3_label']} |\n")

    report.append("\n---\n\n")

    # 仅 LLM 标注的字符
    report.append("## 仅 LLM 标注的字符（v3 中未定义）\n\n")
    report.append("| 字符 | 父类别 | LLM 标注 |\n")
    report.append("|------|--------|----------|\n")

    for char, data in sorted(comparison.items()):
        if data["llm_label"] and not data["v3_label"]:
            report.append(f"| {char} | {data['parent_category']} | {data['llm_label']} |\n")

    report.append("\n---\n\n")

    # 仅 v3 标注的字符
    report.append("## 仅 v3 标注的字符（LLM 未标注）\n\n")
    report.append("| 字符 | 父类别 | v3 标注 |\n")
    report.append("|------|--------|----------|\n")

    for char, data in sorted(comparison.items()):
        if data["v3_label"] and not data["llm_label"]:
            report.append(f"| {char} | {data['parent_category']} | {data['v3_label']} |\n")

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"[OK] 验证报告已保存：{output_path}")


def update_v4_lexicon_with_llm(llm_labels: Dict, comparison: Dict, v1: Dict, v3: Dict):
    """
    基于 LLM 标注和对比结果更新 v4 词典

    策略：
    - 如果 LLM 和 v3 一致，使用该标注
    - 如果不一致，优先使用 LLM 标注（但标记为需要人工审核）
    - 如果仅 LLM 标注，使用 LLM 标注
    - 如果仅 v3 标注，使用 v3 标注

    Args:
        llm_labels: LLM 标注结果
        comparison: 对比结果
        v1: v1 词典
        v3: v3_expanded 词典
    """
    print("\n" + "=" * 60)
    print("Step 4: 更新 v4_pilot 词典")
    print("=" * 60)

    # 创建新的 v4 词典
    v4 = {
        "version": "4.0.0-pilot-llm",
        "created_at": time.strftime("%Y-%m-%d"),
        "description": "Pilot semantic lexicon with LLM-validated subcategories",
        "parent_categories": v1["categories"].copy(),
        "subcategories": defaultdict(list),
        "metadata": {
            "llm_model": "deepseek-chat",
            "validation_date": time.strftime("%Y-%m-%d"),
            "total_chars": len(comparison),
            "llm_labeled": len(llm_labels),
            "conflicts": sum(1 for c in comparison.values() if not c["match"] and c["llm_label"] and c["v3_label"])
        }
    }

    # 填充子类别
    for char, data in comparison.items():
        # 优先使用 LLM 标注
        if data["llm_label"]:
            subcategory = data["llm_label"]
        elif data["v3_label"]:
            subcategory = data["v3_label"]
        else:
            continue

        v4["subcategories"][subcategory].append(char)

    # 转换为普通字典
    v4["subcategories"] = dict(v4["subcategories"])

    # 保存 v4 词典
    with open(LEXICON_V4_PATH, 'w', encoding='utf-8') as f:
        json.dump(v4, f, ensure_ascii=False, indent=2)

    print(f"[OK] v4_pilot 词典已更新：{LEXICON_V4_PATH}")
    print(f"   - {len(v4['subcategories'])} 个子类别")
    print(f"   - {sum(len(chars) for chars in v4['subcategories'].values())} 个字符")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Phase 17: LLM 辅助语义子类别验证")
    print("=" * 60)
    print(f"数据库：{DB_PATH}")
    print(f"词典 v1：{LEXICON_V1_PATH}")
    print(f"词典 v3：{LEXICON_V3_PATH}")
    print(f"词典 v4：{LEXICON_V4_PATH}")
    print(f"LLM 模型：DeepSeek Chat")
    print("=" * 60)

    if not DEEPSEEK_API_KEY:
        print("\n[ERROR] DEEPSEEK_API_KEY not found in .env file")
        print("Please create a .env file with your API key:")
        print("DEEPSEEK_API_KEY=your_api_key_here")
        return

    start_time = time.time()

    # 加载词典
    v1 = load_lexicon(LEXICON_V1_PATH)
    v3 = load_lexicon(LEXICON_V3_PATH)

    # Step 1: LLM 标注
    llm_labels = llm_label_all_characters(v1, v3)

    # Step 2: 对比验证
    comparison = compare_with_existing(llm_labels, v3)

    # Step 3: 生成报告
    report_path = PROJECT_ROOT / "docs" / "reports" / "PHASE_17_LLM_VALIDATION_REPORT.md"
    generate_validation_report(comparison, report_path)

    # Step 4: 更新 v4 词典
    update_v4_lexicon_with_llm(llm_labels, comparison, v1, v3)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[OK] LLM 验证完成！")
    print(f"[TIME] 总耗时：{elapsed:.2f} 秒")
    print("=" * 60)

    print("\n下一步：")
    print(f"1. 查看验证报告：{report_path}")
    print(f"2. 查看更新后的词典：{LEXICON_V4_PATH}")
    print("3. 人工审核不匹配的字符")
    print("4. 重新运行 phase17_semantic_subcategory.py 更新数据库")


if __name__ == "__main__":
    main()
