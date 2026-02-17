"""
Database schema for N-gram analysis results.

Tables:
1. ngram_frequency - Global n-gram frequencies
2. regional_ngram_frequency - Regional n-gram frequencies
3. ngram_tendency - Tendency scores (lift, log-odds, z-score)
4. ngram_significance - Statistical significance tests
5. structural_patterns - Identified templates and patterns
6. village_ngrams - Per-village n-gram features
"""

NGRAM_SCHEMA = {
    'ngram_frequency': """
        CREATE TABLE IF NOT EXISTS ngram_frequency (
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (ngram, n, position)
        )
    """,

    'regional_ngram_frequency': """
        CREATE TABLE IF NOT EXISTS regional_ngram_frequency (
            region TEXT NOT NULL,
            level TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (region, level, ngram, n, position)
        )
    """,

    'ngram_tendency': """
        CREATE TABLE IF NOT EXISTS ngram_tendency (
            region TEXT NOT NULL,
            level TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL NOT NULL,
            regional_count INTEGER NOT NULL,
            regional_total INTEGER NOT NULL,
            global_count INTEGER NOT NULL,
            global_total INTEGER NOT NULL,
            PRIMARY KEY (region, level, ngram, n, position)
        )
    """,

    'ngram_significance': """
        CREATE TABLE IF NOT EXISTS ngram_significance (
            region TEXT NOT NULL,
            level TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            chi2 REAL NOT NULL,
            p_value REAL NOT NULL,
            cramers_v REAL NOT NULL,
            is_significant INTEGER NOT NULL,
            PRIMARY KEY (region, level, ngram, n, position)
        )
    """,

    'structural_patterns': """
        CREATE TABLE IF NOT EXISTS structural_patterns (
            pattern TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            example TEXT NOT NULL,
            description TEXT,
            PRIMARY KEY (pattern, pattern_type, n, position)
        )
    """,

    'village_ngrams': """
        CREATE TABLE IF NOT EXISTS village_ngrams (
            村委会 TEXT NOT NULL,
            自然村 TEXT NOT NULL,
            n INTEGER NOT NULL,
            bigrams TEXT,
            trigrams TEXT,
            prefix_bigram TEXT,
            suffix_bigram TEXT,
            prefix_trigram TEXT,
            suffix_trigram TEXT,
            PRIMARY KEY (村委会, 自然村, n)
        )
    """
}

# Indexes for faster queries
NGRAM_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ngram_freq_ngram ON ngram_frequency(ngram)",
    "CREATE INDEX IF NOT EXISTS idx_ngram_freq_n ON ngram_frequency(n)",
    "CREATE INDEX IF NOT EXISTS idx_regional_ngram_region ON regional_ngram_frequency(region)",
    "CREATE INDEX IF NOT EXISTS idx_regional_ngram_ngram ON regional_ngram_frequency(ngram)",
    "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_region ON ngram_tendency(region)",
    "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_lift ON ngram_tendency(lift DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_zscore ON ngram_tendency(z_score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ngram_sig_pvalue ON ngram_significance(p_value)",
    "CREATE INDEX IF NOT EXISTS idx_structural_patterns_type ON structural_patterns(pattern_type)",
]


def create_ngram_tables(db_path: str = 'data/villages.db'):
    """Create all n-gram analysis tables."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    for table_name, schema in NGRAM_SCHEMA.items():
        print(f"Creating table: {table_name}")
        cursor.execute(schema)

    # Create indexes
    for index_sql in NGRAM_INDEXES:
        print(f"Creating index...")
        cursor.execute(index_sql)

    conn.commit()
    conn.close()
    print("All n-gram tables created successfully!")


if __name__ == '__main__':
    create_ngram_tables()
