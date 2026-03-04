#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Villages-ML Complete Analysis Pipeline Runner
广东省自然村分析系统 - 完整分析流水线执行器

This script orchestrates ALL 17 analysis phases for the Guangdong villages dataset.
本脚本编排执行广东省村庄数据集的全部17个分析阶段。

================================================================================
QUICK START 快速开始
================================================================================

1. Run all phases (完整运行所有阶段):
   python run_all_phases.py --all

2. Run specific phases (运行指定阶段):
   python run_all_phases.py --phases 0,1,2,3

3. Run phase groups (运行阶段组):
   python run_all_phases.py --group core
   python run_all_phases.py --group statistical
   python run_all_phases.py --group advanced

4. Dry run to preview (预览执行计划):
   python run_all_phases.py --all --dry-run

5. List all phases (列出所有阶段):
   python run_all_phases.py --list

6. Show phase details (显示阶段详情):
   python run_all_phases.py --info 12

7. Skip failed phases and continue (跳过失败继续执行):
   python run_all_phases.py --all --continue-on-error

================================================================================
PHASE GROUPS 阶段分组
================================================================================

Core Phases (核心阶段 0-7) - Required for basic analysis:
  Phase 0  : Data Preprocessing (数据预处理) - CRITICAL
  Phase 1  : Character Embeddings (字符嵌入)
  Phase 2  : Frequency Analysis (频率分析)
  Phase 3  : Semantic Analysis (语义分析)
  Phase 4  : Spatial Analysis (空间分析)
  Phase 5  : Feature Engineering (特征工程)
  Phase 6  : Clustering Analysis (聚类分析)
  Phase 7  : Feature Materialization (特征物化)

Statistical Phases (统计阶段 8-10) - Statistical enhancements:
  Phase 8  : Tendency Analysis (倾向性分析)
  Phase 9  : Z-score Normalization (Z分数标准化)
  Phase 10 : Significance Testing (显著性检验)

Advanced Phases (高级阶段 11-17) - Advanced analysis:
  Phase 11 : Query Policy Framework (查询策略框架)
  Phase 12 : N-gram Analysis (N-gram分析)
  Phase 13 : Spatial Hotspots (空间热点)
  Phase 14 : Semantic Composition (语义组合)
  Phase 15 : Region Similarity (区域相似度)
  Phase 16 : Semantic Centrality (语义中心性)
  Phase 17 : Hybrid Analysis (混合分析)

================================================================================
DEPENDENCIES 依赖关系
================================================================================

Phase 0 (Preprocessing) MUST run first - all other phases depend on it!
Phase 0（预处理）必须首先运行 - 所有其他阶段都依赖它！

Dependency Chain (依赖链):
  Phase 0 → All other phases (所有其他阶段)
  Phase 1 → Phase 14, 16, 17 (语义相关分析)
  Phase 2 → Phase 8, 9, 10 (统计增强)
  Phase 4 → Phase 13 (空间热点)
  Phase 5 → Phase 6, 7 (聚类和物化)

================================================================================
EXECUTION TIME 预计执行时间
================================================================================

Estimated time for full dataset (285K villages, 全量数据集):
  Phase 0  : 2-5 min    | Phase 9  : 2-3 min
  Phase 1  : 5-10 min   | Phase 10 : 2-3 min
  Phase 2  : 3-5 min    | Phase 11 : 1-2 min
  Phase 3  : 3-5 min    | Phase 12 : 5-10 min
  Phase 4  : 5-10 min   | Phase 13 : 2-3 min
  Phase 5  : 3-5 min    | Phase 14 : 3-5 min
  Phase 6  : 3-5 min    | Phase 15 : 2-3 min
  Phase 7  : 2-3 min    | Phase 16 : 2-3 min
  Phase 8  : 2-3 min    | Phase 17 : 3-5 min

  Total: 60-120 minutes (1-2 hours, 总计1-2小时)

================================================================================
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# ========== HELPER FUNCTIONS ==========

