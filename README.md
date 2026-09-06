# Library Management System

This monorepo contains the Python 3.14 revamp of the original C++ library management system. The legacy source is retained under `legacy/` as a requirements reference. The current web foundation keeps the Python application and FastAPI adapter at the repository root, the Next.js dashboard under `web/`, and local Supabase/PostgreSQL configuration under `supabase/`.

## Repository structure

| Path | Responsibility |
| --- | --- |
| `src/library_management/` | Domain, application services, adapters, CLI, and FastAPI delivery layer |
| `tests/` | Python unit, integration, API, and repository tests |
| `contracts/openapi.json` | Deterministic API contract shared with the dashboard |
| `web/` | Next.js 16 App Router dashboard with strict TypeScript, Tailwind CSS 4, and React Compiler |
| `supabase/` | Pinned, local-only PostgreSQL/Supabase configuration and migration history |
| `scripts/` | Contract, validation, CI classification, and PowerShell developer workflows |
| `development-plans/` | Ordered implementation plans using `development-plan-xx.md` names |

## Local setup (PowerShell)

The project virtual environment is named `.venv`. To recreate and activate it:

```powershell
& "C:\Path\To\Python314\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --editable .
```

Run the interactive CLI:

```powershell
lms
```

Inside the shell, run `help` to list commands. Start a new installation with `bootstrap-admin`; that command is disabled permanently after the first administrator is created. Use `register` for ordinary member accounts and `login` to begin a session. Passwords are collected through masked prompts and are not written to command history.

It can also be started without activating the environment:

```powershell
.\.venv\Scripts\python.exe -m library_management
```

## FastAPI foundation

The API exposes liveness and database/schema readiness endpoints. With `DATABASE_URL`
set, lifespan opens a bounded Psycopg pool and readiness verifies schema version 2.
Without that setting, liveness works and readiness returns 503. PostgreSQL business
repositories are complete under Plan 14; the CLI intentionally continues to use SQLite
until the controlled import and cutover work in later plans.

```powershell
$env:DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:55432/postgres'
.\.venv\Scripts\python.exe -m library_management.api
```

The default local origin is `http://127.0.0.1:8000`. Configuration is read from environment variables; `.env.example` is a documented template and is not loaded implicitly.

## Next.js dashboard

The isolated frontend requires the Node/npm versions declared in `web/package.json` and `web/.nvmrc`. Use `npm.cmd` because a PowerShell execution policy can block `npm.ps1`:

```powershell
Set-Location web
Copy-Item .env.local.example .env.local
& "C:\Program Files\nodejs\npm.cmd" ci
& "C:\Program Files\nodejs\npm.cmd" run dev
```

The browser receives only the public FastAPI origin. Database credentials must never be placed in a `NEXT_PUBLIC_*` variable. Tailwind CSS is connected through `@tailwindcss/postcss`; React Compiler is enabled in `web/next.config.ts` with its required compiler package locked in `web/package-lock.json`.

## Local PostgreSQL

Docker Desktop must be running. The following uses the CLI version pinned in `supabase/CLI_VERSION` and starts only local containers; this repository is not linked to a hosted project:

```powershell
$supabaseVersion = (Get-Content .\supabase\CLI_VERSION -Raw).Trim()
& "C:\Program Files\nodejs\npx.cmd" --yes "supabase@$supabaseVersion" start
& "C:\Program Files\nodejs\npx.cmd" --yes "supabase@$supabaseVersion" migration up --local
```

`migration up --local` applies pending schema changes without resetting existing local
data. `db reset` is reserved for intentionally rebuilding disposable data. Application
tables live in the private `lms` schema. See `supabase/MIGRATIONS.md` for ownership and
compatibility rules.

The default application pool has zero minimum and five maximum connections, at most
ten waiting callers, and bounded connection/query/lock timeouts. `.env.example`
lists the `LMS_DB_*` settings. Pool statistics are available from `database.pool.get_stats()`;
transaction duration is logged at DEBUG and retry counts at WARNING without SQL or URLs.

