# Development Plan 13: PostgreSQL Infrastructure and Schema

## Document information

- **Status:** Complete
- **Started:** 2026-09-05
- **Completed:** 2026-09-05
- **Depends on:** Plan 12
- **Scope:** Phase B1a of Plan 11; local synthetic data only.

## 1. Scope and sequence adjustment

Plan 11 permits splitting large phases before execution. Its original Plan 13 combined infrastructure with all business repositories. This iteration establishes the database substrate first; Plan 14 will deliver repository parity, pagination, business lock ordering, idempotency operations, and concurrent business tests. SQLite migration moves to Plan 15, full FastAPI capabilities to Plan 16, dashboard workflows to Plan 17, deployment to Plan 18, and pilot/cutover to Plan 19. No existing completed plan is renumbered.

## 2. Deliverables

1. A timestamped PostgreSQL migration under `supabase/migrations/`, with a private `lms` schema, identity keys, native timestamps/booleans, integer money, foreign keys, unique/check constraints, query indexes, and idempotency storage.
2. One synchronous Psycopg pool per API process, constructed closed and opened/closed in lifespan. Defaults: zero minimum, five maximum connections, ten queued callers, two-second acquisition and lock timeouts, five-second statement timeout, ten-second idle-transaction timeout.
3. A reusable transaction primitive that rolls back unless explicitly committed, releases every checked-out connection, rejects nested reuse, and translates overload/contention into persistence errors.
4. A whole-transaction callback runner that retries only serialization/deadlock failures, at most twice, with bounded backoff/jitter. No retry on ambiguous connection loss; callbacks must have no external side effects.
5. Database and exact-schema readiness checks with sanitized failure messages. Startup never migrates. Liveness remains independent of PostgreSQL.
6. Real PostgreSQL tests for schema constraints, commit/rollback, connection reuse/exhaustion, read/write concurrency, lock/statement timeouts, deadlock retry, and API lifespan/readiness. An explicitly named disposable test database prevents use of the local working database or hosted data.
7. CI and PowerShell commands that actually run the database suite, plus configuration and next-plan documentation.

## 3. Schema and migration rules

- Supabase CLI owns migration history; application compatibility is recorded separately in `lms.schema_version`.
- Migration SQL runs within an explicit transaction and obtains a project-specific transaction advisory lock. No migration runs at API startup.
- App tables live outside Data API schemas. Revoke PUBLIC schema/table access and enable RLS with no public policies; the local owner connection is development-only. A least-privilege hosted login and grants must be verified before deployment.
- Preserve all existing entity fields and UTC timestamp semantics. Add partial uniqueness for active loans/reservations, one loan fine and settlement, and null-aware pending request identity.
- Idempotency records will be scoped by actor, operation, and key, with request digest, committed JSON result, status, and expiry. Plan 14 implements atomic claim/replay; Plan 16 wires HTTP behavior.
- No copied legacy account data or existing `.lms` files enter PostgreSQL.

## 4. Verification and exit gate

Execute the migration using a fresh disposable PostgreSQL database, exercise constraints using SQL and native driver connections, and run the complete existing Python suite. Verify contract drift and types after API lifecycle integration. Database tests must fail when explicitly requested infrastructure is unavailable, and otherwise skip with an actionable message when not requested. Record commands and outcomes below. Business parity is a Plan 14 gate and must not be claimed here.

## 5. References

- [Psycopg connection pools](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [Psycopg transaction management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [PostgreSQL 17 constraints](https://www.postgresql.org/docs/17/ddl-constraints.html)

## 6. Execution record

- Installed Psycopg 3.3.5 (native Python 3.14 Windows wheel) and psycopg-pool 3.3.1.
- Applied `20260905000100_initial_lms.sql` to both freshly created disposable databases
  and the local Supabase working database using `migration up --local`. A repeat invocation
  applied zero migrations. PostgreSQL is 17.6; application schema version is 1.
- The private schema contains the nine existing business entity tables, idempotency
  records, and the schema marker, with RLS enabled on all eleven tables. No application
  user records or copied legacy data were imported.
- Added closed-on-construction pool ownership, explicit transaction commit/rollback,
  acquisition/lock/statement limits, connection validation, three-attempt maximum retries
  for confirmed deadlock/serialization aborts, and sanitized database errors. Pool
  statistics and transaction-duration/retry logging provide initial observability.
- FastAPI lifespan now owns the pool. Configured readiness verifies the exact schema
  marker; missing or future schema returns 503 without migration or SQL details. An
  unconfigured API keeps liveness available and explains that PostgreSQL is not configured.
- Added 12 configuration tests and 16 native PostgreSQL tests. Evidence includes an actual
  two-connection deadlock recovered with attempt counts `[1, 2]`, rollback after a SQL
  error, reads during writes, bounded pool/lock/query waits, retry exhaustion, no retry
  after connection loss, unique active loans/reservations/loan-fines/settlements, nullable
  pending-request uniqueness, money/FK constraints, RLS flags, and API lifecycle/readiness.
- Full Python suite: **149 passed** in 13.76 seconds through `check.ps1 -Postgres`.
  Ruff lint/format passed; the lifespan annotation was updated to `AsyncGenerator`
  following a Pyrefly deprecation diagnostic; root OpenAPI
  and generated TypeScript contract checks remain current.
- GitHub workflow validated successfully with actionlint 1.7.7. The validator received only
  `ci.yml` read-only with runtime networking disabled. Database tests now run for backend
  and database changes; deleted paths are classified and both `main`/`master` pushes run CI.
- Test databases are uniquely created and removed by the suite; the final PostgreSQL check
  found zero remaining `lms_test_*` databases. Local development records were not reset.
- One elevated full-suite attempt could not access the existing Windows Pytest temp
  directory. Rerunning in the normal workspace context and then through the PowerShell
  workflow passed. The remaining Pytest warning is the existing third-party Starlette/AnyIO
  deprecation, not a test failure.

- The complete `check.ps1 -Postgres` workflow passed, including frontend contract drift,
  ESLint, strict TypeScript, both component tests, and the Next.js production build
  (compilation 23.5 seconds on this local run with Docker active). Tailwind and React
  Compiler remain enabled. After the annotation adjustment, Pyrefly reported **zero
  diagnostics**, Ruff passed, and all 12 focused API/configuration/contract tests passed.
- No remote CI run or hosted deployment was performed. The workflow syntax is locally
  validated; GitHub execution requires committing and pushing the current work.

All Plan 13 exit gates are satisfied. Repository/business parity,
pagination implementations, operation lock ordering, atomic idempotency operations,
and immutable settlement repository behavior remain explicit Plan 14 deliverables.
