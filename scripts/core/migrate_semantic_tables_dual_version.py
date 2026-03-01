#!/usr/bin/env python3
"""
迁移语义表到双版本架构

将现有的细分类别表备份，然后生成两套表：
1. 基础表（9大类）- semantic_bigrams, semantic_trigrams, semantic_pmi
2. 详细表（细分类别）- semantic_bigrams_detailed, semantic_trigrams_detailed, semantic_pmi_detailed

作者：Claude Code
日期：2026-02-25
"""

import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.semantic_composition import SemanticCompositionAnalyzer


def step1_backup_current_tables(db_path: str):
    """Step 1: 备份当前的细分类别表"""
    print("\n" + "=" * 60)
    print("Step 1: 备份当前表")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables_to_backup = [
        'semantic_bigrams',
        'semantic_trigrams',
        'semantic_composition_patterns',
        'semantic_conflicts'
    ]

    for table in tables_to_backup:
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone():
            # Drop backup if exists
            cursor.execute(f"DROP TABLE IF EXISTS {table}_v3_backup")

            # Create backup
            cursor.execute(f"CREATE TABLE {table}_v3_backup AS SELECT * FROM {table}")

            # Get count
            cursor.execute(f"SELECT COUNT(*) FROM {table}_v3_backup")
            count = cursor.fetchone()[0]

            print(f"[OK] Backed up {table} -> {table}_v3_backup ({count:,} records)")
        else:
            print(f"[WARNING] {table} does not exist, skipping")

    conn.commit()
    conn.close()
    print("\n[OK] Backup complete")


def step2_generate_basic_tables(db_path: str):
    """Step 2: 生成基础表（9大类，v1词典）"""
    print("\n" + "=" * 60)
    print("Step 2: 生成基础表（9大类）")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Use v1 lexicon for basic tables
    lexicon_v1 = str(project_root / 'data' / 'semantic_lexicon_v1.json')

    with SemanticCompositionAnalyzer(db_path, lexicon_path=lexicon_v1) as analyzer:
        print("\n提取语义组合（v1 - 9大类）...")
        compositions = analyzer.analyze_all_compositions()

        # Clear existing tables
        cursor.execute("DELETE FROM semantic_bigrams")
        cursor.execute("DELETE FROM semantic_trigrams")

        # Store bigrams
        print("存储 semantic_bigrams...")
        bigrams = compositions['bigrams']
        total_bigrams = sum(bigrams.values())

        for (cat1, cat2), freq in bigrams.items():
            percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_bigrams
                (category1, category2, frequency, percentage)
                VALUES (?, ?, ?, ?)
            """, (cat1, cat2, freq, percentage))

        # Store trigrams
        print("存储 semantic_trigrams...")
        trigrams = compositions['trigrams']
        total_trigrams = sum(trigrams.values())

        for (cat1, cat2, cat3), freq in trigrams.items():
            percentage = (freq / total_trigrams * 100) if total_trigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_trigrams
                (category1, category2, category3, frequency, percentage)
                VALUES (?, ?, ?, ?, ?)
            """, (cat1, cat2, cat3, freq, percentage))

        conn.commit()

        print(f"\n[OK] 生成 {len(bigrams):,} 个 bigrams（9大类）")
        print(f"[OK] 生成 {len(trigrams):,} 个 trigrams（9大类）")

    # Calculate PMI for basic tables
    print("\n计算 PMI（9大类）...")
    import math
    from collections import Counter

    cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams")
    bigrams = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}

    cat1_freq = Counter()
    cat2_freq = Counter()
    total_freq = 0

    for (cat1, cat2), freq in bigrams.items():
        cat1_freq[cat1] += freq
        cat2_freq[cat2] += freq
        total_freq += freq

    for (cat1, cat2), freq in bigrams.items():
        p_joint = freq / total_freq
        p_cat1 = cat1_freq[cat1] / total_freq
        p_cat2 = cat2_freq[cat2] / total_freq
        p_independent = p_cat1 * p_cat2

        if p_independent > 0:
            pmi = math.log(p_joint / p_independent)
        else:
            pmi = 0.0

        cursor.execute("""
            UPDATE semantic_bigrams
            SET pmi = ?
            WHERE category1 = ? AND category2 = ?
        """, (pmi, cat1, cat2))

    conn.commit()
    print("[OK] PMI 计算完成")

    conn.close()


