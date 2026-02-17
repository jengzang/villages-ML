"""
Database schema for Semantic Composition Analysis (Phase 14).

Tables:
1. semantic_bigrams - Semantic category bigrams
2. semantic_trigrams - Semantic category trigrams
3. semantic_composition_patterns - Common composition patterns
4. semantic_conflicts - Unusual/conflicting combinations
5. village_semantic_structure - Per-village semantic structure
6. semantic_pmi - PMI scores for category pairs
"""

SEMANTIC_COMPOSITION_SCHEMA = {
    'semantic_bigrams': """
        CREATE TABLE IF NOT EXISTS semantic_bigrams (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            pmi REAL,
            PRIMARY KEY (category1, category2)
        )
    """,

    'semantic_trigrams': """
        CREATE TABLE IF NOT EXISTS semantic_trigrams (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            category3 TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (category1, category2, category3)
        )
    """,

    'semantic_composition_patterns': """
        CREATE TABLE IF NOT EXISTS semantic_composition_patterns (
            pattern TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            modifier TEXT,
            head TEXT,
            frequency INTEGER NOT NULL,
            percentage REAL NOT NULL,
            description TEXT,
            PRIMARY KEY (pattern, pattern_type)
        )
    """,

    'semantic_conflicts': """
        CREATE TABLE IF NOT EXISTS semantic_conflicts (
            sequence TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            conflict_type TEXT NOT NULL,
            description TEXT,
            PRIMARY KEY (sequence, conflict_type)
        )
    """,

    'village_semantic_structure': """
        CREATE TABLE IF NOT EXISTS village_semantic_structure (
            村委会 TEXT NOT NULL,
            自然村 TEXT NOT NULL,
            semantic_sequence TEXT NOT NULL,
            sequence_length INTEGER NOT NULL,
            has_modifier INTEGER NOT NULL,
            has_head INTEGER NOT NULL,
            has_settlement INTEGER NOT NULL,
            PRIMARY KEY (村委会, 自然村)
        )
    """,

    'semantic_pmi': """
        CREATE TABLE IF NOT EXISTS semantic_pmi (
            category1 TEXT NOT NULL,
            category2 TEXT NOT NULL,
            pmi REAL NOT NULL,
            frequency INTEGER NOT NULL,
            is_positive INTEGER NOT NULL,
            PRIMARY KEY (category1, category2)
        )
    """
}

# Indexes
SEMANTIC_COMPOSITION_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_semantic_bigrams_freq ON semantic_bigrams(frequency DESC)",
    "CREATE INDEX IF NOT EXISTS idx_semantic_bigrams_pmi ON semantic_bigrams(pmi DESC)",
    "CREATE INDEX IF NOT EXISTS idx_semantic_trigrams_freq ON semantic_trigrams(frequency DESC)",
    "CREATE INDEX IF NOT EXISTS idx_semantic_patterns_type ON semantic_composition_patterns(pattern_type)",
    "CREATE INDEX IF NOT EXISTS idx_semantic_patterns_freq ON semantic_composition_patterns(frequency DESC)",
    "CREATE INDEX IF NOT EXISTS idx_semantic_conflicts_type ON semantic_conflicts(conflict_type)",
    "CREATE INDEX IF NOT EXISTS idx_semantic_pmi_score ON semantic_pmi(pmi DESC)",
]


def create_semantic_composition_tables(db_path: str = 'data/villages.db'):
    """Create all semantic composition analysis tables."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    for table_name, schema in SEMANTIC_COMPOSITION_SCHEMA.items():
        print(f"Creating table: {table_name}")
        cursor.execute(schema)

    # Create indexes
    for index_sql in SEMANTIC_COMPOSITION_INDEXES:
        print(f"Creating index...")
        cursor.execute(index_sql)

    conn.commit()
    conn.close()
    print("All semantic composition tables created successfully!")


if __name__ == '__main__':
    create_semantic_composition_tables()
