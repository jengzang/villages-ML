import sqlite3
import os

db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [row[0] for row in cursor.fetchall()]

print(f"Total tables: {len(tables)}\n")

# Check specific tables mentioned in the audit
key_tables = [
    'semantic_indices', 'village_ngrams', 'spatial_tendency_integration',
    'village_semantic_structure', 'char_embeddings', 'pattern_frequency_global',
    'spatial_hotspots', 'cluster_assignments', 'cluster_profiles',
    'semantic_labels', 'character_significance'
]

print("Key Tables Status:")
print("-" * 60)
for table in key_tables:
    if table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        status = "✅ POPULATED" if count > 0 else "❌ EMPTY"
        print(f"{table:40} {count:>10} rows  {status}")
    else:
        print(f"{table:40} {'N/A':>10}      ⚠️  NOT FOUND")

conn.close()