## FastAPI browser API

Plan 16 exposes the existing services under `/api/v1` by capability: authentication,
accounts, catalog, circulation, finance, engagement, and insights. Run the API only after
applying PostgreSQL migrations:

```powershell
$env:DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:55432/postgres'
$env:LMS_ALLOWED_ORIGINS = 'http://localhost:3000'
& .\.venv\Scripts\python.exe -m library_management.api
```

Login returns an opaque `HttpOnly` session cookie and a CSRF token (also placed in the
non-`HttpOnly` CSRF cookie). Browser calls use `credentials: "include"`; every unsafe
authenticated request sends the exact CSRF value in `X-CSRF-Token`. State-changing
business routes also require a caller-generated `Idempotency-Key` of 8-200 characters.
Only hashes of session and CSRF values are stored, account deactivation revokes active
sessions, and credentialed CORS accepts only the exact origins in `LMS_ALLOWED_ORIGINS`.
The interactive contract is at `/docs`; the committed contract remains authoritative
for the generated Next.js client.

## Developer workflows

Validate prerequisites and print the API/dashboard commands:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -StartDatabase
```

Run the complete backend, contract, frontend, and production-build gate:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

To include the real PostgreSQL suite after starting Supabase:

```powershell
$env:LMS_TEST_POSTGRES_ADMIN_URL = 'postgresql://postgres:postgres@127.0.0.1:55432/postgres'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1 -Postgres
```

The suite creates a random `lms_test_*` database, applies migrations, and drops only
that database on completion. Without the test URL these tests are explicitly skipped;
`-Postgres` requires it to be set. The CI database job always supplies it. Test creation
uses a local owner account; genuine data and hosted databases are outside the test scope.
The PostgreSQL gate also performs a native custom-format `pg_dump`/`pg_restore` drill
against a second disposable database. `scripts/check.ps1` uses the local container name
from `supabase/config.toml`; set `LMS_TEST_POSTGRES_CONTAINER` explicitly if the local
Supabase project name differs.

The process-scoped bypass is necessary on hosts that prohibit local `.ps1` files; it does not alter the machine or user execution policy. Use `-SkipFrontendBuild` only for a faster local iteration; the production build remains mandatory before completion. CI uses the same checks and a conservative path classifier, while always reporting one stable `CI` result.

## Individual quality checks

```powershell
pytest
pyrefly check
ruff check .
ruff format --check .
.\.venv\Scripts\python.exe -m scripts.export_openapi --check

