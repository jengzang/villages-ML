"""
创建 active_run_ids 表并初始化数据

此脚本将 run_id 配置从代码迁移到数据库，实现动态管理。
"""

import sqlite3
import time
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def create_active_run_ids_table(db_path: str):
    """创建 active_run_ids 表并初始化数据"""

    print(f"连接数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建表
    print("创建 active_run_ids 表...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_run_ids (
            analysis_type TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            table_name TEXT NOT NULL,
            updated_at REAL NOT NULL,
            updated_by TEXT,
            notes TEXT,
            UNIQUE(analysis_type)
        )
    """)

    # 初始化数据（从当前硬编码值迁移）
    print("初始化数据（从硬编码值迁移）...")
    current_time = time.time()

    initial_data = [
        ("char_frequency", "freq_final_001", "char_frequency_global", current_time, "migration", "从config.py迁移"),
        ("char_embeddings", "embed_final_001", "char_embeddings", current_time, "migration", "从endpoints迁移"),
        ("char_significance", "test_sig_1771260439", "tendency_significance", current_time, "migration", "从endpoints迁移"),
        ("clustering_county", "cluster_001", "cluster_assignments", current_time, "migration", "从config.py迁移"),
        ("ngrams", "ngram_001", "village_ngrams", current_time, "migration", "从endpoints迁移"),
        ("patterns", "morph_001", "pattern_tendency", current_time, "migration", "从endpoints迁移"),
        ("semantic", "semantic_001", "semantic_labels", current_time, "migration", "从config.py迁移"),
        ("spatial_hotspots", "final_03_20260219_225259", "spatial_hotspots", current_time, "migration", "从endpoints迁移"),
        ("spatial_integration", "integration_final_001", "spatial_tendency_integration", current_time, "migration", "从endpoints迁移"),
        ("village_features", "default", "village_features", current_time, "migration", "从endpoints迁移"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO active_run_ids
        (analysis_type, run_id, table_name, updated_at, updated_by, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, initial_data)

    conn.commit()

    # 验证数据
    print("\n验证插入的数据:")
    cursor.execute("SELECT * FROM active_run_ids ORDER BY analysis_type")
    rows = cursor.fetchall()

    print(f"\n共插入 {len(rows)} 条记录:\n")
    print(f"{'分析类型':<25} {'Run ID':<30} {'数据表':<30}")
    print("-" * 85)
    for row in rows:
        print(f"{row[0]:<25} {row[1]:<30} {row[2]:<30}")

    conn.close()
    print(f"\n[SUCCESS] active_run_ids 表创建成功！")


if __name__ == "__main__":
    db_path = "data/villages.db"
    create_active_run_ids_table(db_path)
