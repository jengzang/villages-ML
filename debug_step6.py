"""Debug step6 village semantic structure extraction."""
import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.semantic_composition import SemanticCompositionAnalyzer

db_path = 'data/villages.db'

with SemanticCompositionAnalyzer(db_path) as analyzer:
    char_labels = analyzer.get_character_labels()
    print(f"[INFO] Loaded {len(char_labels)} character labels")
    print(f"[INFO] Sample labels: {list(char_labels.items())[:10]}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query from preprocessed table
    cursor.execute("""
        SELECT village_id, 村委会, 自然村_去前缀
        FROM 广东省自然村_预处理
        WHERE 有效 = 1
        LIMIT 100
    """)

    count = 0
    skipped = 0
    processed_villages = []

    for row in cursor:
        village_id = row[0]
        village_committee = row[1]
        village_name = row[2]

        if not village_name or not village_id:
            continue

        sequence = analyzer.extract_semantic_sequence(village_name, char_labels)

        if len(sequence) == 0:
            skipped += 1
            continue

        # Calculate labeling coverage
        labeled_count = sum(1 for cat in sequence if cat != 'other')
        coverage = labeled_count / len(sequence) if len(sequence) > 0 else 0

        # Only process villages with at least 50% labeled characters
        if coverage < 0.5:
            skipped += 1
            continue

        count += 1
        processed_villages.append({
            'village_id': village_id,
            'village_name': village_name,
            'sequence': sequence,
            'coverage': coverage
        })

    print(f"\n[INFO] Processed {count} villages (skipped {skipped})")
    print(f"\n[INFO] Sample processed villages:")
    for v in processed_villages[:5]:
        print(f"  {v['village_id']}: {v['village_name']} -> {v['sequence']} (coverage: {v['coverage']:.2%})")

    conn.close()