def print_phase_list():
    """Print a formatted list of all available phases."""
    print("\n" + "="*80)
    print("Available Phases (可用阶段)")
    print("="*80)

    groups = {"core": [], "statistical": [], "advanced": []}
    for phase_id, phase in sorted(PHASES.items()):
        group = phase.get('group', 'core')
        groups[group].append((phase_id, phase))

    for group_name, phases in groups.items():
        if not phases:
            continue

        group_title = {
            "core": "Core Phases (核心阶段 0-7)",
            "statistical": "Statistical Phases (统计阶段 8-10)",
            "advanced": "Advanced Phases (高级阶段 11-17)"
        }[group_name]

        print(f"\n{group_title}:")
        print("-" * 80)

        for phase_id, phase in phases:
            critical = "⚠️ CRITICAL" if phase.get('critical') else ""
            print(f"  Phase {phase_id:2d}: {phase['name']} ({phase.get('name_zh', '')}) {critical}")
            print(f"            {phase['description']}")
            print(f"            Time: {phase.get('estimated_time', 'N/A')}")

    print()


def print_phase_info(phase_id: int):
    """Print detailed information about a specific phase."""
    if phase_id not in PHASES:
        print(f"❌ Error: Phase {phase_id} not found")
        return

    phase = PHASES[phase_id]

    print("\n" + "="*80)
    print(f"Phase {phase_id}: {phase['name']} ({phase.get('name_zh', '')})")
    print("="*80)

    print(f"\n📝 Description:")
    print(f"   EN: {phase['description']}")
    if 'description_zh' in phase:
        print(f"   ZH: {phase['description_zh']}")

    print(f"\n📂 Script: {phase['script']}")
    print(f"🏷️  Group: {phase.get('group', 'N/A')}")
    print(f"⏱️  Estimated Time: {phase.get('estimated_time', 'N/A')}")
    print(f"🔑 Critical: {'Yes' if phase.get('critical') else 'No'}")

    if phase.get('dependencies'):
        deps = ', '.join(f"Phase {d}" for d in phase['dependencies'])
        print(f"🔗 Dependencies: {deps}")
    else:
        print(f"🔗 Dependencies: None")

    if phase.get('output_tables'):
        print(f"\n📊 Output Tables:")
        for table in phase['output_tables']:
            print(f"   - {table}")

    if phase.get('args'):
        print(f"\n⚙️  Arguments:")
        args = phase['args']
        for i in range(0, len(args), 2):
            if i + 1 < len(args):
                print(f"   {args[i]} {args[i+1]}")
            else:
                print(f"   {args[i]}")

    print()


def print_phase_groups():
    """Print phase groups and their members."""
    print("\n" + "="*80)
    print("Phase Groups (阶段分组)")
    print("="*80)

    groups = {}
    for phase_id, phase in PHASES.items():
        group = phase.get('group', 'core')
        if group not in groups:
            groups[group] = []
        groups[group].append(phase_id)

    for group_name in ['core', 'statistical', 'advanced']:
        if group_name not in groups:
            continue

        group_title = {
            "core": "Core Phases (核心阶段)",
            "statistical": "Statistical Phases (统计阶段)",
            "advanced": "Advanced Phases (高级阶段)"
        }[group_name]

        phase_ids = sorted(groups[group_name])
        print(f"\n{group_title}:")
        print(f"  Phases: {', '.join(str(p) for p in phase_ids)}")
        print(f"  Command: python run_all_phases.py --group {group_name}")

    print()


def get_phases_by_group(group: str) -> List[int]:
    """Get all phase IDs in a specific group."""
    return sorted([
        phase_id for phase_id, phase in PHASES.items()
        if phase.get('group') == group
    ])


def parse_phase_list(phase_str: str) -> Optional[List[int]]:
    """Parse phase list string (e.g., '0,1,2' or '0-5,12')."""
    try:
        phases = []
        for part in phase_str.split(','):
            part = part.strip()
            if '-' in part:
                # Range: '0-5'
                start, end = part.split('-')
                phases.extend(range(int(start), int(end) + 1))
            else:
                # Single phase: '12'
                phases.append(int(part))
        return sorted(set(phases))
    except ValueError:
        print(f"❌ Error: Invalid phase format: '{phase_str}'")
        print(f"   Valid formats: '0,1,2' or '0-5,12'")
        return None


