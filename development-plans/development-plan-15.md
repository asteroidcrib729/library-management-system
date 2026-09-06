# Development Plan 15: SQLite Import and PostgreSQL Recovery

## Document information

- **Status:** Complete
- **Started:** 2026-09-06
- **Depends on:** Plan 14
- **Scope:** Phase B2 of Plan 11; synthetic local data and disposable PostgreSQL databases only.

## 1. Objective

Prove that a stable SQLite snapshot can be transferred into a fresh PostgreSQL database
without identifier, relationship, state, timestamp, or financial drift, and prove that
the resulting PostgreSQL system can be logically backed up and restored. This plan does
not switch the CLI, import the user's working database, connect to hosted Supabase, or
authorize a production cutover.

## 2. Deliverables

1. A read-only SQLite snapshot creator and inspector that rejects missing, changing,
   corrupt, logically inconsistent, incomplete, or unsupported-schema sources.
2. A fresh-target-only, single-transaction importer with explicit table order, preserved
   identifiers, restored identity sequences, dry-run rollback, and safe failure messages.
3. A deterministic reconciliation report covering every migrated table, canonical row
   digests, active circulation state, outstanding fine totals, and settlement totals.
4. A rerun contract: successful imports reject non-empty targets; failed/dry-run imports
   leave the target empty, so recovery is a clean atomic rerun rather than partial resume.
5. A portable `pg_dump`/`pg_restore` boundary that keeps credentials out of command-line
   arguments, creates custom-format schema/data archives, verifies archive readability,
   and restores only into a database without the `lms` schema.
6. A PowerShell operator entry point for snapshot, inspect, dry-run/import, logical
   backup, archive verification, and guarded restore operations.
7. Synthetic end-to-end tests plus a real disposable-database backup/restore drill and
   updated CI/documentation.

## 3. Execution and safety rules

- Snapshot creation opens the source by exact path in SQLite read-only mode and writes a
  new destination; it never initializes, migrates, renames, deletes, or replaces source.
- Import accepts only a validated snapshot with exactly SQLite schema versions 1-4.
- PostgreSQL must report application schema versions 1-2 and zero rows in all application
  and idempotency tables. No merge, overwrite, truncate, or `ON CONFLICT` is permitted.
- Rows are inserted in dependency order: users, books, copies, reservations, loans,
  fines, settlements, requests, feedback. Existing positive identifiers are preserved.
- The import uses one transaction and a dedicated advisory lock. Validation,
  reconciliation, and identity-sequence repair occur before commit. Dry-run always rolls
  back after producing the same report.
- Canonical SHA-256 digests are computed from ordered, typed values rather than database
  file bytes or provider-specific serialization. Password hashes are compared but never
  printed in reports or logs.
- Recovery commands never embed the database password or complete URL in process
  arguments. Restore rejects an existing `lms` schema and never drops a schema/database.
- Tests use generated SQLite files and uniquely named `lms_test_*` databases on loopback.
  Genuine SQLite files, local application data, legacy files, hosted projects, and
  production credentials remain outside scope.

## 4. Verification and exit gate

The plan is complete only when synthetic data for every entity and state passes dry-run,
committed import, sequence continuation, digest/metric reconciliation, failed-import
rollback, non-empty-target rejection, and source immutability checks. A custom logical
archive must be created, listed, restored into a second clean disposable database, and
reconciled. Run all Python/PostgreSQL tests, Ruff, Pyrefly, OpenAPI/client drift checks,
frontend checks/build, migration replay, workflow validation, and confirm zero leftover
test databases or committed data/backup artifacts.

## 5. Execution record

Completed on 2026-09-06.

- Added a standalone SQLite snapshot boundary that opens the source read-only, uses the
  SQLite online backup API, requires a new destination, detects visible concurrent source
  changes/replacement, rejects WAL-dependent snapshots, and deletes only an invalid
  destination it created. The source file remains unchanged.
- Added strict inspection for SQLite schema versions 1-4, required tables/columns,
  integrity, foreign keys, positive identifiers, circulation state, reservation state,
  financial/settlement consistency, request lifecycle, and feedback lifecycle.
- Added canonical ordered row serialization and SHA-256 digests for users, books, copies,
  reservations, loans, fines, settlements, requests, and feedback. Reports contain only
  counts, digests, and operational/financial metrics; password hashes are never printed.
- Added a PostgreSQL importer protected by an advisory lock and access-exclusive table
  locks. It accepts only schema versions 1-2 and a zero-row application/idempotency
  target, preserves identifiers, inserts in foreign-key order, resets every identity
  sequence, reconciles before commit, and rolls back dry runs or any failure atomically.
  Successful reruns are refused rather than merged.
- Added a `pg_dump`/`pg_restore` boundary using process environment variables for
  credentials, custom-format `lms` archives, owner/ACL portability, archive listing and
  SHA-256 verification, existing-schema restore refusal, and post-restore schema/RLS
  validation. Neither full connection URLs nor passwords are placed in child-process
  arguments.
- Added `scripts/data-migration.ps1` and `scripts/migrate_data.py` with snapshot,
  inspection, dry-run/default import, explicit `--commit`, backup, verification, and
  guarded restore commands. The complete synthetic operator procedure and remaining
  production restrictions are in `supabase/DATA_MIGRATION.md`.
- Added synthetic tests for source immutability, destination refusal, corruption,
  unsupported schema, logical inconsistency, every migrated table/state, dry-run
  emptiness, committed digest/metric parity, identity continuation, non-empty target
  refusal, and forced reconciliation rollback.
- The native PostgreSQL 17 drill created a custom archive, successfully listed its
  restorable schema/table-data entries, restored into a second clean disposable database,
  and verified versions 1-2, all source users, and RLS on all 11 tables. The archive and
  restore database were test artifacts and were removed.
- Verification passed: 137 non-PostgreSQL tests and 26 PostgreSQL tests (163 total), Ruff
  lint/format, Pyrefly with zero errors, deterministic OpenAPI/client drift checks,
  ESLint, Next.js type generation/TypeScript, two Vitest tests, the Next.js production
  build, local migration versions 1-2, and actionlint on the updated CI workflow. The
  final disposable `lms_test_*` database count was zero. No genuine SQLite file, local
  application row, hosted provider, or deployment was used.

Plan 16 may now begin. Production RPO/RTO, encrypted off-provider retention, scheduled
backup automation, and provider-scale recovery measurements remain gated to Plans 18-19.
