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

8. Clean rebuild: drop ALL derived tables, restart from scratch (全新开始):
   python run_all_phases.py --all --clear

================================================================================
PHASE GROUPS 阶段分组
================================================================================

Core Phases (核心阶段 0-7) - Required for basic analysis:
  Phase 0  : Data Preprocessing (数据预处理) - CRITICAL
  Phase 1  : Character Embeddings (字符嵌入)
  Phase 2  : Frequency Analysis (频率分析) - Includes tendency & z-score
  Phase 3  : Semantic Analysis (语义分析)
  Phase 4  : Spatial Analysis (空间分析)
  Phase 5  : Feature Engineering (特征工程)
  Phase 6  : Clustering Analysis (聚类分析)
  Phase 7  : Feature Materialization (特征物化)

Statistical Phases (统计阶段 10) - Statistical enhancements:
  Phase 10 : Significance Testing (显著性检验)

  Note: Phase 8 (Tendency Analysis) and Phase 9 (Z-score Normalization)
  have been removed as these are now performed by Phase 2.

Advanced Phases (高级阶段 11-18) - Advanced analysis:
  Phase 11 : Query Policy Framework (查询策略框架)
  Phase 12 : N-gram Analysis (N-gram分析)
  Phase 13 : Spatial Hotspots (空间热点)
  Phase 14 : Semantic Composition (语义组合)
  Phase 15 : Region Similarity (区域相似度)
  Phase 16 : Semantic Centrality (语义中心性)
  Phase 17 : Hybrid Analysis (混合分析)
  Phase 18 : Morphology Patterns (形态模式分析)

================================================================================
DEPENDENCIES 依赖关系
================================================================================

Phase 0 (Preprocessing) MUST run first - all other phases depend on it!
Phase 0（预处理）必须首先运行 - 所有其他阶段都依赖它！

Dependency Chain (依赖链):
  Phase 0 → All other phases (所有其他阶段)
  Phase 1 → Phase 3, 14, 16, 17 (语义相关分析)
  Phase 2 → Phase 10 (统计增强) - Phase 2 now includes tendency & z-score
  Phase 4 → Phase 13 (空间热点)
  Phase 5 → Phase 6, 7 (聚类和物化)

================================================================================
EXECUTION TIME 预计执行时间
================================================================================

Estimated time for full dataset (285K villages, 全量数据集):
  Phase 0  : 2-5 min    | Phase 10 : 2-3 min
  Phase 1  : 5-10 min   | Phase 11 : 1-2 min
  Phase 2  : 3-5 min    | Phase 12 : 5-10 min
  Phase 3  : 3-5 min    | Phase 13 : 2-3 min
  Phase 4  : 5-10 min   | Phase 14 : 3-5 min
  Phase 5  : 3-5 min    | Phase 15 : 2-3 min
  Phase 6  : 3-5 min    | Phase 16 : 2-3 min
  Phase 7  : 2-3 min    | Phase 17 : 3-5 min

  Total: 50-100 minutes (0.8-1.7 hours, 总计约1-2小时)

================================================================================
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.pipeline_config import load_pipeline_config, merge_phase_definitions, resolve_pipeline_config_path
from src.pipeline_retention import apply_retention_policy, retention_policy_from_config
from src.schema import get_schema


# ========== HELPER FUNCTIONS ==========

def print_phase_list(phases: Optional[Dict[int, dict]] = None):
    """Print a formatted list of all available phases."""
    phases = phases or PHASES
    print("\n" + "="*80)
    print("Available Phases (可用阶段)")
    print("="*80)

    groups = {"core": [], "statistical": [], "advanced": []}
    for phase_id, phase in sorted(phases.items()):
        group = phase.get('group', 'core')
        groups[group].append((phase_id, phase))

    for group_name, phases in groups.items():
        if not phases:
            continue

        group_title = {
            "core": "Core Phases (核心阶段 0-7)",
            "statistical": "Statistical Phases (统计阶段 8-10)",
            "advanced": "Advanced Phases (高级阶段 11-18)"
        }[group_name]

        print(f"\n{group_title}:")
        print("-" * 80)

        for phase_id, phase in phases:
            critical = "⚠️ CRITICAL" if phase.get('critical') else ""
            print(f"  Phase {phase_id:2d}: {phase['name']} ({phase.get('name_zh', '')}) {critical}")
            print(f"            {phase['description']}")
            print(f"            Time: {phase.get('estimated_time', 'N/A')}")

    print()


