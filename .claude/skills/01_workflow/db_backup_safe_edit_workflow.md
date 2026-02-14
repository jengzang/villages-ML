# Skill: Database Backup & Safe Edit Workflow

## Skill Name
`db_backup_safe_edit_workflow`

## Purpose

This skill enforces a mandatory backup workflow for any operation that edits the database.

Key requirements:

- Every database edit must be preceded by a backup
- Database files must NOT be committed to git
- Backups are temporary and can be deleted only after the user confirms the changes are valid


---

## Trigger Condition

This skill is triggered whenever:

- Any script or operation intends to modify database content
- Any SQL `UPDATE/DELETE/INSERT` is executed against the production dataset
- Any batch normalization/cleaning task will write changes back to DB


---

## Backup Rules (Mandatory)

### 1) Backup Before Edit

Before any database modification begins:

- Create a backup copy of the database file(s)
- Backup must be created *immediately before* applying changes
- Backup naming must be unique, timestamped, and traceable

Recommended backup naming convention:

- `backups/<db_name>.<YYYYMMDD-HHMMSS>.pre_edit.bak`

Example:

- `backups/villages.db.20260215-224501.pre_edit.bak`


### 2) Backup Storage Location

- Backups must be stored under a dedicated directory:
  - `backups/`

- Backups must not overwrite previous backups


### 3) Backup Retention & Deletion

- After database changes are applied, the backup must remain in place
- The backup can be deleted only after:
  - The user explicitly confirms the changes are valid and acceptable

Until user confirmation, backups must not be deleted.


---

## Git Rules for Database Files

### 1) Do NOT Commit Database Files

Database files must never be committed.

This includes (examples):

- `*.db`
- `*.sqlite`
- `*.sqlite3`
- `*.db-wal`
- `*.db-shm`
- any backup files under `backups/`

### 2) Require `.gitignore` Enforcement

Ensure `.gitignore` includes patterns such as:

- `*.db`
- `*.sqlite`
- `*.sqlite3`
- `*.db-wal`
- `*.db-shm`
- `backups/`

Database changes are tracked via scripts, logs, and README updates — not by committing DB binaries.


---

## Post-Edit Validation Requirement

After edits are completed:

- Produce a concise validation summary, e.g.:
  - number of affected rows
  - sample before/after examples
  - any anomalies detected

Then request user confirmation.

Only after the user confirms:

- delete the corresponding backup file(s)

No implicit confirmation is allowed.


---

## Design Philosophy

- Database edits are high-risk and must be reversible
- Backups provide rollback safety without polluting git history
- The repository should track **code + rules + logs**, not binary database artifacts