def check_dependencies(phases_to_run: List[int]) -> Dict[int, List[int]]:
    """Check if all dependencies are satisfied."""
    missing = {}
    for phase_id in phases_to_run:
        phase = PHASES[phase_id]
        deps = phase.get('dependencies', [])
        missing_deps = [d for d in deps if d not in phases_to_run]
        if missing_deps:
            missing[phase_id] = missing_deps
    return missing


def print_execution_plan(phases_to_run: List[int], args):
    """Print the execution plan."""
    print("\n" + "="*80)
    print("Execution Plan (执行计划)")
    print("="*80)

    print(f"\n📋 Phases to run: {', '.join(str(p) for p in phases_to_run)}")
    print(f"📊 Total phases: {len(phases_to_run)}")
    print(f"🗄️  Database: {args.db_path}")
    print(f"🏷️  Run ID prefix: {args.run_id_prefix}")
    print(f"🔍 Dry run: {'Yes' if args.dry_run else 'No'}")
    print(f"⚠️  Continue on error: {'Yes' if args.continue_on_error else 'No'}")

    # Estimate total time
    total_min_time = 0
    total_max_time = 0
    for phase_id in phases_to_run:
        time_str = PHASES[phase_id].get('estimated_time', '0-0 min')
        if '-' in time_str:
            min_t, max_t = time_str.split('-')
            total_min_time += int(min_t.strip().split()[0])
            total_max_time += int(max_t.strip().split()[0])

    print(f"⏱️  Estimated time: {total_min_time}-{total_max_time} minutes")
    print(f"🕐 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n" + "-"*80)
    print("Phase Details:")
    print("-"*80)

    for phase_id in phases_to_run:
        phase = PHASES[phase_id]
        critical = "⚠️" if phase.get('critical') else "  "
        print(f"{critical} Phase {phase_id:2d}: {phase['name']:30s} [{phase.get('estimated_time', 'N/A'):>10s}]")


