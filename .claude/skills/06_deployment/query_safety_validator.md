# Skill 18: Query Safety Validator

## Skill Name
query_safety_validator

## Purpose
Validate query safety and resource consumption to prevent full table scans and unbounded queries.
Ensure online queries comply with 2-core/2GB server resource constraints.
Enforce the "offline-heavy, online-light" principle at runtime.

---

# Part A: Query Risk Types

**High-Risk Queries:**
1. **Full Table Scans**
   - No WHERE clause on large tables
   - Non-indexed column filters
   - Queries returning >10k rows without LIMIT

2. **Unbounded Queries**
   - Missing LIMIT clause
   - No pagination parameters
   - Open-ended aggregations

3. **Complex Joins**
   - Multiple large table joins
   - Non-indexed join keys
   - Cartesian products

4. **Expensive Computations**
   - Embedding generation at runtime
   - Clustering operations
   - Province-wide aggregations without filters

5. **Resource-Intensive Operations**
   - Full-text search without constraints
   - Regex matching on large columns
   - Sorting large result sets

---

# Part B: Validation Rules

**Rule 1: Mandatory Filters**
- Queries on `广东省自然村` table MUST include:
  - Region filter (市级, 县区级, or 乡镇), OR
  - Cluster ID filter, OR
  - Semantic index filter, OR
  - LIMIT ≤ 5000

**Rule 2: Index Requirements**
- WHERE clauses must use indexed columns:
  - ✅ `市级`, `县区级`, `乡镇` (administrative regions)
  - ✅ `cluster_id` (spatial/semantic clusters)
  - ✅ `semantic_index` (semantic categories)
  - ❌ `自然村` (village name - full text search)
  - ❌ `备注` (notes - unstructured text)

**Rule 3: Row Limits**
- Hard limit: 5000 rows per query
- Recommended: 1000 rows per page
- Enforce pagination for large result sets

**Rule 4: Forbidden Operations**
- ❌ Embedding generation (use precomputed)
- ❌ Clustering (use precomputed cluster_id)
- ❌ Province-wide frequency computation (use materialized tables)
- ❌ Full table scans without filters
- ❌ Index rebuilding at runtime

**Rule 5: Timeout Constraints**
- Query timeout: 5 seconds
- Connection timeout: 10 seconds
- Abort queries exceeding limits

---

# Part C: Implementation Strategy

**Pre-Query Validation:**
```python
def validate_query(sql: str, params: dict) -> ValidationResult:
    """
    Validate query before execution.
    Returns: (is_safe, error_message, suggested_fix)
    """
    # Check 1: Parse SQL and extract table names
    tables = extract_tables(sql)

    # Check 2: Verify filters on large tables
    if '广东省自然村' in tables:
        if not has_required_filter(sql, params):
            return ValidationResult(
                is_safe=False,
                error="Missing required filter (region/cluster/semantic)",
                suggested_fix="Add WHERE clause with region or cluster_id"
            )

    # Check 3: Verify LIMIT clause
    if not has_limit(sql) or get_limit(sql) > 5000:
        return ValidationResult(
            is_safe=False,
            error="Missing or excessive LIMIT",
            suggested_fix="Add LIMIT ≤ 5000"
        )

    # Check 4: Verify indexed columns
    if not uses_indexed_columns(sql):
        return ValidationResult(
            is_safe=False,
            error="Query uses non-indexed columns",
            suggested_fix="Filter by indexed columns (市级, cluster_id, etc.)"
        )

    return ValidationResult(is_safe=True)
```

**Query Rewriting:**
```python
def rewrite_unsafe_query(sql: str) -> str:
    """
    Automatically fix common safety issues.
    """
    # Add LIMIT if missing
    if not has_limit(sql):
        sql = add_limit(sql, default=1000)

    # Force index usage
    sql = add_index_hints(sql)

    return sql
```

**Runtime Monitoring:**
```python
def execute_with_monitoring(sql: str, params: dict):
    """
    Execute query with resource monitoring.
    """
    start_time = time.time()
    start_memory = get_memory_usage()

    # Set query timeout
    cursor.execute("PRAGMA query_timeout = 5000")  # 5 seconds

    try:
        result = cursor.execute(sql, params)

        # Check execution time
        elapsed = time.time() - start_time
        if elapsed > 5.0:
            log_warning(f"Slow query: {elapsed:.2f}s")

        # Check memory usage
        memory_used = get_memory_usage() - start_memory
        if memory_used > 100_000_000:  # 100 MB
            log_warning(f"High memory query: {memory_used / 1e6:.1f} MB")

        return result

    except sqlite3.OperationalError as e:
        if "timeout" in str(e):
            raise QueryTimeoutError("Query exceeded 5 second timeout")
        raise
```

---

# Part D: Monitoring Metrics

**Query Performance Metrics:**
- `query_count` - Total queries executed
- `query_duration_p50` - Median query time
- `query_duration_p95` - 95th percentile query time
- `query_duration_p99` - 99th percentile query time
- `slow_query_count` - Queries >1 second
- `timeout_count` - Queries exceeding timeout

**Resource Metrics:**
- `memory_usage_avg` - Average memory per query
- `memory_usage_peak` - Peak memory usage
- `cpu_usage_avg` - Average CPU utilization
- `connection_count` - Active connections

