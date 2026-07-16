# Raw Village Cleanup Guide

This guide documents the row-level cleanup workflow for the raw table
`广东省自然村` in `data/villages.db`.

The scripts are conservative by design:

- They do not rely on random sampling.
- Analysis scripts write CSV reports under `results/`.
- Maintenance scripts write audit tables before deleting rows.
- Database backups should be created before applying destructive changes.

## Important Columns

The current raw table schema uses these physical column names:

- `市级`
- `区县级`
- `乡镇级`
- `行政村`
- `自然村`
- `拼音`
- `方言分布`
- `longitude`
- `latitude`

Note that the raw table uses `行政村` and `方言分布`, not `村委会` or
`语言分布`.

## 1. Raw Table Audit

Run a full row-level audit of the raw table:

```bash
python3 scripts/analysis/audit_raw_villages.py
```

Outputs:

- `results/raw_village_audit/SUMMARY.md`
- `results/raw_village_audit/row_level_audit.csv`
- duplicate summary CSV files

This is exploratory only. It does not modify the database.

## 2. Intra-Administrative Near-Duplicate Audit

Run exhaustive pairwise comparison inside each
`市级 + 区县级 + 乡镇级 + 行政村` group:

```bash
python3 scripts/analysis/audit_intra_admin_near_duplicates.py
```

Outputs:

- `results/intra_admin_near_duplicates/merge_review_pairs.csv`
- `results/intra_admin_near_duplicates/fuzzy_signals.csv`
- `results/intra_admin_near_duplicates/row_candidate_coverage.csv`
- `results/intra_admin_near_duplicates/SUMMARY.md`

Use `merge_review_pairs.csv` for cleanup review. `fuzzy_signals.csv` is broad
and should not be used directly for deletion.

## 3. Admin-Prefix Duplicate Proposals

Generate proposals for cases where one row is a natural village name and the
other is the same name with the administrative village prefixed.

```bash
python3 scripts/analysis/propose_intra_admin_merges.py
```

Output:

- `results/intra_admin_near_duplicates/merge_proposals.csv`

Example:

```text
keep:   细围
delete: 丁屋细围
reason: 丁屋细围 minus 行政村 prefix 丁屋 = 细围
```

The proposal script does not modify the database.

## 4. Apply Admin-Prefix Merges

Dry-run first:

```bash
python3 scripts/maintenance/apply_admin_prefix_merges.py --dry-run --max-distance-m 500
```

Apply:

```bash
python3 scripts/maintenance/apply_admin_prefix_merges.py --max-distance-m 500
```

The script:

- Keeps the shorter no-admin-prefix name.
- Deletes the admin-prefixed duplicate.
- Transfers `方言分布` to the kept row when the kept row is blank.
- Writes an audit row to `cleanup_admin_prefix_merge_audit` before deletion.

Create a database backup before applying.

## 5. Exact Same Name Merges

Merge rows that have the exact same `自然村` inside the same administrative
village group and whose coordinates are within a configured threshold.

Dry-run:

```bash
python3 scripts/maintenance/apply_exact_name_merges.py --dry-run --max-distance-m 1000
```

Apply:

```bash
python3 scripts/maintenance/apply_exact_name_merges.py --max-distance-m 1000
```

The script:

- Groups by `市级 + 区县级 + 乡镇级 + 行政村 + 自然村`.
- Builds connected components for rows within the distance threshold.
- Keeps the row with `方言分布`; if tied, keeps the longer `拼音`; if tied,
  keeps the lower `rowid`.
- Merges all non-empty dialect values into the kept row.
- Writes audit rows to `cleanup_exact_name_merge_audit`.

## 6. Far Coordinate System Analysis

For far admin-prefix candidates, test whether the distance can be explained by
mixed WGS84, GCJ-02, or BD-09 coordinates:

```bash
python3 scripts/analysis/analyze_far_merge_coordinates.py
```

Output:

- `results/intra_admin_near_duplicates/far_coordinate_system_analysis.csv`

This script is analytical only. It does not modify the database.

## 7. Homophone / Variant Candidate List

List close homophone or variant-writing candidates for manual review:

```bash
python3 scripts/analysis/list_homophone_variant_candidates.py
```

Output:

- `results/intra_admin_near_duplicates/homophone_variant_candidates.csv`

These should be reviewed before merging. Examples include variants like
`凹/坳`, `冈/岗`, `寮/料`, and `黎/李`.

## 8. Verification Queries

Check raw row count:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/villages.db').cursor(); print(c.execute('select count(*) from \"广东省自然村\"').fetchone()[0])"
```

Check audit counts:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/villages.db').cursor(); print(c.execute('select count(*) from cleanup_admin_prefix_merge_audit where action=\"applied\"').fetchone()[0]); print(c.execute('select count(*) from cleanup_exact_name_merge_audit where action=\"applied\"').fetchone()[0])"
```

Check that deleted rowids are gone:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/villages.db').cursor(); print(c.execute('select count(*) from \"广东省自然村\" where rowid in (select delete_rowid from cleanup_exact_name_merge_audit where action=\"applied\")').fetchone()[0])"
```

## 9. Preprocessed Table Warning

The cleanup scripts modify only the raw table `广东省自然村`.

After raw cleanup, `广东省自然村_预处理` may be stale. Rebuild or synchronize the
preprocessed table before running downstream analysis pipelines.