def print_phase_info(phase_id: int, phases: Optional[Dict[int, dict]] = None):
    """Print detailed information about a specific phase."""
    phases = phases or PHASES
    if phase_id not in phases:
        print(f"❌ Error: Phase {phase_id} not found")
        return

    phase = phases[phase_id]

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


def print_phase_groups(phases: Optional[Dict[int, dict]] = None):
    """Print phase groups and their members."""
    phases = phases or PHASES
    print("\n" + "="*80)
    print("Phase Groups (阶段分组)")
    print("="*80)

    groups = {}
    for phase_id, phase in phases.items():
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


def get_phases_by_group(group: str, phases: Optional[Dict[int, dict]] = None) -> List[int]:
    """Get all phase IDs in a specific group."""
    phases = phases or PHASES
    return sorted([
        phase_id for phase_id, phase in phases.items()
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


def check_dependencies(phases_to_run: List[int], phases: Optional[Dict[int, dict]] = None) -> Dict[int, List[int]]:
    """Check if all dependencies are satisfied."""
    phases = phases or PHASES
    missing = {}
    for phase_id in phases_to_run:
        phase = phases[phase_id]
        deps = phase.get('dependencies', [])
        missing_deps = [d for d in deps if d not in phases_to_run]
        if missing_deps:
            missing[phase_id] = missing_deps
    return missing


def print_execution_plan(phases_to_run: List[int], args, phases: Optional[Dict[int, dict]] = None):
    """Print the execution plan."""
    phases = phases or PHASES
    print("\n" + "="*80)
    print("Execution Plan (执行计划)")
    print("="*80)

    print(f"\n📋 Phases to run: {', '.join(str(p) for p in phases_to_run)}")
    print(f"📊 Total phases: {len(phases_to_run)}")
    print(f"⚙️  Config profile: {args.config}")
    print(f"🗄️  Database: {args.db_path}")
    print(f"🏷️  Run ID prefix: {args.run_id_prefix}")
    print(f"🔍 Dry run: {'Yes' if args.dry_run else 'No'}")
    print(f"⚠️  Continue on error: {'Yes' if args.continue_on_error else 'No'}")
    if args.clear:
        print(f"🧹 Clear mode: ALL derived tables will be dropped before execution")

    # Estimate total time
    total_min_time = 0
    total_max_time = 0
    for phase_id in phases_to_run:
        time_str = phases[phase_id].get('estimated_time', '0-0 min')
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
        phase = phases[phase_id]
        critical = "⚠️" if phase.get('critical') else "  "
        print(f"{critical} Phase {phase_id:2d}: {phase['name']:30s} [{phase.get('estimated_time', 'N/A'):>10s}]")


def print_summary(results: Dict[int, bool], start_time: float, dry_run: bool, phases: Optional[Dict[int, dict]] = None):
    """Print execution summary."""
    phases = phases or PHASES
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
        phase_name = phases[phase_id]['name']
        print(f"  {status} | Phase {phase_id:2d}: {phase_name}")

    if dry_run:
        print(f"\n🔍 This was a dry run - no phases were actually executed")

    print()


def run_database_maintenance(db_path: str, run_vacuum: bool = False) -> bool:
    """Run final SQLite maintenance after the selected phase pipeline finishes."""
    import os
    import sqlite3

    if not os.path.exists(db_path):
        print(f"\n⚠️  Database maintenance skipped: database not found at {db_path}")
        return False

    print("\n" + "="*80)
    print("Database Maintenance (数据库维护)")
    print("="*80)
    print(f"Database: {db_path}")

    start_time = time.time()
    conn = sqlite3.connect(db_path)
    try:
        print("\n[1/2] Running ANALYZE...")
        conn.execute("ANALYZE")
        conn.commit()
        print("      [OK] ANALYZE completed")

        print("[2/2] Running PRAGMA optimize...")
        conn.execute("PRAGMA optimize")
        print("      [OK] PRAGMA optimize completed")

        if run_vacuum:
            conn.close()
            conn = None
            print("\n[Optional] Running VACUUM...")
            vacuum_start = time.time()
            vacuum_conn = sqlite3.connect(db_path)
            try:
                vacuum_conn.execute("VACUUM")
            finally:
                vacuum_conn.close()
            print(f"      [OK] VACUUM completed in {time.time() - vacuum_start:.1f}s")
        else:
            print("\n[Optional] VACUUM skipped. Use --vacuum to rebuild and compact the database.")

        elapsed = time.time() - start_time
        print(f"\n✅ Database maintenance completed in {elapsed:.1f}s")
        return True
    except sqlite3.Error as e:
        print(f"\n⚠️  Database maintenance failed: {e}")
        return False
    finally:
        if conn is not None:
            conn.close()


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
        "output_tables": ["广东省自然村_预处理", "metadata_overview_stats", "region_hierarchy_stats", "regional_basic_stats"],
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
        "description": "VTF analysis (9 categories) + semantic intensity indices. Note: semantic_labels is generated separately via LLM-assisted labeling, not by this phase",
        "description_zh": "VTF分析（9类别）+ 语义强度指数。注：semantic_labels通过LLM辅助标注单独生成，不由此阶段生成",
        "group": "core",
        "dependencies": [0, 1],  # Depends on Phase 1 for character embeddings
        "estimated_time": "3-5 min",
        "output_tables": ["semantic_vtf_global", "semantic_indices"],
        "critical": True,
        "use_run_id": True,
        "special_run_id_handling": True  # Requires --char-run-id and --output-run-id
    },
    4: {
        "name": "Spatial Analysis",
        "name_zh": "空间分析",
        "script": "scripts/core/run_spatial_analysis.py",
        "args": [
            "--db-path", "data/villages.db",
            "--multi-resolution",
            "--integrate-tendency"
        ],
        "description": "Multi-resolution spatial clustering: DBSCAN (eps=0.3/0.5/10/20km) + HDBSCAN, KDE hotspots",
        "description_zh": "多分辨率空间聚类：DBSCAN (eps=0.3/0.5/10/20km) + HDBSCAN，KDE热点检测",
        "group": "core",
        "dependencies": [0, 2],
        "estimated_time": "25-50 min",
        "output_tables": ["village_spatial_features", "spatial_clusters", "village_cluster_assignments", "spatial_hotspots", "region_spatial_aggregates", "spatial_tendency_integration"],
        "critical": True,
        "use_run_id": False
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
        "dependencies": [0, 3, 5],  # Depends on Phase 3 (semantic) and Phase 5 (features)
        "estimated_time": "3-5 min",
        "output_tables": ["regional_features", "cluster_assignments", "cluster_profiles"],
        "critical": True,
        "use_run_id": True,
        "special_run_id_handling": True  # Requires --semantic-run-id, --morphology-run-id, --output-run-id
    },
    7: {
        "name": "Feature Materialization (DEPRECATED)",
        "name_zh": "特征物化（已废弃）",
        "script": "scripts/core/fill_aggregates_tables.py",
        "args": [],
        "description": "DEPRECATED: Replaced by real-time SQL GROUP BY + semantic_indices join",
        "description_zh": "已废弃：替换为实时SQL GROUP BY + semantic_indices关联查询",
        "group": "core",
        "dependencies": [],
        "estimated_time": "<1 min",
        "output_tables": [],
        "critical": False,
        "use_run_id": False
    },

    # ========== STATISTICAL PHASES (10) ==========
    # Note: Phase 8 (Tendency Analysis) and Phase 9 (Z-score Normalization) have been removed
    # as these calculations are now performed by Phase 2 (Frequency Analysis) and stored
    # directly in the char_regional_analysis table.
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
        "dependencies": [0, 2],
        "estimated_time": "2-3 min",
        "output_tables": ["char_regional_analysis"],
        "critical": False,
        "use_run_id": True
    },

    # ========== ADVANCED PHASES (11-18) ==========
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
        "output_tables": ["ngram_frequency", "structural_patterns", "village_ngrams"],
        "critical": False,
        "use_run_id": True
    },
    13: {
        "name": "Spatial Hotspots",
        "name_zh": "空间热点",
        "script": "scripts/core/generate_spatial_features.py",
        "args": [
            "--db-path", "data/villages.db",
            "--mode", "hotspots",
            "--hotspot-bandwidth-km", "6.0",
            "--hotspot-threshold-percentile", "80.0",
            "--hotspot-cluster-eps-km", "1.0",
            "--hotspot-cluster-min-samples", "10",
            "--hotspot-sample-size", "0"
        ],
        "description": "KDE-based hotspot detection (8 hotspot regions)",
        "description_zh": "基于KDE的热点检测（8个热点区域）",
        "group": "advanced",
        "dependencies": [0],
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
        "output_tables": ["semantic_bigrams", "semantic_trigrams", "semantic_composition_patterns", "semantic_conflicts", "village_semantic_structure", "semantic_pmi", "semantic_indices_detailed"],
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
        "output_tables": ["region_similarity"],
        "critical": False,
        "use_run_id": True
    },
    16: {
        "name": "Semantic Centrality (DEPRECATED)",
        "name_zh": "语义中心性（已废弃）",
        "script": "scripts/core/phase16_semantic_centrality.py",
        "args": [],
        "description": "DEPRECATED: Real-time compute/compute/semantic/network endpoint replaced offline precomputation",
        "description_zh": "已废弃：实时 /compute/semantic/network 端点替代了离线预计算",
        "group": "advanced",
        "dependencies": [],
        "estimated_time": "<1 min",
        "output_tables": [],
        "critical": False,
        "use_run_id": False
    },
    17: {
        "name": "Hybrid Analysis",
        "name_zh": "混合分析",
        "script": "scripts/core/phase17_semantic_subcategory.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Subcategory VTF analysis (76 subcategories). Note: semantic_subcategory_labels is an intermediate table, not an API output",
        "description_zh": "子类别VTF分析（76个子类别）。注：semantic_subcategory_labels是中间表，非API输出",
        "group": "advanced",
        "dependencies": [0, 1, 3],
        "estimated_time": "3-5 min",
        "output_tables": ["semantic_subcategory_vtf_global", "semantic_subcategory_vtf_regional"],
        "critical": False,
        "use_run_id": True
    },
    18: {
        "name": "Morphology Patterns",
        "name_zh": "形态模式分析",
        "script": "scripts/core/run_morphology.py",
        "args": [
            "--db-path", "data/villages.db"
        ],
        "description": "Extract suffix/prefix patterns, compute frequency and tendency, persist to pattern tables",
        "description_zh": "提取后缀/前缀模式，计算频率和倾向性，写入 pattern_frequency_global 和 pattern_regional_analysis",
        "group": "advanced",
        "dependencies": [0],
        "estimated_time": "3-5 min",
        "output_tables": ["pattern_frequency_global", "pattern_regional_analysis"],
        "critical": False,
        "use_run_id": True
    }
}