Set-Location web
& "C:\Program Files\nodejs\npm.cmd" run check
```

## CLI appearance

The application provides its own color theme, styled output, interactive history, and a PowerShell-like prompt. Font selection belongs to the terminal host and cannot be changed reliably by a Python process.

## SQLite migration and PostgreSQL recovery

Plan 15 provides `scripts/data-migration.ps1` for validated snapshot creation, inspection,
dry-run or committed fresh-target import, custom-format logical backup verification, and
guarded restore. Import is dry-run by default and `--commit` is explicit. It preserves
identifiers, repairs PostgreSQL sequences, compares every table using canonical row
digests, and reconciles circulation and minor-unit financial totals before commit.

The current milestone is synthetic rehearsal only: do not import the working SQLite
database or discard any source/backup. Follow the complete preconditions, command order,
credential handling, off-provider storage, rollback contract, and restore checks in
`supabase/DATA_MIGRATION.md`.

For the intended appearance, use Windows Terminal and select a monospace font such as Cascadia Mono or Cascadia Code in the terminal profile used to launch the application. The CLI remains usable when color or Unicode support is unavailable.

## Current catalog commands

After signing in, use `books [query]`, `book <id>`, and `copies <book-id>` to browse the catalog. Librarians and administrators can use `add-book`, `update-book <id>`, `add-copy <book-id> [barcode]`, and `copy-status <barcode> <status>` to manage inventory. Run `help` inside the application for the complete command list.

## Current circulation commands

Members can use `reserve <book-id>`, `reservations`, `cancel-reservation <id>`, `loans`, and `renew <loan-id>` to manage their reservations and loans. Librarians and administrators can use `checkout <username> <barcode>` and `return-copy <barcode>`, inspect another account with `loans <username>`, and cancel reservations for other users. Reservation queues are first-in, first-out, and checkout, renewal, and return policies are enforced transactionally.

## Current financial commands

Members can use `fines` and `fine <id>` to inspect their own fine history and outstanding balance. Librarians and administrators can use `fines <username>`, `assess-fine <username> <amount>`, and `pay-fine <id>` to manage charges and record full payments. Administrators can use `waive-fine <id>` to waive an outstanding fine with a recorded reason.

The overdue rate is currently PKR 10.00 per started day. Returning an overdue copy creates its fine in the same database transaction that closes the loan and restores copy availability. Amounts are persisted as integer minor units, and payments and waivers retain immutable settlement records.

## Current engagement commands

Members can use `request-book`, `requests [status]`, `submit-feedback`, and `feedbacks [status]` to submit and inspect their own acquisition requests and feedback. Librarians and administrators can review all submissions with `review-request <id> <approved|rejected>`, `acquire-request <request-id> <book-id>`, `review-feedback <id>`, and `archive-feedback <id>`.

Duplicate pending requests from the same member are rejected case-insensitively. Approved requests can be linked to an existing catalog record when acquired, while feedback follows a retained `new` → `reviewed` → `archived` lifecycle.

## Current insights commands

Authenticated users can run `recommend [limit]` for explainable, personalized suggestions and `popular [limit]` for the most-circulated books that currently have an available copy. Recommendations use borrowing-history category and author affinity, historical checkout popularity, availability, and deterministic tie-breaking while excluding previously borrowed titles.

Librarians and administrators can run `dashboard` for current account, catalog, copy, loan, reservation, fine, acquisition-request, and feedback workload metrics, followed by the five most-circulated available books. Reporting is read-only and calculated directly from persisted operational data.

## Current maintenance commands

Administrators can run `db-health` to check SQLite integrity, foreign keys, schema compatibility, circulation consistency, and financial settlement consistency. Use `backup` to create an online, validated snapshot and `backups` to inspect managed backup health and compatibility.

Use `restore-backup <filename>` to restore a listed backup after entering the explicit `RESTORE` confirmation phrase. Restore candidates are restricted to the application's `backups` directory, must pass current-schema health validation, and are staged before atomic replacement. A validated `pre-restore` safety backup is created automatically before the live database is replaced.

## Password security

Passwords are handled with Argon2id through `argon2-cffi`. Plaintext passwords must never be persisted or logged. The password service also supports replacing a valid hash when its security parameters become outdated.

## Project status

The CLI remains available while the web revamp has completed Plans 12-17. PostgreSQL
schema version 3, bounded pooling and transactional concurrency, the validated
SQLite-to-PostgreSQL migration path, opaque browser sessions, CSRF/CORS and idempotent
FastAPI capability routes, deterministic OpenAPI generation, and the responsive
role-aware Next.js dashboard are implemented and verified. The browser talks only to
FastAPI; it has no Supabase credentials or direct database path. Plan 18 has added
redacted Render/Vercel descriptors, protected staging automation, deployment validation
and probes, observability headers, and operational runbooks under `deploy/`. The real
three-provider staging spike, capacity/security/recovery evidence, genuine-data
migration, and production cutover remain blocked pending explicit owner authorization
and Plan 18's external acceptance gates.

## Deployment readiness

Validate the committed provider and secret boundaries without contacting a provider:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_deployment
```

The staging setup, exact-commit release, smoke/latency/load commands, manual Supabase
resume, backup/restore, monitoring, quota, and component rollback procedures are in
`deploy/RUNBOOK.md`. Provider values belong only in the protected locations listed in
`deploy/ENVIRONMENTS.md`. The **Deploy staging** GitHub workflow is manual and cannot run
until the owner creates an isolated `staging` environment and supplies its secrets.