def step3_generate_detailed_tables(db_path: str):
    """Step 3: 生成详细表（76子类别，v4_hybrid词典）"""
    print("\n" + "=" * 60)
    print("Step 3: 生成详细表（76子类别）")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create detailed tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_bigrams_detailed (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            pmi REAL,
            PRIMARY KEY (category1, category2)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_trigrams_detailed (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            category3 TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (category1, category2, category3)
        )
    """)

    conn.commit()

    # Use v4_hybrid lexicon for detailed tables
    lexicon_v4 = str(project_root / 'data' / 'semantic_lexicon_v4_hybrid.json')

    with SemanticCompositionAnalyzer(db_path, lexicon_path=lexicon_v4) as analyzer:
        print("\n提取语义组合（v4_hybrid - 76子类别）...")
        compositions = analyzer.analyze_all_compositions()

        # Clear existing detailed tables
        cursor.execute("DELETE FROM semantic_bigrams_detailed")
        cursor.execute("DELETE FROM semantic_trigrams_detailed")

        # Store bigrams
        print("存储 semantic_bigrams_detailed...")
        bigrams = compositions['bigrams']
        total_bigrams = sum(bigrams.values())

        for (cat1, cat2), freq in bigrams.items():
            percentage = (freq / total_bigrams * 100) if total_bigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_bigrams_detailed
                (category1, category2, frequency, percentage)
                VALUES (?, ?, ?, ?)
            """, (cat1, cat2, freq, percentage))

        # Store trigrams
        print("存储 semantic_trigrams_detailed...")
        trigrams = compositions['trigrams']
        total_trigrams = sum(trigrams.values())

        for (cat1, cat2, cat3), freq in trigrams.items():
            percentage = (freq / total_trigrams * 100) if total_trigrams > 0 else 0
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_trigrams_detailed
                (category1, category2, category3, frequency, percentage)
                VALUES (?, ?, ?, ?, ?)
            """, (cat1, cat2, cat3, freq, percentage))

        conn.commit()

        print(f"\n[OK] 生成 {len(bigrams):,} 个 bigrams（76子类别）")
        print(f"[OK] 生成 {len(trigrams):,} 个 trigrams（76子类别）")

    # Calculate PMI for detailed tables
    print("\n计算 PMI（76子类别）...")
    import math
    from collections import Counter

    cursor.execute("SELECT category1, category2, frequency FROM semantic_bigrams_detailed")
    bigrams = {(cat1, cat2): freq for cat1, cat2, freq in cursor.fetchall()}

    cat1_freq = Counter()
    cat2_freq = Counter()
    total_freq = 0

    for (cat1, cat2), freq in bigrams.items():
        cat1_freq[cat1] += freq
        cat2_freq[cat2] += freq
        total_freq += freq

    for (cat1, cat2), freq in bigrams.items():
        p_joint = freq / total_freq
        p_cat1 = cat1_freq[cat1] / total_freq
        p_cat2 = cat2_freq[cat2] / total_freq
        p_independent = p_cat1 * p_cat2

        if p_independent > 0:
            pmi = math.log(p_joint / p_independent)
        else:
            pmi = 0.0

        cursor.execute("""
            UPDATE semantic_bigrams_detailed
            SET pmi = ?
            WHERE category1 = ? AND category2 = ?
        """, (pmi, cat1, cat2))

    conn.commit()
    print("[OK] PMI 计算完成")

    conn.close()


def step4_verify_results(db_path: str):
    """Step 4: 验证结果"""
    print("\n" + "=" * 60)
    print("Step 4: 验证结果")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = [
        ('semantic_bigrams', '9大类'),
        ('semantic_bigrams_detailed', '76子类别'),
        ('semantic_trigrams', '9大类'),
        ('semantic_trigrams_detailed', '76子类别')
    ]

    print("\n表记录统计：")
    for table, desc in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        # Get sample categories
        if 'bigrams' in table:
            cursor.execute(f"SELECT DISTINCT category1 FROM {table} LIMIT 3")
            samples = [row[0] for row in cursor.fetchall()]
            print(f"  {table} ({desc}): {count:,} records")
            print(f"    Sample: {samples}")
        else:
            print(f"  {table} ({desc}): {count:,} records")

    # Check PMI
    print("\nPMI 统计：")
    for table in ['semantic_bigrams', 'semantic_bigrams_detailed']:
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pmi IS NULL THEN 1 ELSE 0 END) as null_count,
                ROUND(MIN(pmi), 2) as min_pmi,
                ROUND(MAX(pmi), 2) as max_pmi
            FROM {table}
        """)
        total, null_count, min_pmi, max_pmi = cursor.fetchone()
        print(f"  {table}: {total - null_count}/{total} 有PMI值 (范围: {min_pmi} ~ {max_pmi})")

    conn.close()


def main():
    db_path = str(project_root / 'data' / 'villages.db')

    print("=" * 60)
    print("语义表双版本迁移")
    print("=" * 60)
    print(f"Database: {db_path}\n")

    try:
        step1_backup_current_tables(db_path)
        step2_generate_basic_tables(db_path)
        step3_generate_detailed_tables(db_path)
        step4_verify_results(db_path)

        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)
        print("\n现在您有两套表：")
        print("  基础表（9大类）：semantic_bigrams, semantic_trigrams")
        print("  详细表（76子类别）：semantic_bigrams_detailed, semantic_trigrams_detailed")
        print("\n原有数据已备份到 *_v3_backup 表")

    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