def _sync_active_run_ids(db_path, phase_id, run_id, output_run_id):
    """Write active_run_ids records after a phase completes successfully.

    The external backend reads active_run_ids to resolve analysis_type → run_id
    for API queries. Each phase that produces backend-consumed tables must register
    its run_id here.
    """
    import sqlite3
    from src.data.db_writer import create_active_run_ids_table, upsert_active_run_id

    conn = sqlite3.connect(db_path)
    try:
        create_active_run_ids_table(conn)

        if phase_id == 1 and run_id:
            upsert_active_run_id(conn, 'char_embeddings', run_id, 'char_embeddings')
        elif phase_id == 3 and output_run_id:
            upsert_active_run_id(conn, 'semantic_indices', output_run_id, 'semantic_indices')
        elif phase_id == 4:
            upsert_active_run_id(conn, 'spatial_clusters', 'spatial_eps_25', 'spatial_clusters')
            upsert_active_run_id(conn, 'spatial_integration', 'spatial_multi_tendency', 'spatial_tendency_integration')
        elif phase_id == 5 and run_id:
            upsert_active_run_id(conn, 'village_features', run_id, 'village_features')
        elif phase_id == 6 and output_run_id:
            upsert_active_run_id(conn, 'clustering_county', output_run_id, 'cluster_assignments')
        elif phase_id == 10 and run_id:
            upsert_active_run_id(conn, 'char_significance', run_id, 'tendency_significance')
        elif phase_id == 13 and run_id:
            upsert_active_run_id(conn, 'spatial_hotspots', run_id, 'spatial_hotspots')
    finally:
        conn.close()


