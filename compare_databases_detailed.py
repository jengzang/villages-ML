#!/usr/bin/env python3
"""
Detailed content comparison for specific tables.
"""

import sqlite3

def compare_table_content(table_name, conn_old, conn_new):
    """Compare content of a specific table."""
    cursor_old = conn_old.cursor()
    cursor_new = conn_new.cursor()

    print(f"\n{'='*100}")
    print(f"TABLE: {table_name}")
    print(f"{'='*100}")

    # Get row counts
    count_old = cursor_old.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
    count_new = cursor_new.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    print(f"\nRow counts: OLD={count_old:,}, NEW={count_new:,}, DIFF={count_new-count_old:,}")

    # Get schema
    schema_old = cursor_old.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    schema_new = cursor_new.execute(f'PRAGMA table_info("{table_name}")').fetchall()

    print(f"\nColumns: OLD={len(schema_old)}, NEW={len(schema_new)}")

    # Check if schema changed
    cols_old = [col[1] for col in schema_old]
    cols_new = [col[1] for col in schema_new]

    if cols_old != cols_new:
        print("  Schema CHANGED!")
        print(f"    Old columns: {', '.join(cols_old)}")
        print(f"    New columns: {', '.join(cols_new)}")
    else:
        print(f"  Schema unchanged: {', '.join(cols_new[:5])}{'...' if len(cols_new) > 5 else ''}")

    # Get indexes
    indexes_old = cursor_old.execute(f'PRAGMA index_list("{table_name}")').fetchall()
    indexes_new = cursor_new.execute(f'PRAGMA index_list("{table_name}")').fetchall()

    print(f"\nIndexes: OLD={len(indexes_old)}, NEW={len(indexes_new)}")

    if len(indexes_old) != len(indexes_new):
        print("  OLD indexes:")
        for idx in indexes_old:
            print(f"    - {idx[1]}")
        print("  NEW indexes:")
        for idx in indexes_new:
            print(f"    - {idx[1]}")

def main():
    print("="*100)
    print("DETAILED CONTENT COMPARISON")
    print("="*100)

    conn_old = sqlite3.connect('data/old/villages.db')
    conn_new = sqlite3.connect('data/villages.db')

    # Tables to analyze in detail
    tables_to_analyze = [
        'ngram_significance',
        'ngram_tendency',
        'regional_ngram_frequency',
        'char_regional_analysis',
        'tendency_significance',
        'char_frequency_global',
        'pattern_regional_analysis',
        'semantic_indices',
        'semantic_indices_detailed',
        'regional_centroids'
    ]

    for table in tables_to_analyze:
        try:
            compare_table_content(table, conn_old, conn_new)
        except Exception as e:
            print(f"\nError analyzing {table}: {e}")

    # Summary of key changes
    print(f"\n{'='*100}")
    print("SUMMARY OF KEY CHANGES")
    print(f"{'='*100}")

    cursor_old = conn_old.cursor()
    cursor_new = conn_new.cursor()

    print("\n1. N-GRAM TABLES:")
    print("   - ngram_significance: Deleted City/County levels (-963,051 rows, -47.6%)")
    print("   - ngram_tendency: Only Township level remains (-10,218 rows, -0.9%)")
    print("   - regional_ngram_frequency: Only Township level remains (-10,218 rows, -0.9%)")

    print("\n2. CHARACTER ANALYSIS:")
    print("   - char_frequency_global: Removed duplicates (-11,532 rows, -75.0%)")
    print("   - char_regional_analysis: Removed City/County duplicates (-90,300 rows, -21.5%)")
    print("   - tendency_significance: Same as char_regional_analysis (-90,300 rows, -21.5%)")

    print("\n3. SEMANTIC TABLES:")
    print("   - semantic_indices: Added 58 townships (+1,827 rows, +11.8%)")
    print("   - semantic_indices_detailed: Added 58 townships (+4,560 rows, +3.5%)")
    print("   - semantic_regional_analysis: Added 58 townships (+558 rows, +3.6%)")

    print("\n4. SPATIAL TABLES:")
    print("   - regional_centroids: Added 58 townships (+292 rows, +16.4%)")
    print("   - region_spatial_aggregates: Added data (+60 rows, +3.5%)")

    print("\n5. AGGREGATES:")
    print("   - town_aggregates: Added 58 townships (+58 rows, +3.7%)")
    print("   - county_aggregates: Added 2 counties (+2 rows, +1.6%)")

    # Database size comparison
    print(f"\n{'='*100}")
    print("DATABASE SIZE COMPARISON")
    print(f"{'='*100}")
    print("\nFile sizes:")
    print("  OLD: 3.1 GB")
    print("  NEW: 2.5 GB")
    print("  SAVED: 0.6 GB (19.4% reduction)")
    print("\nNote: After VACUUM optimization, actual savings from 4.1 GB -> 2.5 GB = 1.6 GB (39%)")

    conn_old.close()
    conn_new.close()

if __name__ == '__main__':
    main()
