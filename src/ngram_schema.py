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
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (level, city, county, township, ngram, n, position)
        )
    """,

    'ngram_tendency': """
        CREATE TABLE IF NOT EXISTS ngram_tendency (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            lift REAL NOT NULL,
            log_odds REAL NOT NULL,
            z_score REAL NOT NULL,
            regional_count INTEGER NOT NULL,
            regional_total INTEGER NOT NULL,
            regional_total_raw INTEGER,
            global_count INTEGER NOT NULL,
            global_total INTEGER NOT NULL,
            PRIMARY KEY (level, city, county, township, ngram, n, position)
        )
    """,

    'ngram_significance': """
        CREATE TABLE IF NOT EXISTS ngram_significance (
            level TEXT NOT NULL,
            city TEXT,
            county TEXT,
            township TEXT,
            region TEXT NOT NULL,
            ngram TEXT NOT NULL,
            n INTEGER NOT NULL,
            position TEXT NOT NULL,
            chi2 REAL NOT NULL,
            p_value REAL NOT NULL,
            cramers_v REAL NOT NULL,
            is_significant INTEGER NOT NULL,
            total_before_filter INTEGER,
            PRIMARY KEY (level, city, county, township, ngram, n, position)
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
            village_id TEXT NOT NULL,
            村委会 TEXT,
            自然村 TEXT,
            n INTEGER NOT NULL,
            bigrams TEXT,
            trigrams TEXT,
            prefix_bigram TEXT,
            suffix_bigram TEXT,
            prefix_trigram TEXT,
            suffix_trigram TEXT,
            PRIMARY KEY (village_id, n)
        )
    """
}

# Indexes for faster queries
# Keep this list small: production storage is constrained, so each index should
# match a stable backend query shape instead of covering speculative access.
NGRAM_INDEXES = [
    ("ngram_frequency", "CREATE INDEX IF NOT EXISTS idx_ngram_freq_ngram ON ngram_frequency(ngram)"),
    ("ngram_frequency", "CREATE INDEX IF NOT EXISTS idx_ngram_freq_n_position_frequency ON ngram_frequency(n, position, frequency DESC)"),
    ("regional_ngram_frequency", "CREATE INDEX IF NOT EXISTS idx_regional_ngram_level_n_region_freq ON regional_ngram_frequency(level, n, region, frequency DESC)"),
    ("regional_ngram_frequency", "CREATE INDEX IF NOT EXISTS idx_regional_ngram_level ON regional_ngram_frequency(level)"),
    ("regional_ngram_frequency", "CREATE INDEX IF NOT EXISTS idx_regional_ngram_region ON regional_ngram_frequency(region)"),
    ("regional_ngram_frequency", "CREATE INDEX IF NOT EXISTS idx_regional_ngram_ngram ON regional_ngram_frequency(ngram)"),
    ("ngram_tendency", "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_level ON ngram_tendency(level)"),
    ("ngram_tendency", "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_level_region_lift ON ngram_tendency(level, region, lift DESC)"),
    ("ngram_tendency", "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_level_lift ON ngram_tendency(level, lift DESC)"),
    ("ngram_tendency", "CREATE INDEX IF NOT EXISTS idx_ngram_tendency_zscore ON ngram_tendency(z_score DESC)"),
    ("ngram_significance", "CREATE INDEX IF NOT EXISTS idx_ngram_sig_level ON ngram_significance(level)"),
    ("ngram_significance", "CREATE INDEX IF NOT EXISTS idx_ngram_sig_pvalue ON ngram_significance(p_value)"),
    ("structural_patterns", "CREATE INDEX IF NOT EXISTS idx_structural_patterns_type ON structural_patterns(pattern_type)"),
    ("village_ngrams", "CREATE INDEX IF NOT EXISTS idx_village_ngrams_id ON village_ngrams(village_id)"),
]


def create_ngram_tables(db_path: str = 'data/villages.db', exclude_tables: set[str] | None = None):
    """Create all n-gram analysis tables."""
    import sqlite3

    exclude_tables = exclude_tables or set()
    conn = sqlite3.connect(db_path, timeout=60.0)
    cursor = conn.cursor()

    # Create tables
    for table_name, schema in NGRAM_SCHEMA.items():
        if table_name in exclude_tables:
            print(f"Skipping table: {table_name}")
            continue
        print(f"Creating table: {table_name}")
        cursor.execute(schema)

    # Create indexes
    for table_name, index_sql in NGRAM_INDEXES:
        if table_name in exclude_tables:
            continue
        print(f"Creating index...")
        cursor.execute(index_sql)

    conn.commit()
    conn.close()
    print("All n-gram tables created successfully!")


if __name__ == '__main__':
    create_ngram_tables()
