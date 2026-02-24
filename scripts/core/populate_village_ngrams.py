#!/usr/bin/env python3
"""
Populate village_ngrams table.

This script extracts n-grams for each village and stores them in the village_ngrams table.
This enables per-village n-gram queries for the API.

Usage:
    python scripts/core/populate_village_ngrams.py
"""

import sqlite3
import sys
from pathlib import Path
import json
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ngram_analysis import NgramExtractor


def populate_village_ngrams(db_path: str = 'data/villages.db', batch_size: int = 1000):
    """
    Populate village_ngrams table with per-village n-gram data.

    Args:
        db_path: Path to database
        batch_size: Number of villages to process in each batch
    """
    print("\\n" + "="*60)
    print("Populating village_ngrams Table")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get total count for progress bar
    cursor.execute("""
        SELECT COUNT(*) FROM 广东省自然村_预处理 WHERE 有效 = 1
    """)
    total_villages = cursor.fetchone()[0]
    print(f"\\nProcessing {total_villages:,} villages...")

    # Load villages in batches
    cursor.execute("""
        SELECT village_id, 村委会, 自然村_去前缀
        FROM 广东省自然村_预处理
        WHERE 有效 = 1
    """)

    # Fetch all villages first to avoid cursor issues
    villages = cursor.fetchall()
    print(f"Loaded {len(villages):,} villages from database")

    batch = []
    processed = 0
    insert_cursor = conn.cursor()  # Separate cursor for inserts

    with tqdm(total=len(villages), desc="Extracting n-grams") as pbar:
        for row in villages:
            village_id, village_committee, village_name = row

            # Skip if either field is NULL
            if not village_name or not village_committee or not village_id:
                pbar.update(1)
                continue

            # Extract bigrams
            bigrams_pos = NgramExtractor.extract_positional_ngrams(village_name, n=2)
            bigrams_all = bigrams_pos['all']
            prefix_bigram = bigrams_pos['prefix'][0] if bigrams_pos['prefix'] else None
            suffix_bigram = bigrams_pos['suffix'][0] if bigrams_pos['suffix'] else None

            # Extract trigrams
            trigrams_pos = NgramExtractor.extract_positional_ngrams(village_name, n=3)
            trigrams_all = trigrams_pos['all']
            prefix_trigram = trigrams_pos['prefix'][0] if trigrams_pos['prefix'] else None
            suffix_trigram = trigrams_pos['suffix'][0] if trigrams_pos['suffix'] else None

            # Convert lists to JSON strings
            bigrams_json = json.dumps(bigrams_all, ensure_ascii=False) if bigrams_all else None
            trigrams_json = json.dumps(trigrams_all, ensure_ascii=False) if trigrams_all else None

            batch.append((
                village_id,
                village_committee,
                village_name,
                2,  # n for bigrams
                bigrams_json,
                trigrams_json,
                prefix_bigram,
                suffix_bigram,
                prefix_trigram,
                suffix_trigram
            ))

            processed += 1
            pbar.update(1)

            # Insert batch when it reaches batch_size
            if len(batch) >= batch_size:
                insert_cursor.executemany("""
                    INSERT OR REPLACE INTO village_ngrams
                    (village_id, 村委会, 自然村, n, bigrams, trigrams, prefix_bigram, suffix_bigram, prefix_trigram, suffix_trigram)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch = []

    # Insert remaining batch
    if batch:
        insert_cursor.executemany("""
            INSERT OR REPLACE INTO village_ngrams
            (village_id, 村委会, 自然村, n, bigrams, trigrams, prefix_bigram, suffix_bigram, prefix_trigram, suffix_trigram)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()

    # Verify results
    cursor.execute("SELECT COUNT(*) FROM village_ngrams")
    count = cursor.fetchone()[0]

    print(f"\\n[OK] Populated village_ngrams table with {count:,} records")

    conn.close()


if __name__ == '__main__':
    populate_village_ngrams()
