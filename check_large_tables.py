"""Check large village-level tables for run_id/timestamp fields."""
import sqlite3

db_path = 'data/villages.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Large village-level tables (>100k rows)
large_tables = [
    '广东省自然村',
    '广东省自然村_预处理',
    'village_ngrams',
    'village_semantic_structure',
    'village_features',
    'village_spatial_features'
]

print("Checking large village-level tables for run_id/timestamp fields...\n")

found_issues = []

for table in large_tables:
    try:
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            print(f"[SKIP] {table} - table does not exist")
            continue

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]

        # Get columns
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        # Check for problematic column names
        problem_cols = []
        for col in columns:
            col_name = col[1].lower()
            if any(keyword in col_name for keyword in ['run_id', 'created_at', 'timestamp', 'updated_at']):
                problem_cols.append(col[1])

        if problem_cols:
            found_issues.append({
                'table': table,
                'columns': problem_cols,
                'row_count': row_count
            })
            print(f"[WARN] {table} ({row_count:,} rows)")
            for col in problem_cols:
                print(f"       - {col}")
        else:
            print(f"[OK] {table} ({row_count:,} rows)")

    except Exception as e:
        print(f"[ERROR] {table}: {e}")

conn.close()

print(f"\n{'='*60}")
if found_issues:
    print(f"Found {len(found_issues)} large tables with run_id/timestamp fields:")
    for issue in found_issues:
        print(f"  - {issue['table']}: {', '.join(issue['columns'])}")
else:
    print("All large village-level tables are clean!")