def print_summary(results: Dict[int, bool], start_time: float, dry_run: bool):
    """Print execution summary."""
    elapsed = time.time() - start_time

    print("\n" + "="*80)
    print("Execution Summary (执行总结)")
    print("="*80)

    # Count results
    total = len(results)
    success_count = sum(1 for v in results.values() if v)
    fail_count = total - success_count

    print(f"\n📊 Results:")
    print(f"   Total phases: {total}")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {fail_count}")

    print(f"\n⏱️  Timing:")
    print(f"   Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"   End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n📋 Phase Results:")
    print("-"*80)

    for phase_id in sorted(results.keys()):
        status = "✅ OK  " if results[phase_id] else "❌ FAIL"
        phase_name = PHASES[phase_id]['name']
        print(f"  {status} | Phase {phase_id:2d}: {phase_name}")

    if dry_run:
        print(f"\n🔍 This was a dry run - no phases were actually executed")

    print()


# Phase definitions with complete metadata
PHASES = {
    # ========== CORE PHASES (0-7) ==========
    0: {
        "name": "Data Preprocessing",
        "name_zh": "数据预处理",
        "script": "scripts/preprocessing/create_preprocessed_table.py",
        "args": [],
        "description": "Clean village names, remove administrative prefixes (5,782 prefixes)",
        "description_zh": "清理村名、去除行政前缀（5,782个前缀）",
        "group": "core",
        "dependencies": [],
        "estimated_time": "2-5 min",
        "output_tables": ["广东省自然村_预处理"],
        "critical": True,
        "use_run_id": False
    },
    1: {
        "name": "Character Embeddings",
        "name_zh": "字符嵌入",
        "script": "scripts/core/train_char_embeddings.py",
        "args": [
            "--db-path", "data/villages.db",
            "--vector-size", "100",
            "--window", "3",
            "--min-count", "2",
            "--epochs", "15",
            "--model-type", "skipgram",
            "--precompute-similarities",
            "--top-k", "50"
        ],
        "description": "Train Word2Vec embeddings (Skip-gram, 100-dim, 9,209 chars)",
        "description_zh": "训练Word2Vec嵌入（Skip-gram，100维，9,209个字符）",
        "group": "core",
        "dependencies": [0],
        "estimated_time": "5-10 min",
        "output_tables": ["char_embeddings", "char_similarity"],
        "critical": True,
        "use_run_id": True
    },
    2: {
        "name": "Frequency Analysis",
        "name_zh": "频率分析",
        "script": "scripts/core/run_frequency_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Compute character frequencies and regional tendencies",
        "description_zh": "计算字符频率和区域倾向性",
        "group": "core",
        "dependencies": [0],
        "estimated_time": "3-5 min",
        "output_tables": ["char_regional_analysis"],
        "critical": True,
        "use_run_id": True
    },
    3: {
        "name": "Semantic Analysis",
        "name_zh": "语义分析",
        "script": "scripts/core/run_semantic_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "LLM-assisted semantic labeling and co-occurrence analysis",
        "description_zh": "LLM辅助语义标注和共现分析",
        "group": "core",
        "dependencies": [0],
        "estimated_time": "3-5 min",
        "output_tables": ["semantic_labels", "semantic_cooccurrence", "semantic_network_edges"],
        "critical": True,
        "use_run_id": True
    },
    4: {
        "name": "Spatial Analysis",
        "name_zh": "空间分析",
        "script": "scripts/core/run_spatial_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "k-NN, DBSCAN clustering, KDE hotspot detection (283,986 villages)",
        "description_zh": "k-NN、DBSCAN聚类、KDE热点检测（283,986个村庄）",
        "group": "core",
        "dependencies": [0],
        "estimated_time": "5-10 min",
        "output_tables": ["village_spatial_features", "spatial_clusters"],
        "critical": True,
        "use_run_id": True
    },
    5: {
        "name": "Feature Engineering",
        "name_zh": "特征工程",
        "script": "scripts/core/generate_village_features.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Extract 230+ features per village (semantic, spatial, morphology)",
        "description_zh": "提取每个村庄的230+特征（语义、空间、形态学）",
        "group": "core",
        "dependencies": [0, 1, 3, 4],
        "estimated_time": "3-5 min",
        "output_tables": ["village_features"],
        "critical": True,
        "use_run_id": True
    },
    6: {
        "name": "Clustering Analysis",
        "name_zh": "聚类分析",
        "script": "scripts/core/run_clustering_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "KMeans, DBSCAN, GMM clustering on 121 counties",
        "description_zh": "对121个区县进行KMeans、DBSCAN、GMM聚类",
        "group": "core",
        "dependencies": [0, 5],
        "estimated_time": "3-5 min",
        "output_tables": ["regional_features", "cluster_assignments", "cluster_profiles"],
        "critical": True,
        "use_run_id": True
    },
    7: {
        "name": "Feature Materialization",
        "name_zh": "特征物化",
        "script": "scripts/core/fill_aggregates_tables.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Materialize regional aggregates (city/county/township level)",
        "description_zh": "物化区域聚合特征（市/县/镇级别）",
        "group": "core",
        "dependencies": [0, 5],
        "estimated_time": "2-3 min",
        "output_tables": ["regional_aggregates"],
        "critical": False,
        "use_run_id": True
    },

    # ========== STATISTICAL PHASES (8-10) ==========
    8: {
        "name": "Tendency Analysis",
        "name_zh": "倾向性分析",
        "script": "scripts/core/run_tendency_with_significance.py",
        "args": [
            "--db-path", "data/villages.db",
            "--mode", "tendency"
        ],
        "description": "Compute lift and log-odds ratios for regional tendencies",
        "description_zh": "计算区域倾向性的lift和log-odds比率",
        "group": "statistical",
        "dependencies": [0, 2],
        "estimated_time": "2-3 min",
        "output_tables": ["char_regional_analysis"],
        "critical": False,
        "use_run_id": True
    },
    9: {
        "name": "Z-score Normalization",
        "name_zh": "Z分数标准化",
        "script": "scripts/core/run_tendency_with_significance.py",
        "args": [
            "--db-path", "data/villages.db",
            "--mode", "zscore"
        ],
        "description": "Normalize tendency scores using z-score transformation",
        "description_zh": "使用z-score变换标准化倾向性分数",
        "group": "statistical",
        "dependencies": [0, 2, 8],
        "estimated_time": "2-3 min",
        "output_tables": ["char_regional_analysis"],
        "critical": False,
        "use_run_id": True
    },
    10: {
        "name": "Significance Testing",
        "name_zh": "显著性检验",
        "script": "scripts/core/compute_significance_only.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Chi-square test, p-values, effect sizes, confidence intervals",
        "description_zh": "卡方检验、p值、效应量、置信区间",
        "group": "statistical",
        "dependencies": [0, 2, 8],
        "estimated_time": "2-3 min",
        "output_tables": ["char_regional_analysis"],
        "critical": False,
        "use_run_id": True
    },

    # ========== ADVANCED PHASES (11-17) ==========
    11: {
        "name": "Query Policy Framework",
        "name_zh": "查询策略框架",
        "script": "scripts/core/create_missing_tables.py",
        "args": [
            "--db-path", "data/villages.db",
            "--tables", "query_policy"
        ],
        "description": "Create query policy tables for API resource management",
        "description_zh": "创建查询策略表用于API资源管理",
        "group": "advanced",
        "dependencies": [0],
        "estimated_time": "1-2 min",
        "output_tables": ["query_policy_config", "query_logs"],
        "critical": False,
        "use_run_id": False
    },
    12: {
        "name": "N-gram Analysis",
        "name_zh": "N-gram分析",
        "script": "scripts/core/phase12_ngram_analysis.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Extract bigrams, trigrams, 4-grams (1,909,959 patterns)",
        "description_zh": "提取bigram、trigram、4-gram（1,909,959个模式）",
        "group": "advanced",
        "dependencies": [0],
        "estimated_time": "5-10 min",
        "output_tables": ["ngram_frequency", "structural_patterns"],
        "critical": False,
        "use_run_id": True
    },
    13: {
        "name": "Spatial Hotspots",
        "name_zh": "空间热点",
        "script": "scripts/core/generate_spatial_features.py",
        "args": [
            "--db-path", "data/villages.db",
            "--mode", "hotspots"
        ],
        "description": "KDE-based hotspot detection (8 hotspot regions)",
        "description_zh": "基于KDE的热点检测（8个热点区域）",
        "group": "advanced",
        "dependencies": [0, 4],
        "estimated_time": "2-3 min",
        "output_tables": ["spatial_hotspots"],
        "critical": False,
        "use_run_id": True
    },
    14: {
        "name": "Semantic Composition",
        "name_zh": "语义组合",
        "script": "scripts/core/phase14_semantic_composition.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Analyze semantic composition patterns (8 patterns)",
        "description_zh": "分析语义组合模式（8种模式）",
        "group": "advanced",
        "dependencies": [0, 1, 3],
        "estimated_time": "3-5 min",
        "output_tables": ["semantic_composition_patterns", "semantic_bigrams", "semantic_trigrams"],
        "critical": False,
        "use_run_id": True
    },
    15: {
        "name": "Region Similarity",
        "name_zh": "区域相似度",
        "script": "scripts/core/phase15_region_similarity.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Compute region similarity using cosine similarity on feature vectors",
        "description_zh": "使用特征向量的余弦相似度计算区域相似度",
        "group": "advanced",
        "dependencies": [0, 5, 6],
        "estimated_time": "2-3 min",
        "output_tables": ["region_vectors"],
        "critical": False,
        "use_run_id": True
    },
    16: {
        "name": "Semantic Centrality",
        "name_zh": "语义中心性",
        "script": "scripts/core/phase16_semantic_centrality.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Compute semantic network centrality metrics (degree, betweenness, PageRank)",
        "description_zh": "计算语义网络中心性指标（度中心性、介数中心性、PageRank）",
        "group": "advanced",
        "dependencies": [0, 1, 3],
        "estimated_time": "2-3 min",
        "output_tables": ["semantic_network_edges"],
        "critical": False,
        "use_run_id": True
    },
    17: {
        "name": "Hybrid Analysis",
        "name_zh": "混合分析",
        "script": "scripts/core/phase17_semantic_subcategory.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "LLM validation, semantic subcategories, hybrid lexicon creation",
        "description_zh": "LLM验证、语义子类别、混合词典创建",
        "group": "advanced",
        "dependencies": [0, 1, 3],
        "estimated_time": "3-5 min",
        "output_tables": ["semantic_labels"],
        "critical": False,
        "use_run_id": True
    }
}


def run_phase(phase_id, run_id_prefix="run", dry_run=False, db_path="data/villages.db"):
    """Run a single analysis phase.

    Args:
        phase_id: Phase number to run
        run_id_prefix: Prefix for run ID generation
        dry_run: If True, only show what would be executed
        db_path: Path to database file

    Returns:
        bool: True if phase completed successfully, False otherwise
    """
    if phase_id not in PHASES:
        print(f"❌ Error: Phase {phase_id} not found")
        return False

    phase = PHASES[phase_id]

    # Print phase header
    print(f"\n{'='*80}")
    print(f"Phase {phase_id}: {phase['name']} ({phase.get('name_zh', '')})")
    print(f"{'='*80}")
    print(f"Description: {phase['description']}")
    if 'description_zh' in phase:
        print(f"描述: {phase['description_zh']}")
    print(f"Group: {phase.get('group', 'N/A')}")
    print(f"Estimated time: {phase.get('estimated_time', 'N/A')}")
    print(f"Script: {phase['script']}")

    # Show dependencies
    if phase.get('dependencies'):
        deps = ', '.join(str(d) for d in phase['dependencies'])
        print(f"Dependencies: Phase {deps}")

    # Show output tables
    if phase.get('output_tables'):
        tables = ', '.join(phase['output_tables'])
        print(f"Output tables: {tables}")

    # Build command
    cmd = ["python", phase['script']]

    # Add run-id if the script supports it
    if phase.get('use_run_id', True) and phase_id > 0:
        run_id = f"{run_id_prefix}_{phase_id:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cmd.extend(["--run-id", run_id])

    # Add phase-specific arguments (replace db-path if needed)
    args = phase['args'].copy() if phase['args'] else []
    if '--db-path' in args and db_path != "data/villages.db":
        idx = args.index('--db-path')
        args[idx + 1] = db_path
    cmd.extend(args)

    print(f"\nCommand: {' '.join(cmd)}")

    if dry_run:
        print("🔍 [DRY RUN] Command not executed")
        return True

    # Execute
    print(f"\n▶️  [START] Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )

        elapsed = time.time() - start_time
        print(f"\n✅ [OK] Phase {phase_id} completed successfully in {elapsed:.1f}s ({elapsed/60:.1f} min)")
        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"\n❌ [FAIL] Phase {phase_id} failed after {elapsed:.1f}s")
        print(f"Error: {e}")
        return False

    except KeyboardInterrupt:
        print(f"\n⏹️  [STOP] Phase {phase_id} interrupted by user")
        return False


def main():
    """Main entry point for the pipeline runner."""
    parser = argparse.ArgumentParser(
        description="Villages-ML Complete Analysis Pipeline Runner (广东省自然村分析系统)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Execution mode arguments
    exec_group = parser.add_argument_group('Execution Mode (执行模式)')
    exec_group.add_argument(
        "--all",
        action="store_true",
        help="Run all phases sequentially (按顺序运行所有阶段)"
    )
    exec_group.add_argument(
        "--phases",
        type=str,
        metavar="PHASE_IDS",
        help="Comma-separated list of phase IDs to run (e.g., '0,1,2,3' or '0-5,12')"
    )
    exec_group.add_argument(
        "--group",
        type=str,
        choices=["core", "statistical", "advanced"],
        help="Run all phases in a specific group (core: 0-7, statistical: 8-10, advanced: 11-17)"
    )

    # Configuration arguments
    config_group = parser.add_argument_group('Configuration (配置选项)')
    config_group.add_argument(
        "--db-path",
        type=str,
        default="data/villages.db",
        metavar="PATH",
        help="Path to database file (default: data/villages.db)"
    )
    config_group.add_argument(
        "--run-id-prefix",
        type=str,
        default="run",
        metavar="PREFIX",
        help="Prefix for run IDs (default: 'run')"
    )

    # Behavior arguments
    behavior_group = parser.add_argument_group('Behavior (行为选项)')
    behavior_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without actually running (预览执行计划)"
    )
    behavior_group.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue executing remaining phases even if one fails (失败后继续执行)"
    )
    behavior_group.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="Skip dependency checking (advanced users only, 跳过依赖检查)"
    )

    # Information arguments
    info_group = parser.add_argument_group('Information (信息查询)')
    info_group.add_argument(
        "--list",
        action="store_true",
        help="List all available phases (列出所有可用阶段)"
    )
    info_group.add_argument(
        "--info",
        type=int,
        metavar="PHASE_ID",
        help="Show detailed information about a specific phase (显示指定阶段的详细信息)"
    )
    info_group.add_argument(
        "--show-groups",
        action="store_true",
        help="Show phase groups and their members (显示阶段分组)"
    )

    args = parser.parse_args()

    # Handle information queries
    if args.list:
        print_phase_list()
        return 0

    if args.info is not None:
        print_phase_info(args.info)
        return 0

    if args.show_groups:
        print_phase_groups()
        return 0

    # Determine which phases to run
    phases_to_run = []

    if args.all:
        phases_to_run = sorted(PHASES.keys())
    elif args.group:
        phases_to_run = get_phases_by_group(args.group)
    elif args.phases:
        phases_to_run = parse_phase_list(args.phases)
        if phases_to_run is None:
            return 1
    else:
        parser.print_help()
        return 1

    # Validate phases
    invalid = [p for p in phases_to_run if p not in PHASES]
    if invalid:
        print(f"❌ Error: Invalid phase IDs: {invalid}")
        print(f"Valid phases: {sorted(PHASES.keys())}")
        return 1

    # Check dependencies
    if not args.skip_dependencies:
        missing_deps = check_dependencies(phases_to_run)
        if missing_deps:
            print(f"\n⚠️  Warning: Missing dependencies detected!")
            for phase_id, deps in missing_deps.items():
                phase_name = PHASES[phase_id]['name']
                print(f"  Phase {phase_id} ({phase_name}) requires: {deps}")
            print(f"\n💡 Tip: Add missing phases or use --skip-dependencies to ignore")
            return 1

    # Print execution plan
    print_execution_plan(phases_to_run, args)

    # Confirm execution (unless dry-run)
    if not args.dry_run and len(phases_to_run) > 3:
        response = input("\n▶️  Proceed with execution? [Y/n]: ")
        if response.lower() in ['n', 'no']:
            print("❌ Execution cancelled by user")
            return 0

    # Run phases
    overall_start = time.time()
    results = {}

    for phase_id in phases_to_run:
        success = run_phase(phase_id, args.run_id_prefix, args.dry_run, args.db_path)
        results[phase_id] = success

        if not success and not args.dry_run:
            if args.continue_on_error:
                print(f"\n⚠️  Phase {phase_id} failed, but continuing due to --continue-on-error")
            else:
                print(f"\n⏹️  Phase {phase_id} failed. Stopping execution.")
                print(f"💡 Tip: Use --continue-on-error to skip failed phases")
                break

    # Print summary
    print_summary(results, overall_start, args.dry_run)

    # Return exit code
    all_success = all(results.values())
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
