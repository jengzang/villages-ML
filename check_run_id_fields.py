"""Check all tables for run_id, created_at, timestamp fields."""
import sqlite3

db_path = 'data/villages.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

print(f"Checking {len(tables)} tables for run_id/timestamp fields...\n")

found_issues = []

for table in tables:
    try:
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
                'columns': problem_cols
            })
            print(f"⚠️  {table}")
            for col in problem_cols:
                print(f"    - {col}")
    except Exception as e:
        print(f"✗ Error checking {table}: {e}")

conn.close()

if found_issues:
    print(f"\n❌ Found {len(found_issues)} tables with run_id/timestamp fields")
else:
    print("\n✅ No tables have run_id/timestamp fields")