def build_phase_command(
    phase_id,
    phases: Optional[Dict[int, dict]] = None,
    run_id_prefix="run",
    db_path="data/villages.db",
    now_str: Optional[str] = None,
):
    """Build the subprocess command for one phase."""
    phases = phases or PHASES
    if phase_id not in phases:
        raise KeyError(f"Phase {phase_id} not found")

    phase = phases[phase_id]
    run_id = None
    output_run_id = None
    timestamp = now_str or datetime.now().strftime('%Y%m%d_%H%M%S')
    cmd = [sys.executable, phase['script']]

    if phase.get('special_run_id_handling') and phase_id in (3, 6):
        return cmd, run_id, output_run_id

    if phase.get('use_run_id', True) and phase_id > 0:
        run_id = f"{run_id_prefix}_{phase_id:02d}_{timestamp}"
        cmd.extend(["--run-id", run_id])

    args = phase['args'].copy() if phase['args'] else []
    if '--db-path' in args and db_path != "data/villages.db":
        idx = args.index('--db-path')
        args[idx + 1] = db_path
    cmd.extend(args)

    return cmd, run_id, output_run_id


def run_phase(phase_id, run_id_prefix="run", dry_run=False, db_path="data/villages.db", phases: Optional[Dict[int, dict]] = None):
    """Run a single analysis phase.

    Args:
        phase_id: Phase number to run
        run_id_prefix: Prefix for run ID generation
        dry_run: If True, only show what would be executed
        db_path: Path to database file

    Returns:
        bool: True if phase completed successfully, False otherwise
    """
    phases = phases or PHASES
    if phase_id not in phases:
        print(f"❌ Error: Phase {phase_id} not found")
        return False

    phase = phases[phase_id]

    # Track generated run_ids for active_run_ids sync after success
    run_id = None
    output_run_id = None

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

    # Handle special run ID cases (e.g., Phase 3 needs --char-run-id and --output-run-id)
    if phase.get('special_run_id_handling') and phase_id == 3:
        cmd = [sys.executable, phase['script']]
        if dry_run:
            char_run_id = f"{run_id_prefix}_01_DRYRUN"
            output_run_id = f"{run_id_prefix}_{phase_id:02d}_DRYRUN"
            cmd.extend(["--char-run-id", char_run_id])
            cmd.extend(["--output-run-id", output_run_id])
            print(f"Using char-run-id: {char_run_id}")
            print(f"Output run-id: {output_run_id}")
        else:
            # Phase 3 needs char-run-id from Phase 1
            import sqlite3
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT run_id FROM char_embeddings ORDER BY run_id DESC LIMIT 1")
                result = cursor.fetchone()
                conn.close()

                if result:
                    char_run_id = result[0]
                    output_run_id = f"{run_id_prefix}_{phase_id:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    cmd.extend(["--char-run-id", char_run_id])
                    cmd.extend(["--output-run-id", output_run_id])
                    print(f"Using char-run-id: {char_run_id}")
                    print(f"Output run-id: {output_run_id}")
                else:
                    print(f"❌ Error: No character embeddings found in database. Run Phase 1 first.")
                    return False
            except Exception as e:
                print(f"❌ Error querying database for char-run-id: {e}")
                return False
    # Handle Phase 6 (Clustering) - needs semantic-run-id and morphology-run-id
    elif phase.get('special_run_id_handling') and phase_id == 6:
        cmd = [sys.executable, phase['script']]
        if dry_run:
            semantic_run_id = f"{run_id_prefix}_03_DRYRUN"
            morphology_run_id = f"{run_id_prefix}_18_DRYRUN"
            output_run_id = f"{run_id_prefix}_{phase_id:02d}_DRYRUN"
            cmd.extend(["--semantic-run-id", semantic_run_id])
            cmd.extend(["--morphology-run-id", morphology_run_id])
            cmd.extend(["--output-run-id", output_run_id])
            print(f"Using semantic-run-id: {semantic_run_id}")
            print(f"Using morphology-run-id: {morphology_run_id}")
            print(f"Output run-id: {output_run_id}")
        else:
            import sqlite3
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Get semantic run ID from Phase 3
                cursor.execute("SELECT DISTINCT run_id FROM semantic_vtf_global ORDER BY run_id DESC LIMIT 1")
                semantic_result = cursor.fetchone()

                # Get morphology run ID from Phase 18 (morphology patterns) - use dummy if not available
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_regional_analysis'")
                pattern_table_exists = cursor.fetchone()

                if pattern_table_exists:
                    cursor.execute("PRAGMA table_info(pattern_regional_analysis)")
                    pattern_columns = {row[1] for row in cursor.fetchall()}
                    if "run_id" in pattern_columns:
                        cursor.execute("SELECT DISTINCT run_id FROM pattern_regional_analysis ORDER BY run_id DESC LIMIT 1")
                        morphology_result = cursor.fetchone()
                        morphology_run_id = morphology_result[0] if morphology_result else "dummy_morph"
                    else:
                        morphology_run_id = "dummy_morph"
                        print("⚠️  Warning: pattern_regional_analysis has no run_id column. Using dummy value (morphology features will be skipped).")
                else:
                    morphology_run_id = "dummy_morph"
                    print(f"⚠️  Warning: No morphology data found. Using dummy value (morphology features will be skipped).")

                conn.close()

                if semantic_result:
                    semantic_run_id = semantic_result[0]
                    output_run_id = f"{run_id_prefix}_{phase_id:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    cmd.extend(["--semantic-run-id", semantic_run_id])
                    cmd.extend(["--morphology-run-id", morphology_run_id])
                    cmd.extend(["--output-run-id", output_run_id])
                    print(f"Using semantic-run-id: {semantic_run_id}")
                    print(f"Using morphology-run-id: {morphology_run_id}")
                    print(f"Output run-id: {output_run_id}")
                else:
                    print(f"❌ Error: No semantic analysis data found in database. Run Phase 3 first.")
                    return False
            except Exception as e:
                print(f"❌ Error querying database for run IDs: {e}")
                return False
    else:
        cmd, run_id, output_run_id = build_phase_command(
            phase_id,
            phases=phases,
            run_id_prefix=run_id_prefix,
            db_path=db_path,
        )

    if phase.get('special_run_id_handling') and phase_id in (3, 6):
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
        _sync_active_run_ids(db_path, phase_id, run_id, output_run_id)
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
        help="Run all phases in a specific group (core: 0-7, statistical: 8-10, advanced: 11-18)"
    )

    # Configuration arguments
    config_group = parser.add_argument_group('Configuration (配置选项)')
    config_group.add_argument(
        "--db-path",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to database file (default: data/villages.db)"
    )
    config_group.add_argument(
        "--run-id-prefix",
        type=str,
        default=None,
        metavar="PREFIX",
        help="Prefix for run IDs (default: 'run')"
    )
    config_group.add_argument(
        "--config",
        type=str,
        metavar="PATH",
        help="Path to pipeline profile JSON config"
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
        "--clear",
        action="store_true",
        help="DROP all tables except 广东省自然村 before running. Forces a clean rebuild. (删除除了原始数据之外的所有表)"
    )
    behavior_group.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="Skip dependency checking (advanced users only, 跳过依赖检查)"
    )
    behavior_group.add_argument(
        "--skip-maintenance",
        action="store_true",
        help="Skip final ANALYZE and PRAGMA optimize after execution (跳过退出前数据库维护)"
    )
    behavior_group.add_argument(
        "--vacuum",
        action="store_true",
        help="Run VACUUM during final maintenance. Requires extra disk space and time. (退出前额外执行 VACUUM)"
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

    try:
        config_path = resolve_pipeline_config_path(args.config)
        pipeline_config = load_pipeline_config(config_path)
        phases = merge_phase_definitions(PHASES, pipeline_config)
        retention_policy = retention_policy_from_config(pipeline_config)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1

    if args.db_path is None:
        args.db_path = pipeline_config.get("dataset", {}).get("db_path", "data/villages.db")
    if args.run_id_prefix is None:
        args.run_id_prefix = pipeline_config.get("run", {}).get("run_id_prefix", "run")
    args.config = config_path
    schema_name = pipeline_config.get("dataset", {}).get("schema", "guangdong")
    raw_table_to_keep = get_schema(schema_name).raw_table

    # Handle information queries
    if args.list:
        print_phase_list(phases)
        return 0

    if args.info is not None:
        print_phase_info(args.info, phases)
        return 0

    if args.show_groups:
        print_phase_groups(phases)
        return 0

    # Determine which phases to run
    phases_to_run = []

    if args.all:
        phases_to_run = sorted(phases.keys())
    elif args.group:
        phases_to_run = get_phases_by_group(args.group, phases)
    elif args.phases:
        phases_to_run = parse_phase_list(args.phases)
        if phases_to_run is None:
            return 1
    elif args.vacuum:
        if args.dry_run:
            print(f"\n🔍 --vacuum (dry-run): would run ANALYZE, PRAGMA optimize, and VACUUM on {args.db_path}")
            return 0
        return 0 if run_database_maintenance(args.db_path, run_vacuum=True) else 1
    else:
        parser.print_help()
        return 1

    # Validate phases
    invalid = [p for p in phases_to_run if p not in phases]
    if invalid:
        print(f"❌ Error: Invalid phase IDs: {invalid}")
        print(f"Valid phases: {sorted(phases.keys())}")
        return 1

    # Check dependencies
    if not args.skip_dependencies:
        missing_deps = check_dependencies(phases_to_run, phases)
        if missing_deps:
            print(f"\n⚠️  Warning: Missing dependencies detected!")
            for phase_id, deps in missing_deps.items():
                phase_name = phases[phase_id]['name']
                print(f"  Phase {phase_id} ({phase_name}) requires: {deps}")
            print(f"\n💡 Tip: Add missing phases or use --skip-dependencies to ignore")
            return 1

    # Print execution plan
    print_execution_plan(phases_to_run, args, phases)

    # Handle --clear: drop all tables except raw data
    if args.clear and not args.dry_run:
        import sqlite3 as _sqlite3
        print("\n" + "=" * 60)
        print(f"CLEAR MODE: 清除所有衍生表（保留 {raw_table_to_keep}）")
        print("=" * 60)

        _conn = _sqlite3.connect(args.db_path)
        _cursor = _conn.cursor()
        _cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != ? AND name NOT LIKE 'sqlite_%'",
            (raw_table_to_keep,),
        )
        tables_to_drop = [r[0] for r in _cursor.fetchall()]

        if tables_to_drop:
            print(f"将删除 {len(tables_to_drop)} 张表:")
            for t in sorted(tables_to_drop):
                _cursor.execute(f"SELECT COUNT(*) FROM \"{t}\"")
                cnt = _cursor.fetchone()[0]
                print(f"  - {t:45s} ({cnt:,} rows)")

            print(f"\n⚠️  这不可逆！数据将永久丢失。")
            response = input("确认删除？输入 'yes' 继续: ")
            if response == 'yes':
                for t in tables_to_drop:
                    _cursor.execute(f"DROP TABLE \"{t}\"")
                _conn.commit()
                print(f"[OK] 已删除 {len(tables_to_drop)} 张表，保留 {raw_table_to_keep}")
            else:
                print("已取消。")
                _conn.close()
                return 0
        else:
            print("没有可清除的表。")
        _conn.close()
    elif args.clear and args.dry_run:
        import sqlite3 as _sqlite3
        if not Path(args.db_path).exists():
            print(f"\n🔍 --clear (dry-run): 将会删除 0 张衍生表，保留 {raw_table_to_keep}")
        else:
            _conn = _sqlite3.connect(args.db_path)
            _cursor = _conn.cursor()
            _cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != ? AND name NOT LIKE 'sqlite_%'",
                (raw_table_to_keep,),
            )
            tables_to_drop = [r[0] for r in _cursor.fetchall()]
            print(f"\n🔍 --clear (dry-run): 将会删除 {len(tables_to_drop)} 张衍生表，保留 {raw_table_to_keep}")
            _conn.close()

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
        success = run_phase(phase_id, args.run_id_prefix, args.dry_run, args.db_path, phases)
        results[phase_id] = success

        if not success and not args.dry_run:
            if args.continue_on_error:
                print(f"\n⚠️  Phase {phase_id} failed, but continuing due to --continue-on-error")
            else:
                print(f"\n⏹️  Phase {phase_id} failed. Stopping execution.")
                print(f"💡 Tip: Use --continue-on-error to skip failed phases")
                break

    # Print summary
    print_summary(results, overall_start, args.dry_run, phases)

    if retention_policy.enabled and results and all(results.values()):
        retention_result = apply_retention_policy(args.db_path, retention_policy, dry_run=args.dry_run)
        label = "Compact retention (dry-run)" if args.dry_run else "Compact retention"
        print(f"\n{label}:")
        if args.dry_run:
            print(f"  Would drop {len(retention_policy.drop_tables) - len(retention_result.missing_tables)} configured table(s):")
            for table in retention_policy.drop_tables:
                if table not in retention_result.missing_tables:
                    print(f"  - {table}")
        else:
            print(f"  Dropped {len(retention_result.dropped_tables)} table(s):")
            for table in retention_result.dropped_tables:
                print(f"  - {table}")
        if retention_result.missing_tables:
            print(f"  Missing/skipped {len(retention_result.missing_tables)} configured table(s):")
            for table in retention_result.missing_tables:
                print(f"  - {table}")

    if not args.dry_run and results and not args.skip_maintenance:
        run_database_maintenance(args.db_path, run_vacuum=args.vacuum)
    elif args.skip_maintenance:
        print("\n⚠️  Final database maintenance skipped due to --skip-maintenance")

    # Return exit code
    all_success = all(results.values())
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
