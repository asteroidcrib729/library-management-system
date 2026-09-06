# SQLite migration and PostgreSQL recovery runbook

This runbook owns synthetic rehearsals until Plan 19 authorizes a final genuine-data
cutover. Do not point these commands at the working SQLite database directly for import:
first create a new snapshot, retain the source and snapshot, and run the dry-run gate.

## Preconditions

- Use the committed Python environment and PostgreSQL schema versions 1-3.
- Stop writes before creating a final cutover snapshot. The snapshot API detects a
  concurrent commit visible to its SQLite connection, but a maintenance window remains
  mandatory for the final import.
- Set `DATABASE_URL` only in the current process or a protected provider environment.
  Do not pass it as a command argument or save it in repository files.
- The import target must contain the `lms` schema and migrations but zero rows in every
  application and idempotency table. The tool refuses merge and overwrite behavior.
- Store snapshots, reports, and logical archives outside the repository on encrypted,
  access-controlled storage. Record the printed SHA-256 digest with the change ticket.

## Synthetic rehearsal sequence

Run from the repository root. Substitute disposable paths only:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\data-migration.ps1 `
  snapshot --source C:\safe\synthetic-source.db --output C:\safe\migration.sqlite3

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\data-migration.ps1 `
  inspect --snapshot C:\safe\migration.sqlite3

$env:DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:55432/fresh_database'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\data-migration.ps1 `
  import --snapshot C:\safe\migration.sqlite3 --environment test
```

`import` is a dry run unless `--commit` is present. Compare the reported file digest,
per-table counts/digests, active circulation metrics, and minor-unit financial totals.
Only after the dry-run report is approved should the same immutable snapshot and target
be used with explicit commit:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\data-migration.ps1 `
  import --snapshot C:\safe\migration.sqlite3 --environment test --commit
```

The transaction preserves SQLite identifiers, repairs each PostgreSQL identity sequence,
and reconciles before commit. Dry runs and failures roll back every inserted row. A
successful import makes the target non-empty, so rerunning is refused; recovery means
discarding the disposable target and recreating it from committed migrations.

## Logical backup

Install PostgreSQL client tools compatible with the server. Override their executable
paths with `LMS_PG_DUMP` and `LMS_PG_RESTORE` when they are not on `PATH`.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\data-migration.ps1 `
  backup --output C:\secure-off-provider\lms-20260906.dump --environment test

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\data-migration.ps1 `
  verify-backup --archive C:\secure-off-provider\lms-20260906.dump --environment test
```

The archive is PostgreSQL custom format, limited to `lms`, and excludes ownership and
ACL bindings so it can be restored by a controlled target owner. The result reports its
size, SHA-256 digest, and restorable-entry count. It is not encrypted by `pg_dump`; the
storage location must supply encryption and independent access control.

## Guarded restore drill

Create a new empty PostgreSQL database. Do not apply LMS migrations to it: the archive
contains the complete `lms` schema and migration markers. Point `DATABASE_URL` at that
new database, verify the archived SHA-256 value, and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\data-migration.ps1 `
  restore --archive C:\secure-off-provider\lms-20260906.dump --environment test
```

Restore fails closed if `to_regnamespace('lms')` already exists and never drops a schema
or database. After restoration, verify readiness, per-table reconciliation, RLS, login,
circulation, and reports before declaring recovery successful. Retain the pre-incident
database until the recovery decision is approved; destructive production restoration
requires maintenance mode and the Plan 19 data-loss assessment.

## Rehearsal evidence and limits

Plan 15's synthetic archive/list/restore test completes automatically in the PostgreSQL
CI job. It proves command and schema portability on the pinned local PostgreSQL 17 image,
not a production recovery objective. Provider-scale RPO/RTO, encrypted off-provider
retention, alerting, and scheduled restore frequency must be measured and approved in
Plans 18-19. Plan 18's provider-specific encryption, storage ownership, retention,
clean-target rehearsal, and evidence requirements are defined in `deploy/RUNBOOK.md`;
Free Supabase is not treated as an automatic-backup service.