**Safety Metrics:**
- `unsafe_query_blocked` - Queries blocked by validator
- `full_scan_prevented` - Full table scans prevented
- `limit_enforced` - Queries with LIMIT added
- `rewrite_count` - Queries automatically rewritten

---

# Part E: CLI Usage

**Module:** `src/data/query_validator.py`
**Class:** `QuerySafetyValidator`

**Validation Mode:**
```bash
# Validate a query without executing
python scripts/validate_query.py \
  --sql "SELECT * FROM 广东省自然村 WHERE 市级='广州市' LIMIT 1000" \
  --check-only
```

**Enforcement Mode:**
```bash
# Run query with safety enforcement
python scripts/safe_query.py \
  --sql "SELECT * FROM 广东省自然村 WHERE 市级='广州市'" \
  --auto-fix \
  --timeout 5
```

**Monitoring Mode:**
```bash
# Monitor query performance
python scripts/monitor_queries.py \
  --duration 3600 \
  --output-file query_metrics.json
```

**Parameter Flags:**
- `--sql` - SQL query to validate/execute
- `--check-only` - Validate without executing
- `--auto-fix` - Automatically rewrite unsafe queries
- `--timeout` - Query timeout in seconds (default: 5)
- `--max-rows` - Maximum rows to return (default: 5000)
- `--strict-mode` - Reject queries that can't be auto-fixed

---

# Part F: Best Practices

**For Query Writers:**
1. Always include region/cluster filters on large tables
2. Use LIMIT for all queries (even if you think result is small)
3. Filter by indexed columns when possible
4. Avoid full-text search on unindexed columns
5. Use materialized tables for aggregations

**For API Developers:**
1. Validate all user-provided queries
2. Enforce pagination (default page size: 100)
3. Set query timeouts at application level
4. Log slow queries for optimization
5. Provide query cost estimates to users

**For Database Administrators:**
1. Create indexes on frequently filtered columns
2. Monitor query performance metrics
3. Identify and optimize slow queries
4. Set resource limits at database level
5. Regularly analyze query patterns

---

# Part G: Configuration

**Config File:** `config/query_safety.yaml`

```yaml
query_safety:
  # Row limits
  max_rows_per_query: 5000
  default_page_size: 100
  max_page_size: 1000

  # Timeouts
  query_timeout_seconds: 5
  connection_timeout_seconds: 10

  # Required filters
  require_filter_on_tables:
    - 广东省自然村

  allowed_filter_columns:
    - 市级
    - 县区级
    - 乡镇
    - cluster_id
    - semantic_index

  # Forbidden operations
  forbidden_keywords:
    - CREATE INDEX
    - DROP INDEX
    - VACUUM
    - ANALYZE

  # Monitoring
  log_slow_queries: true
  slow_query_threshold_seconds: 1.0
  log_high_memory_queries: true
  high_memory_threshold_mb: 100

  # Auto-fix
  auto_add_limit: true
  auto_add_index_hints: false
  strict_mode: false
```

---

# Part H: Error Messages

**User-Friendly Error Messages:**

```python
ERROR_MESSAGES = {
    "missing_filter": """
        Query requires a filter on region, cluster, or semantic index.

        Suggested fix:
        Add WHERE clause: WHERE 市级='广州市' OR cluster_id=5
    """,

    "missing_limit": """
        Query must include LIMIT clause (max 5000 rows).

        Suggested fix:
        Add: LIMIT 1000
    """,

    "non_indexed_column": """
        Query filters on non-indexed column.

        Indexed columns: 市级, 县区级, 乡镇, cluster_id, semantic_index

        Suggested fix:
        Use indexed column or add to materialized table
    """,

    "query_timeout": """
        Query exceeded 5 second timeout.

        Suggested fixes:
        1. Add more specific filters
        2. Reduce LIMIT
        3. Use precomputed materialized table
    """,

    "forbidden_operation": """
        Operation not allowed in online queries.

        Forbidden: embedding generation, clustering, index rebuilding

        Solution: Use precomputed results from offline pipeline
    """
}
```

---

# Part I: Integration with Phase 11

**Phase 11 Online Serving Policy:**
- This skill implements the query safety strategy from Phase 11
- Enforces "offline-heavy, online-light" principle
- Prevents accidental heavy computation in production

**Key Principles:**
1. Online endpoints only read materialized tables
2. No expensive recomputation at runtime
3. All heavy computation must be offline jobs
4. Queries are bounded and resource-constrained

**Deployment:**
- Integrate validator into API middleware
- Apply to all database queries
- Log violations for analysis
- Provide feedback to query writers

---

# Acceptance Criteria

1. ✅ Query validator identifies high-risk queries
2. ✅ Validation rules enforce filters, limits, and indexed columns
3. ✅ Unsafe queries are blocked or rewritten
4. ✅ Query timeouts prevent runaway queries
5. ✅ Resource monitoring tracks performance metrics
6. ✅ User-friendly error messages guide query writers
7. ✅ Configuration file allows tuning safety parameters
8. ✅ Integration with Phase 11 online serving policy
9. ✅ Logging and monitoring for production deployment
10. ✅ Documentation includes best practices and examples
