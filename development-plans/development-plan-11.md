# Development Plan 11: Web Application and Deployment Architecture

## Document information

- **Status:** Approved
- **Project:** Library Management System
- **Plan:** `development-plan-11.md`
- **Depends on:** `development-plan-01.md` through `development-plan-10.md`
- **Decision date:** 2026-09-05
- **Last updated:** 2026-09-05
- **Milestone:** Transition the Python application to a browser-accessible system and validate its selected three-provider deployment architecture.
- **Update scope:** Final design and execution model, monorepo/local workflow, provider wake behavior, multi-user capacity, PostgreSQL concurrency and optimization, frontend performance, FastAPI adaptation, and database rewrite execution.

## 1. Approved architecture decision

The project will use:

- **Vercel** to build and host the TypeScript Next.js user-facing dashboard;
- **Render** to build and host the Python 3.14 FastAPI backend; and
- **Supabase** to host the PostgreSQL database.

FastAPI remains the application's only business API. The dashboard must not connect directly to PostgreSQL or use the Supabase Data API. Supabase Auth, Realtime, Storage, and Edge Functions are not selected by this decision and require separate approval if they are considered later.

The current Argon2id password service and application-owned role model remain authoritative. Browser sessions will be added to PostgreSQL for the web application. The CLI remains available during migration, parity testing, and rollback preparation.

This decision approves the technical direction, not the creation of cloud accounts, provisioning of paid resources, production release, or deletion of the SQLite implementation.

## 2. Decision rationale and consequences

This arrangement gives genuine users a conventional browser interface while retaining the established Python domain and application layers:

- Next.js provides the responsive member, librarian, and administrator experience.
- FastAPI exposes versioned HTTP endpoints around existing application services.
- PostgreSQL preserves the relational model, constraints, transactions, and reporting patterns more closely than a document database would.
- Supabase solves Render Free's inability to persist a local SQLite file.
- Each provider can be upgraded independently when the free tier becomes inadequate.

The consequences are:

- SQLite will no longer be the production system of record after cutover.
- PostgreSQL persistence and migration work must be completed before the API can run on Render with genuine data.
- Requests cross two public provider boundaries, so region placement, TLS, latency, egress, credentials, and failure handling become first-class concerns.
- Vercel and Render use different origins by default; browser authentication requires an intentional domain, cookie, CORS, and CSRF design.
- Three providers create three sets of quotas, terms, logs, incidents, and configuration that must be monitored.

## 3. Selected-provider assessment

This is a dated snapshot. Pricing, quotas, terms, region availability, and free-tier policies must be rechecked immediately before provisioning and release.

| Provider and role | Current free-tier findings | Decision |
| --- | --- | --- |
| Vercel: Next.js dashboard | Hobby supports Next.js and custom domains but is limited to personal, non-commercial use. Usage caps can pause the project until the allowance resets. | Selected. Hobby is acceptable only when the deployment qualifies under its terms; an institutional or commercial deployment must use an eligible paid plan. |
| Render: FastAPI backend | Free web services receive 750 instance-hours per workspace monthly, spin down after 15 idle minutes, can take about one minute to wake, cannot scale beyond one instance, and may be suspended for unusually high service-initiated external traffic. Render currently supports Python 3.14 natively. | Selected. Free is for development and a limited pilot; upgrade when cold starts, support, scaling, or external-database traffic become unacceptable. |
| Supabase: PostgreSQL database | Free includes a 500 MB database quota on shared CPU with up to 500 MB RAM, 5 GB egress, and two active projects. Projects with insufficient activity over seven days can be paused. Free projects have no automatic backups or point-in-time recovery. | Selected. Free is acceptable for development and a controlled pilot with independent backups; genuine use requires an upgrade if pausing, capacity, backup, or recovery limits are unacceptable. |

### 3.1 Free-stack verdict

Vercel Hobby, Render Free, and Supabase Free can form a zero-cost development or personal demonstration stack. They are not collectively equivalent to production infrastructure:

- Render can sleep after 15 idle minutes.
- Supabase can pause a low-activity project after seven days.
- A first request can therefore encounter backend cold-start delay or database unavailability.
- Supabase Free does not supply automatic database backups.
- Vercel Hobby cannot be assumed to cover organizational, institutional, or commercial use.

The provider choices are approved, but the applicable paid or free tiers remain a release decision. Genuine user data must not be accepted until the selected tiers satisfy the recovery, availability, and terms-of-use gates in this plan.

### 3.2 Idle, paused, and suspended service behavior

The three deployed components do not share one wake-up mechanism:

| Condition | What a user request does | Required operational response |
| --- | --- | --- |
| Vercel dashboard is available, Render is warm, and Supabase is active | The request follows the normal browser-to-API-to-database path. | None. |
| Render Free has spun down after 15 minutes without inbound traffic | A browser or Vercel request that actually reaches FastAPI wakes Render automatically. Render documents a wake time of about one minute. Merely viewing a cached or static frontend page does not wake it. | The dashboard shows a bounded `backend_waking` state and retries safe requests with backoff and jitter. No owner action is normally required. |
| Supabase Free is approaching inactivity pausing | Genuine database requests during the warning period can prevent the pause. Supabase normally warns the project owner by email before pausing. | Monitor the owner mailbox and provider dashboard. Do not create artificial keep-alive traffic solely to evade free-tier policy. |
| Supabase Free has already been paused | Requests from Render cannot resume it. FastAPI cannot become ready because PostgreSQL is unavailable. | A project owner opens Supabase Studio, selects the project, and confirms **Resume project**. The API then reconnects through its pool. |
| Render has been suspended because of quota exhaustion or policy/resource limits | This is not an ordinary idle cold start and an HTTP request is not a reliable recovery mechanism. | Follow the Render notice: wait for an applicable allowance reset, correct the cause, or move to a paid plan. |

If both Render and Supabase are inactive, Vercel can still load the dashboard, Render will wake on the first API call, and that API call will remain unavailable until an owner manually resumes Supabase. The UI must distinguish a slow cold start from a confirmed `database_unavailable` response; it must never promise that Supabase will wake automatically.

Operational and interface requirements:

- `/health/live` reports only whether the FastAPI process is running.
- `/health/ready` performs a short, bounded database check and reports whether the API can serve database-backed requests.
- The frontend API client maps Render's cold-start response, temporary gateway failure, or bounded timeout to a local `service_warming` state because FastAPI cannot emit an application error while its process is asleep. Once FastAPI is running, dependency failures use a stable `503 database_unavailable` envelope plus `Retry-After` where appropriate, without exposing provider credentials or internal connection details.
- The frontend switches from its normal loading skeleton to a clear waking message after a measured threshold, stops retrying after a bounded interval, and offers a manual retry.
- Automatic retries are allowed for idempotent reads. State-changing requests are retried only when protected by an idempotency key and when the outcome of the earlier attempt is known or safely recoverable.
- Monitoring must not be configured merely to defeat Render sleep or Supabase inactivity rules. A deployment that requires continuous unattended availability must use tiers that provide it.

## 4. Target deployment architecture

```text
                         Git repository
                       /                \
                      v                  v
             Vercel deployment     Render deployment
                      |                  |
                      v                  v
Browser -- HTTPS --> Next.js -- HTTPS --> FastAPI
                    dashboard           API
                                           |
                                           | TLS / PostgreSQL protocol
                                           v
                                  Supavisor session pooler
                                           |
                                           v
                                  Supabase PostgreSQL

CI migration job -----------------------> PostgreSQL direct/session connection
Scheduled logical backup ---------------> independent encrypted storage
```

Recommended production-style domains:

- `app.<project-domain>` for Vercel; and
- `api.<project-domain>` for Render.

Using subdomains of the same registrable domain keeps the frontend and API same-site while still cross-origin. It permits secure host-only API cookies without depending on third-party cookies. Exact credentialed CORS rules and CSRF protections are still required.

Default `vercel.app` and `onrender.com` domains are acceptable for non-authenticated smoke tests. They must not become the final authenticated-browser design without a separate decision because cross-site cookie behavior is increasingly restricted by browsers.

## 5. Responsibility and trust boundaries

### 5.1 Vercel and Next.js

- Render user interfaces, collect input, and call only the versioned FastAPI API.
- Contain no database password, Supabase secret key, Render secret, password hash, or session-token hash.
- Receive only a public API base URL and other explicitly public configuration.
- Treat route guards and hidden controls as usability features, not authorization.
- Avoid server-side rendering unless a documented dashboard requirement needs it.

### 5.2 Render and FastAPI

- Authenticate requests and enforce account, ownership, and role authorization.
- Validate HTTP input and call existing application services.
- Own all database transactions through repository and unit-of-work interfaces.
- Issue, revoke, and expire browser sessions.
- Expose safe liveness and readiness endpoints without revealing secrets.
- Return stable versioned response and error contracts to Next.js.

### 5.3 Supabase and PostgreSQL

- Persist all production accounts, catalog, inventory, circulation, financial, engagement, reporting, migration, and session data.
- Accept database connections only from trusted backend, migration, and backup processes.
- Use a non-exposed application schema and a least-privilege application database role.
- Keep the Supabase Data API disabled because the browser will not use it. If it cannot be disabled for an environment, revoke Data API roles and verify that no application table is exposed.
- Never expose the PostgreSQL connection string or a Supabase secret/service-role key to Next.js client code.

## 6. Authentication, sessions, CORS, and CSRF

The first web version retains application-managed authentication:

1. Next.js submits credentials to FastAPI over HTTPS.
2. FastAPI finds the account through the PostgreSQL repository.
3. The existing Argon2id password service verifies the password and rehashes when needed.
4. FastAPI creates a cryptographically random opaque session token.
5. PostgreSQL stores only the token hash with user, creation, expiry, revocation, and last-use metadata.
6. FastAPI returns the token in a `Secure`, `HttpOnly` cookie.

Security rules:

- Use a host-only API cookie unless a demonstrated requirement needs a wider cookie domain.
- Use `SameSite=Lax` with the recommended same-site subdomains; revisit the setting only after browser testing.
- Permit credentialed CORS requests from the exact production Vercel origin and explicitly approved preview origins only.
- Reject unrecognized `Origin` values on unsafe methods.
- Require CSRF protection for state-changing cookie-authenticated requests.
- Rotate the session identifier after authentication and privilege changes.
- Rate-limit login, bootstrap, recovery, and other sensitive endpoints.
- Revoke all active sessions when an account is deactivated or its security state changes.
- Keep role and active-account checks in the application service layer instead of trusting frontend state.

Supabase Auth is intentionally excluded so that this milestone does not combine a database migration, API conversion, dashboard build, and identity-provider migration.

## 7. SQLite-to-Supabase PostgreSQL migration

### 7.1 Application code impact

The existing application services already depend on repository and unit-of-work protocols rather than directly on `sqlite3`. Domain entities, business policies, authorization rules, Argon2id hashes, and most service tests can remain unchanged.

Required additions and changes:

- Psycopg 3 as the Python 3.14-compatible PostgreSQL driver;
- a deliberately small Psycopg connection pool;
- a PostgreSQL connection factory configured through `DATABASE_URL`;
- `PostgresUnitOfWork` implementing the existing `UnitOfWork` protocol;
- PostgreSQL repositories for users, books, copies, reservations, loans, fines, settlements, book requests, feedback, and reporting;
- a database-maintenance interface with separate SQLite and PostgreSQL implementations;
- PostgreSQL-native schema migrations stored under `supabase/migrations/`; and
- repository contract tests against a real PostgreSQL instance.

Keep the implementation synchronous initially. Psycopg's synchronous API fits the current service layer and normal FastAPI `def` handlers without forcing an unrelated asynchronous rewrite.

### 7.2 Schema and SQL changes

| SQLite behavior | Supabase PostgreSQL replacement |
| --- | --- |
| `INTEGER PRIMARY KEY` identifiers | `BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` |
| ISO 8601 timestamps stored as `TEXT` | native `TIMESTAMPTZ` with timezone-aware Python `datetime` values |
| `is_active` constrained to integer `0` or `1` | native `BOOLEAN` |
| `COLLATE NOCASE` and case-insensitive `LIKE` | explicit `lower(...)` indexes and comparisons plus `ILIKE` search |
| SQLite `STRICT` tables | remove `STRICT`; PostgreSQL types enforce column typing |
| `?` placeholders | Psycopg parameter binding |
| `cursor.lastrowid` | `INSERT ... RETURNING id` |
| `publication_year IS ?` | `IS NOT DISTINCT FROM` or explicit null/equality branches |
| `sqlite3.IntegrityError` | map specific PostgreSQL constraint exceptions to existing repository errors |
| `PRAGMA` and `BEGIN IMMEDIATE` | PostgreSQL constraints, timeouts, locks, transactions, and an explicit isolation policy |
| SQLite file backup and replacement | PostgreSQL logical dump, restore, and provider recovery processes |

Partial unique indexes and most check constraints can be preserved. Monetary values remain integer minor units. Existing Argon2id password hashes must be transferred byte-for-byte.

### 7.3 Existing-data transfer

Do not pipe a raw SQLite `.dump` into PostgreSQL. Use a repeatable, one-purpose Python migration utility:

1. Create the PostgreSQL schema from version-controlled Supabase migrations.
2. Put the SQLite application into read-only maintenance mode.
3. Create and validate a final SQLite online backup.
4. Read the snapshot in foreign-key order and insert rows into PostgreSQL inside controlled transactions.
5. Preserve identifiers and relationships, then advance PostgreSQL identity sequences beyond imported maximum identifiers.
6. Convert timestamp strings to timezone-aware values and integer booleans to booleans.
7. Preserve password hashes and monetary minor units without transformation.
8. Compare table counts, identifiers, constraints, active loans, reservations, outstanding balances, and reports.
9. Run service and API smoke tests against PostgreSQL.
10. Retain the final SQLite snapshot and documented rollback procedure for the agreed observation period.

### 7.4 Database rewrite workstream

The database change is an adapter rewrite and controlled data migration, not a rewrite of the domain model or business rules. The existing `UnitOfWork` and repository protocols are the seam that permits SQLite and PostgreSQL to coexist during the transition.

Implementation sequence:

1. Freeze the current SQLite behavior with repository contract tests and service-level characterization tests.
2. Move schema ownership out of Python string constants for the PostgreSQL path and into ordered, immutable files under `supabase/migrations/`.
3. Add a PostgreSQL connection-pool owner and `PostgresUnitOfWork`; one entered unit of work receives one checked-out connection and one transaction.
4. Port one repository capability at a time, using Psycopg parameters, `RETURNING`, native timestamps and booleans, and PostgreSQL constraint-error mapping.
5. Extend repository contracts only where concurrent correctness requires an explicit capability such as `get_for_update`, conditional status transition, or a paginated projection. Do not leak raw Psycopg connections into services.
6. Run the same contract suite against SQLite and a real disposable PostgreSQL database. Mocks are insufficient for constraints, isolation, locks, query plans, or SQL dialect behavior.
7. Add PostgreSQL-native integration tests for lock contention, deadlock recovery, uniqueness races, connection exhaustion, and transaction rollback.
8. Build the snapshot migration utility with dry-run, structured progress, a migration-run identifier, source/target counts, and a reconciliation report. Never dual-write SQLite and PostgreSQL; that would create a distributed consistency problem without providing a safe benefit at this project scale.
9. Rehearse migration from a copied SQLite database, time the maintenance window, and record exact rollback criteria.
10. At cutover, stop writes, create the final SQLite backup, import and reconcile once, switch `DATABASE_URL`, run smoke tests, and either open the web application or roll back before accepting new writes.

Migration validation must cover more than row counts. It must compare primary and foreign keys, normalized usernames and ISBNs, active-loan uniqueness, reservation order, copy status versus active loans, renewal counts, fine and settlement totals, request/feedback states, nulls, timestamps, identity sequences, and Argon2id hashes. A deterministic manifest containing source-file checksum, schema version, row counts, migration version, start/end time, and reconciliation outcome becomes a retained cutover artifact.

## 8. Supabase connection, schema, and recovery policy

- Use Supavisor **session mode** on port `5432` for normal Render application traffic when a direct IPv6 connection is unavailable. Render is a persistent backend while awake, which matches session mode.
- Use the direct connection for migrations, `pg_dump`, and administrative tools when their network supports IPv6. Otherwise, use a compatible session-pooler connection after testing.
- Do not use Supavisor transaction mode by default. If later selected for transient workloads, disable prepared statements and test every transaction-dependent operation.
- Keep the application pool small and below Supabase connection limits. Avoid stacking an oversized client pool on top of Supavisor.
- Select Render and Supabase regions with the lowest measured round-trip latency available to the intended users.
- Require TLS for all database connections.
- Store runtime database credentials only in Render secrets and migration credentials only in the CI secret store.
- Create an application schema that is not exposed through Supabase REST or GraphQL APIs.
- Apply all schema changes through migration files. Do not make unrecorded production changes through the Supabase dashboard.
- Supabase Free has no automatic backups. Schedule encrypted logical dumps to storage outside Supabase and complete regular restore drills.
- Treat automatic project pausing as a pilot limitation, not as a recovery or backup mechanism.

### 8.1 Read/write concurrency and transaction safety

PostgreSQL's MVCC permits ordinary reads to proceed alongside writes, but multi-step library policies still require deliberate serialization. The default isolation level will remain `READ COMMITTED`; stronger isolation is selected for an individual operation only when its invariants cannot be expressed safely with row locks, conditional writes, and constraints.

Transaction rules:

- A FastAPI request never shares a Psycopg connection or active unit of work with another request.
- Open a transaction immediately before database work and commit or roll back immediately after it. Never hold a transaction while waiting for browser input, network calls, password hashing, file I/O, or sleeps.
- Use atomic SQL and constraints instead of read-then-write where possible. Status changes use a compare-and-set form such as `UPDATE ... WHERE id = ? AND status = ?`; zero affected rows becomes a domain conflict.
- Preserve partial unique constraints for one active loan per copy and one active reservation per user/title, and the unique settlement-per-fine constraint. Constraint violations remain the final race-safe guard even when services pre-check for friendlier errors.
- Use `SELECT ... FOR UPDATE` only on rows that protect a business decision. Do not lock whole tables during request handling.
- For checkout, lock the borrower row before enforcing the active-loan limit, then lock the book aggregate and selected copy before checking availability and the reservation queue.
- For reservation creation, checkout, return, and renewal, lock the book row as the stable aggregate mutex before reading or changing its active reservation queue. Lock the affected copy, reservation, loan, and fine rows only as needed.
- For account deactivation, fine settlement, request review/acquisition, and feedback review, lock or conditionally update the target row so two staff actions cannot both succeed from the same starting state.
- When more than one row of the same type is touched, acquire them in ascending primary-key order. Across types, use the documented order: user, book, copy, reservation, loan, fine, settlement/request/feedback. Any exception requires a code comment and a concurrency test.
- PostgreSQL migration jobs use a transaction-scoped advisory lock with one project-specific key. Runtime circulation does not use session-level advisory locks.

Deadlocks cannot be promised away completely. PostgreSQL detects them and aborts one participant, so the application must both minimize and recover from them:

- Map SQLSTATE `40P01` (deadlock) and `40001` (serialization failure) to a whole-transaction retry policy: at most two retries with short exponential backoff and jitter.
- Retry only inside the application-service boundary and only before any irreversible external side effect. Re-read all state on every attempt.
- Protect state-changing HTTP commands with an idempotency key stored with the committed result, especially checkout, return, fine settlement, acquisition, and administrative commands.
- If retries are exhausted, roll back, return a stable `409 conflict_retry` or `503 transaction_busy` response, and log a correlation ID rather than database details.
- Configure bounded per-transaction `lock_timeout`, `statement_timeout`, and `idle_in_transaction_session_timeout`. Initial candidates are 2 seconds, 5 seconds, and 10 seconds respectively; load tests must tune them before release.
- Record slow lock waits, deadlocks, pool wait time, transaction duration, and retry counts. Investigate repeated conflicts instead of raising retry counts indefinitely.

### 8.2 Database query and storage optimization

Optimization will follow measurements, not index accumulation:

- Replace unbounded repository methods such as `list_all()` in web-facing paths with filtered pagination. Prefer keyset pagination on stable `(created_at, id)` or `(title_sort_key, id)` orderings; cap page size server-side.
- Add projection/query repositories for dashboard views so the current per-item lookups do not become N+1 query patterns. Fetch related book, copy, borrower, loan, and aggregate data using measured joins or bounded batches.
- Select only response columns, perform counts and sums in PostgreSQL, and never load an entire catalog to filter in Python.
- Preserve useful partial/composite indexes from SQLite, then add indexes for actual PostgreSQL filters, joins, and ordering: normalized username/ISBN lookup; book identity; copy availability; active-loan and user-loan views; reservation queue order; outstanding fines; and pending review queues.
- Implement case-insensitive catalog search first with normalized expression indexes. Evaluate `pg_trgm` only after realistic search data shows that substring/fuzzy search needs it.
- Capture representative `EXPLAIN (ANALYZE, BUFFERS)` plans in a non-production-like test environment and use Supabase Query Performance/Index Advisor as evidence. An advisor recommendation is reviewed, tested, and versioned rather than applied blindly.
- Track slow queries and frequently executed queries with provider-supported statistics. Establish a baseline before optimization and compare p50, p95, rows examined/returned, and buffer activity afterward.
- Avoid over-indexing: every index consumes storage and makes writes more expensive. Remove confirmed redundant or unused indexes only through a reviewed migration.
- Let PostgreSQL autovacuum and auto-analyze maintain tables by default; monitor dead tuples and stale statistics before changing provider defaults.
- Use `CREATE INDEX CONCURRENTLY` for a large live table only through a migration procedure designed for its transaction restrictions and failure cleanup. Small pre-release schemas should receive indexes before user traffic begins.
- Store cover images or future documents outside PostgreSQL object rows; retain only metadata and object references. That storage provider requires a later explicit decision.

### 8.3 Connection pool and free-tier resource budget

Capacity must be bounded at each layer so a traffic burst queues predictably instead of exhausting Supabase or Render:

| Layer | Initial pilot policy | Overload behavior and evidence |
| --- | --- | --- |
| Vercel/Next.js | Prefer static layouts and browser calls to FastAPI; avoid unnecessary Vercel functions and request-time SSR. Collapse duplicate fetches and never poll merely to keep another provider awake. | Track bandwidth, function use if any, build size, Core Web Vitals, and plan limits. |
| Render/FastAPI | Start with one Uvicorn process on the single Free instance. Use synchronous `def` handlers for the existing synchronous service/Psycopg path so FastAPI runs them in its worker thread pool. | CPU-heavy Argon2 verification, reports, and database work receive rate/concurrency limits. Queue waits are bounded; overload returns `429` or `503` rather than growing without limit. |
| Psycopg client pool | Start at `min_size=0`, `max_size=5`, acquire on demand, validate connections after a Supabase resume, and set a short acquisition timeout. Open/close the pool in FastAPI lifespan. | A request that cannot obtain a connection within the tested deadline fails cleanly. Pool-in-use, pool-waiting, acquisition latency, and leaks are monitored. Values are configuration, not hard-coded business rules. |
| Supavisor session pooler | Use the current dashboard-reported limit as authoritative and reserve headroom for Supabase services, CI migration, backup, and administration. The application pool must remain a small fraction of the available database connections. | Verify pool mode, pool size, and connection charts at provisioning and before each tier change. Never assume published free-tier numbers are permanent. |
| Supabase PostgreSQL | Keep transactions and queries short, paginate results, and test against the selected compute size with production-like data. | Monitor CPU, memory, database size, connection usage, cache hit behavior, egress, slow queries, and lock waits. Upgrade before sustained saturation. |

One Render process and five database connections do not mean only five signed-in users; inactive browser sessions consume no database connection. They bound simultaneous database transactions. The initial supported envelope is a controlled pilot validated with at least 20 mixed concurrent users and a separate burst test of 50 virtual users. Admission limits and an upgrade are required if pool wait, CPU, memory, errors, or latency exceed the gates in this plan.

Password verification is intentionally expensive. Login, password change, bootstrap, and recovery endpoints therefore receive per-IP and per-account rate limits plus a small process-local concurrency limiter. Reporting endpoints use pagination/pre-aggregation and stricter frequency limits so one report cannot starve circulation operations. In-memory rate limits are pilot-only; multiple Render instances later require a shared limiter or an edge/provider control.

## 9. API and dashboard scope

### 9.1 FastAPI

- Version endpoints under `/api/v1`.
- Generate and retain the OpenAPI contract.
- Use Pydantic request and response types independent of persistence rows.
- Define consistent errors, pagination, filtering, sorting, timestamps, and money representations.
- Add authentication dependencies without moving authorization out of application services.
- Expose catalog, circulation, finance, engagement, recommendation, reporting, and maintenance capabilities incrementally.

### 9.2 Next.js

The first dashboard must provide:

- bootstrap, registration, sign-in, sign-out, and session handling;
- catalog search, details, availability, and recommendations;
- member loans, renewals, reservations, fines, requests, and feedback;
- librarian circulation, inventory, request, feedback, and fine workflows;
- administrator account and maintenance workflows with explicit destructive-action confirmation;
- role-aware navigation, loading, empty, validation, and recoverable error states; and
- responsive, keyboard-accessible, screen-reader-friendly interfaces with visible focus and sufficient contrast.

Public SEO pages, native applications, and real-time sockets are not required for the first release.

### 9.3 Wrapping the existing Python application in FastAPI

FastAPI is a new delivery adapter around the existing object-oriented application; it does not replace the domain and service layers, and API routers must never call CLI screens or SQLite repositories directly.

Proposed backend structure:

```text
src/library_management/
  api/
    app.py                 # application factory and lifespan
    dependencies.py        # authenticated principal and service dependencies
    errors.py              # domain-to-HTTP error mapping
    middleware.py          # correlation, origin, security, and timing controls
    schemas/               # Pydantic HTTP request/response contracts
    routers/               # auth, catalog, circulation, finance, engagement, admin
  domain/                  # unchanged framework-independent model
  services/                # unchanged business use cases where practical
  repositories/
    sqlite/                # retained migration/CLI adapter
    postgres/              # deployed persistence adapter
```

Adaptation rules and sequence:

1. Introduce an application factory that receives settings and constructs the Psycopg pool, unit-of-work factory, password service, application services, and routers. Importing a module must not open a database connection.
2. Use FastAPI lifespan to open the pool, verify configuration/migration compatibility, and close resources cleanly. A failed database readiness check must not expose secrets.
3. Keep current service methods as the authoritative use cases. Where an HTTP request requires several existing calls atomically, add a cohesive application-service method instead of coordinating a transaction in the router.
4. Implement normal synchronous endpoints as `def` while repositories use synchronous Psycopg. Do not place blocking service or database calls directly inside `async def` handlers. Reconsider an end-to-end async conversion only after profiling shows that connection concurrency, rather than free-tier CPU/memory, is the bottleneck.
5. Use thin routers: parse a Pydantic input schema, obtain the authenticated principal, call one use case, map its result to a response schema, and allow central exception handlers to produce the error envelope.
6. Keep HTTP schemas separate from domain dataclasses and database rows. The API owns external field names, pagination cursors, timezone-aware ISO timestamps, integer minor-unit money values plus currency code, and versioned compatibility.
7. Map validation to `422`, unauthenticated access to `401`, insufficient permission to `403`, absence to `404`, expected state races to `409`, rate limiting to `429`, and temporary dependency failure to `503`.
8. Add opaque browser-session persistence and CSRF handling before exposing protected operations. Never convert the existing password hash into a frontend token or store authorization state only in Next.js.
9. Deliver vertical slices: health and session, read-only catalog, member circulation, librarian workflows, finance/engagement, then administration and reporting. Keep the CLI working through the same services during the transition.
10. Generate a typed frontend client from the reviewed OpenAPI document or validate an equivalent handwritten client against it in CI. Breaking API changes require a new version or an explicit compatibility window.

Testing layers include router tests with controlled service doubles, service tests against repository contracts, PostgreSQL integration tests, OpenAPI snapshot/compatibility checks, and end-to-end browser journeys. The deployed API command starts an ASGI server against the application factory; schema migration never runs inside that start command.

### 9.4 Frontend latency and loading-time strategy

The dashboard must remain understandable when its static shell is fast but its backend is cold or its database is unavailable:

- Use Next.js App Router layouts and Server Components for stable, non-secret presentation where they reduce client JavaScript, but avoid request-time server rendering that blocks the whole page on a sleeping Render API. Authenticated operational data is fetched from FastAPI with an intentional client boundary.
- Ship route-level `loading` and error states, Suspense boundaries around independent panels, skeletons with stable dimensions, and progressive disclosure. Navigation and sign-out controls remain responsive while a data panel loads.
- Classify failures in one API client: `warming`, `database_unavailable`, `offline`, `timeout`, `unauthorized`, `forbidden`, `conflict`, and unexpected. Do not show a permanent spinner or raw provider response.
- On a likely Render cold start, retry safe reads with exponential backoff and jitter for a bounded window of approximately 75 seconds, tuned from the deployment spike. Deduplicate retries across components so one page does not create a wake-up stampede.
- Apply client timeouts and `AbortController`; cancel stale catalog searches and requests from abandoned routes. Debounce search input and require a useful minimum query length where appropriate.
- Remove request waterfalls. Fetch independent resources in parallel and add purpose-built summary endpoints when one screen would otherwise make many sequential API calls. Do not create oversized all-purpose responses.
- Paginate and virtualize long tables where measurement justifies it. Preserve filters and pagination in the URL so reload and navigation do not refetch unnecessary pages.
- Cache versioned static assets aggressively. Cache stable catalog metadata only with explicit `ETag`/revalidation rules; do not cache sessions, permissions, current fines, reservation position, or live copy availability as if they were immutable.
- Use `next/font` with the approved custom font, the smallest required subset and weights, and a fallback with compatible metrics. Limit icon and component-library imports, lazy-load heavy administrator/reporting features, and inspect production bundles with `@next/bundle-analyzer`.
- Use optimized images with explicit dimensions, responsive sizes, lazy loading below the fold, and restrained cover-image quality. A placeholder or textual fallback is required when no cover is stored.
- Prefer CSS and accessible native controls over heavy runtime UI packages. Every dependency must justify its transferred JavaScript and maintenance cost.
- Let Vercel serve static assets and provider-supported compression. Enable API compression only after payload measurement; small JSON responses should not pay avoidable CPU cost on Render.

Performance budgets are measured separately for warm and cold paths. Initial warm-path targets are Core Web Vitals in the "good" range, no unexpected layout shift from loaders, cached catalog reads below 500 ms p95, and ordinary writes below 1 second p95 from the target region. CI records route bundle sizes and fails on an agreed regression threshold established from the first production build. The deployment spike records time to first shell, Render wake duration, readiness duration, API latency, database time, payload size, and full interaction time so optimization addresses the actual slow segment.

## 10. Monorepo, local development, and deployment configuration

### 10.1 Monorepo decision and analysis

The Python backend, Next.js frontend, database migrations, documentation, and deployment definitions will remain in one local directory and one GitHub repository. GitHub hosts the source and collaboration history; it does not host the running application. Locally, the components run as separate processes. In deployment, Vercel and Render build separate artifacts from the same commit and Supabase applies only the versioned database migrations.

The monorepo is the preferred design at the current scale:

| Consideration | One repository | Separate repositories | Decision |
| --- | --- | --- | --- |
| API and UI contract changes | One pull request can update FastAPI, OpenAPI, generated client, and UI atomically. | Requires coordinated versions and merges across repositories. | Monorepo is safer while one project owns both sides. |
| Database changes | Migration, compatible repository code, API contract, and affected UI can be reviewed together. | Greater risk of deploying an incompatible combination. | Monorepo supports the required expand-contract sequence. |
| Existing Python code | Remains at its current root paths with no packaging churn. | A backend repository or a forced `backend/` move adds immediate migration work. | Keep the Python project at the repository root. |
| Deployment independence | Requires provider root/build filters and a controlled release workflow. | Naturally separate triggers. | Filters and CI orchestration provide sufficient isolation. |
| Secrets and permissions | Must be scoped in each provider and workflow, not treated as repository-wide runtime configuration. | Repository access can be split more strictly. | Current single-owner/small-team model does not justify a split. |
| Repository size and tooling | One checkout and issue history; CI must avoid unnecessary work. | Smaller checkouts and specialized pipelines. | Current codebase is small enough for a monorepo. |

The repository may be split later if the frontend and backend acquire independent teams or release schedules, materially different access controls, compliance isolation, very large build histories, or provider limitations that path filters cannot solve. Until one of those conditions exists, a split would add contract-versioning and release-coordination work without adding meaningful runtime isolation.

### 10.2 Approved asymmetric layout

Do not move the established Python package into a new `backend/` directory during this transition. Add the web application as an isolated subproject and keep deployment/control files discoverable at the root:

```text
.github/
  workflows/
    ci.yml                       # always-reported required CI result
    deploy-production.yml        # ordered migrations, API, then dashboard
contracts/
  openapi.json                   # reviewed API contract artifact
development-plans/
legacy/
scripts/
  dev.ps1                       # local orchestration and preflight
  check.ps1                     # local equivalent of CI quality gates
src/library_management/
  api/                          # FastAPI delivery adapter
  domain/
  repositories/
    sqlite/
    postgres/
  services/
supabase/
  config.toml                   # safe local Supabase configuration
  migrations/                   # immutable ordered PostgreSQL migrations
  seed.sql                      # synthetic local data only
tests/                          # Python unit, contract, integration, migration tests
web/
  package.json
  package-lock.json             # one selected and committed JS lockfile
  src/
    app/
    components/
    lib/api/generated/          # generated client committed for isolated Vercel builds
  tests/                        # component/frontend tests
  .env.local.example
.env.example                    # redacted backend/local configuration contract
.python-version
pyproject.toml
requirements.txt
render.yaml
README.md
```

There is only one JavaScript application, so adding Turborepo, Nx, npm workspaces, or a root Node package is not justified initially. `web/` owns its Node dependencies and lockfile. Python dependencies remain owned by `pyproject.toml` and `requirements.txt` at the repository root. Cross-language sharing happens through `contracts/openapi.json`, not by importing source files across application boundaries.

The OpenAPI artifact is generated deterministically from FastAPI, reviewed in the same change as an API contract modification, and checked for drift in CI. The typed client is generated into `web/src/lib/api/generated/` and committed so Vercel can build from `web/` without permission to read Python files outside its root. Hand edits to generated files are prohibited.

### 10.3 Local execution model

The default Windows/PowerShell development path uses three independently observable processes:

```text
Browser -> Next.js dev server (localhost:3000)
                    |
                    v
           FastAPI/Uvicorn (localhost:8000)
                    |
                    v
       Supabase local PostgreSQL (CLI-managed port)
```

Local workflow:

1. Clone the one GitHub repository and create the Python 3.14 `.venv`.
2. Install the root Python development dependencies and the locked dependencies under `web/`.
3. Start the Supabase local stack from the repository root using its CLI and a Docker-compatible runtime. Use explicit `--local` or `--linked` flags for database commands so a local command cannot accidentally target a remote project.
4. Recreate the local database from committed migrations and synthetic seed data. No copied production user data is permitted in local development.
5. Start FastAPI on `127.0.0.1:8000` with local-only settings and exact CORS allowance for `http://localhost:3000`.
6. Start Next.js on `localhost:3000` with only the public local API base URL.
7. Run backend, frontend, contract, database, and browser checks before opening a pull request.

`scripts/dev.ps1` will perform preflight checks, print the selected local endpoints, and orchestrate or clearly instruct the three processes without embedding credentials. Each component must remain startable separately for debugging. Stopping the wrapper must shut down only processes that it started; it must not delete local volumes or reset the database. Destructive reset and seed operations require an explicit separate command and confirmation.

The local environment must never fall back silently to production URLs. Settings validation rejects mixed environments, including a local API with a production database or a local frontend with an unapproved production API. Root and frontend example environment files document names and safe placeholders; `.env`, `.env.local`, Supabase temporary state, provider tokens, and database dumps remain ignored.

### 10.4 Provider build boundaries from one GitHub repository

| Consumer | Repository scope | Trigger policy | Secrets and outputs |
| --- | --- | --- | --- |
| Vercel project | Root Directory is `web/`. It builds the committed Next.js project and generated client, not Python source. Access to files outside the root stays disabled unless a later documented dependency requires it. | Preview builds occur for relevant frontend pull-request changes. Production deployment is promoted only after the compatible API commit is healthy. Avoid rebuilding for documentation/backend-only changes using verified monorepo project settings. | Receives public API URL and frontend-only configuration. It never receives `DATABASE_URL`, password pepper, session-hash secret, Supabase database credentials, or Render deploy hook. |
| Render web service | Repository root remains the service root because `pyproject.toml`, `requirements.txt`, and `src/` already live there. The build command installs only Python/backend dependencies. | Build filters include backend/config files and exclude `web/**`, local state, and documentation-only changes. Production auto-deploy is `off` when the ordered CI deployment workflow is active; otherwise `checksPass` is acceptable only for changes with no migration ordering requirement. | Receives backend runtime secrets and emits the FastAPI service. It receives no Vercel token or frontend build secrets. |
| Supabase migration job | Reads only `supabase/` plus the migration/reconciliation tooling it explicitly needs. | Runs in CI after all checks and approval, before the dependent Render production deployment. It is never triggered by a frontend-only change. | Receives a narrowly scoped migration connection secret in the protected GitHub production environment, not in pull-request jobs. |
| GitHub Actions | Checks out the repository and runs jobs selected from the changed-path graph. | Pull requests run required CI; production jobs run only from the protected production branch/environment. | Stores deployment/migration credentials as environment secrets with approvals where available. Logs and artifacts are scanned/redacted. |

Render documents that files outside a configured service root are unavailable at build/runtime, which is why the backend retains the repository root and uses build filters instead of selecting `src/` as its root. Vercel officially supports selecting `web/` as a monorepo Root Directory. A shared repository therefore does not require either provider to build or execute both applications.

### 10.5 CI ownership and change detection

One top-level CI workflow will report a stable required `ci` result on every pull request. It detects affected areas internally and runs the appropriate jobs:

| Changed paths | Required jobs |
| --- | --- |
| `src/**`, `tests/**`, Python configuration | Ruff, Pyrefly, Pytest, package/build check |
| `supabase/**`, PostgreSQL repositories, migration tooling | Clean database reset, migration lint/test, repository contracts, concurrency and reconciliation tests |
| `contracts/**`, API schemas/routers | Backend tests, OpenAPI drift/compatibility check, frontend client regeneration check, frontend type/tests |
| `web/**` | Locked install, lint, TypeScript, component tests, production build, bundle budget |
| deployment workflows, `render.yaml`, environment contracts | Configuration validation and applicable backend/frontend builds |
| documentation only | Documentation checks and a successful `ci` summary without unnecessary application builds |

Do not make separately path-filtered workflows themselves mandatory branch checks: GitHub documents that skipped path-filtered workflows can remain pending and block merging. Instead, the always-started workflow uses change detection to skip jobs deliberately and finishes with one required summary job. Shared contract, migration, dependency-lock, and deployment changes force all affected jobs.

Required controls across the monorepo:

- Protect the production branch; merge reviewed pull requests only after the stable CI result succeeds.
- Pin Python to the approved 3.14 patch line with `.python-version` or Render configuration and pin the selected Node major line in `web/`.
- Add FastAPI, an ASGI server, Psycopg, and PostgreSQL migration dependencies only when their implementation phase begins.
- Keep Pytest, Pyrefly, and Ruff as Python quality gates; add TypeScript checking, frontend linting, component tests, production builds, and browser tests.
- Treat both Python and Node lock/dependency changes as security-sensitive review items and enable automated dependency update/security reporting when the GitHub repository is connected.
- Validate all required environment variables at startup without logging their values.
- Keep all real secret files out of Git and provide redacted example configuration.
- Add `/health/live` for process health and `/health/ready` for database and migration readiness.

Configuration boundaries remain explicit:

| Environment | Vercel/Next.js | Render/FastAPI | Supabase/PostgreSQL |
| --- | --- | --- | --- |
| Local | Local Next.js and public local API URL | Local FastAPI and local PostgreSQL URL | Supabase CLI local stack |
| Pull-request preview | Preview-specific API URL or a mocked contract service; never production credentials | Isolated preview API only when its database is also isolated | Disposable database or dedicated non-production project/schema with cleanup policy |
| Staging | Stable staging dashboard URL | Stable staging API | Dedicated staging project is preferred |
| Production | Production API URL only | Production database URL, origin policy, session settings, and runtime secrets | Production application role, migrations, backup credentials, and data |

A frontend preview must not connect to production merely because no preview backend exists. Until an isolated preview stack is affordable, contract mocks plus local end-to-end tests are safer than granting arbitrary preview URLs access to production sessions and data.

## 11. Migration and deployment workflow

### 11.1 Change execution loop

Every implementation change follows the numbered plan that owns it:

1. Confirm the active `development-plan-xx.md` prerequisites, scope, non-goals, risks, and exit criteria.
2. Create a focused Git branch and record the existing test/migration baseline before changing behavior.
3. Change domain/services first only when business behavior changes; otherwise add the new API, repository, or UI adapter around existing behavior.
4. Add or update tests with the implementation. Database behavior is tested against real PostgreSQL and UI/API integration is checked against the OpenAPI contract.
5. Regenerate migrations, OpenAPI, and the typed frontend client only through their documented commands, then inspect the diff. Generated output never substitutes for review.
6. Run the same root quality command used by CI and attach migration, concurrency, security, accessibility, or performance evidence required by the plan.
7. Open one reviewable pull request that explains affected components, configuration, migration compatibility, deployment order, rollback, and the plan criteria it satisfies.
8. Merge only after the stable required CI result passes. Direct production-branch edits and manual unrecorded database schema changes are prohibited.
9. After verification, update the active plan's status/evidence and the README's current project status. Incomplete criteria move to a later numbered plan explicitly rather than disappearing from scope.

Small vertical changes are preferred over one large web rewrite. A vertical slice may add a PostgreSQL repository method, FastAPI endpoint, OpenAPI client operation, and one dashboard workflow together while the CLI and other workflows continue to function.

### 11.2 Ordered production release

One Git commit SHA is the release identity for migration tooling, Render, and Vercel. Frontend-only or backend-only releases may skip unaffected stages, but a contract or schema change must follow the complete order:

1. Build immutable Python and Next.js artifacts and run all quality, contract, security, migration, concurrency, and applicable browser checks.
2. Create or verify the required pre-migration backup and confirm that the production database reports the expected starting schema version.
3. Acquire the project migration advisory lock and apply backward-compatible **expand** migrations from `supabase/migrations/` using the protected GitHub production environment.
4. Verify migration history, constraints, permissions, and a bounded database smoke query; release the advisory lock. A migration failure stops the release.
5. Trigger Render for the exact commit SHA and wait for build, `/health/live`, `/health/ready`, schema-compatibility, authentication, and representative API smoke checks.
6. Only after the API is healthy, deploy or promote the matching `web/` commit to Vercel and attach the production domain.
7. Run deployed browser journeys for sign-in, catalog, one read/write circulation path, authorization rejection, sign-out, and provider-unavailable presentation.
8. Record commit SHA, migration version, Render/Vercel deployment identifiers, test evidence, timestamps, operator, and outcome in the release record.
9. Observe errors, latency, connection/lock pressure, and quota changes for the defined stabilization window before declaring the release complete.

Production provider auto-deploys must not race this sequence. Render production auto-deploy is disabled and triggered from the protected workflow, or an equivalently ordered `checksPass` arrangement is proven before use. Vercel preview integration may remain automatic, but production promotion waits for API readiness. Render deploy hooks and all provider tokens are secrets; where supported, deployment targets the explicit Git commit rather than an ambiguous branch head.

Render Free does not support pre-deploy commands, so database migration must not be hidden in a Render start command. Startup migration would rerun after every cold start and mixes schema ownership with serving traffic. The dedicated CI migration stage uses PostgreSQL advisory locking and stops before application deployment when unsafe.

### 11.3 Compatibility and rollback rules

- Use expand-migrate-contract changes for any schema/API evolution that cannot be completed safely in one release. Add nullable/new structures first, deploy code that understands old and new forms, migrate/backfill in bounded batches, switch reads/writes, observe, and remove old structures only in a later plan/release.
- The FastAPI readiness check validates that the database schema is within the application's supported minimum/maximum range. It must fail closed after an incompatible migration.
- Frontend contracts remain compatible with the currently deployed API throughout promotion. A required field is not removed or redefined in place.
- Frontend rollback selects the previous Vercel deployment. Backend rollback selects the previous Render deployment only when it supports the current database schema.
- Applied production migrations are not automatically reversed. Prefer a forward corrective migration; destructive restore requires maintenance mode, a verified backup, reconciliation, an explicit data-loss assessment, and operator approval.
- If API deployment fails after an expand migration, leave the compatible expanded schema in place and restore the previous API. If frontend deployment fails, keep the verified API and restore the previous frontend.
- No production release deletes the SQLite source snapshot, old PostgreSQL column/table, or compatibility code until the applicable observation and contract-removal gate passes.

Vercel preview deployments must not automatically connect to the production API or database. Preview-to-production access requires explicit approval and narrowly scoped configuration.

## 12. Phased implementation

The phases execute in dependency order and each is authorized by a smaller numbered development plan. A later phase may be researched while an earlier phase is active, but implementation does not cross an unmet gate. The CLI, SQLite adapter, and legacy snapshot remain available until Phase F explicitly retires or repositions them.

### Phase A: Platform and contract foundation

- Record expected users, concurrency, catalog size, traffic, target region, recovery objectives, and intended Vercel usage classification.
- Establish local PostgreSQL and Supabase migration workflows.
- Define API conventions, OpenAPI ownership, domain names, CORS, cookies, CSRF, and environment boundaries.
- Define transaction lock order, conditional-update conventions, idempotency keys, timeout/retry rules, pool configuration, overload responses, and the provider wake-state error contract.
- Establish warm/cold latency, frontend bundle, connection, CPU/memory, database-size, egress, and load-test baselines.
- Create provider configuration templates without provisioning production resources.

### Phase B: PostgreSQL persistence and data migration

- Implement the PostgreSQL connection, unit of work, repositories, migrations, and maintenance boundary.
- Run shared repository and service tests against PostgreSQL.
- Add realistic concurrent checkout, reservation, return, renewal, settlement, review, pool-exhaustion, and deadlock/serialization tests.
- Build and verify the repeatable SQLite-to-PostgreSQL migration utility.
- Implement logical backup and validated restore procedures.

### Phase C: FastAPI backend

- Add the API composition root and health endpoints.
- Implement session authentication and versioned endpoints by capability.
- Add contract, authorization, validation, idempotency, rate-limit, pool-overload, cold-start, and dependency-failure tests.
- Keep the CLI functional against the selected database during transition.

### Phase D: Next.js dashboard

- Create the TypeScript application and schema-checked API client.
- Implement member workflows before librarian and administrator workflows.
- Implement deduplicated cold-start retries, distinct unavailable/error states, pagination, cancellation, and route-level loading boundaries.
- Add component, accessibility, and browser-level critical-journey tests.
- Configure isolated Vercel preview and production environments.

### Phase E: Three-provider deployment spike

- Deploy Next.js to Vercel, FastAPI to Render, and PostgreSQL to Supabase using non-critical data.
- Measure Vercel-to-Render and Render-to-Supabase latency.
- Measure Render cold start, confirm automatic HTTP wake, and rehearse the manual Supabase resume runbook.
- Measure pool acquisition, query and lock time, API processing, payload transfer, client rendering, Core Web Vitals, and bundle sizes independently.
- Verify credentialed CORS, session cookies, CSRF, TLS, origin rejection, and logout/revocation.
- Verify migrations, backup export, clean-environment restore, readiness, alerts, and quota visibility.

### Phase F: Pilot and cutover

- Complete web-versus-CLI parity, security, accessibility, concurrency, and recovery reviews.
- Import the final validated SQLite snapshot.
- Conduct a limited pilot and fix blocking usability or reliability issues.
- Approve appropriate provider tiers before admitting genuine users.
- Retire or reposition the CLI only after parity, restore, and rollback gates pass.

### 12.1 Planned development-plan sequence

All follow-up files retain the `development-plan-xx.md` naming convention. They are created just before execution so their commands and dependency versions can be verified at that time.

| Plan | Owns | Entry gate | Exit result |
| --- | --- | --- | --- |
| `development-plan-12.md` | Phase A: asymmetric monorepo scaffolding, local Supabase/PostgreSQL workflow, configuration contracts, FastAPI skeleton, OpenAPI/client generation path, CI change graph, and performance/concurrency baselines | Plan 11 approved | One-command documented local stack and CI foundation without production provisioning |
| `development-plan-13.md` | Phase B1a: PostgreSQL schema/migrations, pool, transaction primitive, bounded retries, readiness, infrastructure concurrency tests | Plan 12 gates pass | Real PostgreSQL infrastructure verified without switching business services |
| `development-plan-14.md` | Phase B1b: repository adapters and UoW composition, shared service parity, pagination, query plans, aggregate locking, atomic idempotency, business concurrency tests | Plan 13 infrastructure stable | Existing services pass against PostgreSQL with measured concurrent correctness |
| `development-plan-15.md` | Phase B2: SQLite snapshot importer, reconciliation, logical backup, restore drill, cutover rehearsal | Plan 14 schema/repositories stable | Repeatable migration and recovery evidence from a clean target |
| `development-plan-16.md` | Phase C: FastAPI sessions, CSRF/CORS, capability routers, rate/overload controls, OpenAPI, API tests | Plans 14-15 provide stable persistence/recovery | Versioned API reaches required CLI business parity |
| `development-plan-17.md` | Phase D: Next.js role workflows, accessibility, cold/unavailable states, optimization, browser tests | Stable session/API contract from Plan 16 | Locally complete dashboard meets functional and experience gates |
| `development-plan-18.md` | Phase E: protected CI/CD, non-production deployment, monitoring, backup automation, security and load/performance spike | Local end-to-end gates pass | Measured deployment evidence and tier recommendation |
| `development-plan-19.md` | Phase F: final import, pilot, tier approval, ordered release, stabilization, rollback, CLI disposition, cutover | Plan 18 release gates pass | Controlled production release or explicit no-go decision |

If a planned file becomes too large to implement safely, split it using the next unused sequential plan number and update this table before implementation. Do not reuse a number, overwrite completed-plan history, or silently move acceptance criteria.

### 12.2 Phase readiness and completion

A follow-up plan is ready to start only when:

- its predecessor's blocking exit criteria and evidence are complete;
- unresolved decisions, environment assumptions, and required credentials/tools are listed;
- destructive actions, external provisioning, expected costs, and rollback boundaries are explicit;
- deliverables are small enough to review and test independently; and
- the working tree is inspected so existing user changes are not overwritten.

A phase is complete only when:

- code, migrations, generated contracts, configuration examples, documentation, and tests agree;
- the local clean-clone workflow succeeds using committed instructions;
- its quality, security, concurrency, accessibility, performance, migration, or recovery gates pass as applicable;
- no real secret, production data, build output, local database volume, or provider state has been committed;
- operational evidence and remaining risks are recorded in the owning plan; and
- the next plan can begin without relying on undocumented manual state.

## 13. Feasibility and release gates

- A clean clone on the supported Windows/PowerShell environment can install both dependency sets, recreate the local database from migrations/seeds, and start Next.js plus FastAPI without production credentials.
- Vercel builds from `web/` without backend/database secrets or undeclared access to root Python sources; Render builds only the root Python application and is not redeployed by frontend/documentation-only changes.
- The committed OpenAPI artifact matches FastAPI, the committed generated client matches OpenAPI, and a contract change runs both backend and frontend checks.
- One stable required GitHub CI result is reported for every pull request, including documentation-only changes, without path-filtered checks remaining indefinitely pending.
- Every existing repository contract and application service test passes against PostgreSQL.
- Concurrent business operations preserve loan limits, copy availability, reservation order, one-time state transitions, and financial invariants without lost updates.
- The documented lock order is followed, synthetic deadlocks are recovered only by bounded whole-transaction retry, and an exhausted retry returns a stable non-500 response.
- The SQLite migration produces matching counts, identifiers, constraints, circulation state, balances, and reports.
- A logical backup restores successfully into a clean PostgreSQL target.
- No Supabase database endpoint or secret appears in browser bundles, source maps, logs, or Vercel public variables.
- The Supabase Data API cannot access application tables.
- Authentication works through the deployed Vercel and Render origins without depending on third-party cookies.
- Role, ownership, deactivation, CSRF, origin, brute-force, token-revocation, and log-redaction tests pass.
- A 30-minute mixed read/write test with 20 concurrent simulated users and a separate 50-user burst produce no lost updates, connection leaks, unbounded queues, or unexpected HTTP 5xx responses.
- Pool saturation, authentication pressure, reports, and overload produce bounded `429`/`503` responses without starving health checks or corrupting transactions.
- Cached reads meet a 500 ms p95 target and ordinary writes meet a 1 second p95 target from the intended user region, excluding an explicitly measured cold start.
- The dashboard remains interactive during a Render cold start, safe retries are deduplicated and bounded, and database-unavailable behavior gives the operator a usable manual-resume path.
- Warm and cold performance measurements identify frontend, Vercel-to-Render, FastAPI, pool wait, query/lock, Render-to-Supabase, and rendering time separately.
- Monitoring detects API unavailability, database failure, quota pressure, migration failure, and backup failure.
- A non-production release rehearsal applies migrations, deploys the exact API commit, verifies readiness, deploys the matching frontend, records identifiers, and demonstrates component rollback in the documented order.
- Vercel usage complies with the selected plan's terms.
- The selected provider tiers will not pause, suspend, or exceed quotas under the documented genuine-user workload without an accepted operational response.

## 14. Upgrade triggers

Upgrade Render when:

- cold starts are unacceptable;
- sustained external-database traffic approaches suspension or bandwidth limits;
- more memory, CPU, workers, shell access, or operational support is required; or
- the service needs production availability expectations.

Upgrade Supabase when:

- automatic pausing is unacceptable;
- database size approaches 70% of the 500 MB quota;
- shared compute or connection limits miss performance targets;
- automatic daily backups, point-in-time recovery, or stronger support is required; or
- egress approaches the monthly allowance.

Upgrade Vercel when:

- the application is no longer eligible for Hobby's personal/non-commercial terms;
- collaboration, support, logs, compute, or traffic exceed Hobby capabilities; or
- the dashboard is operated on behalf of an institution or business whose use requires a paid plan.

## 15. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Render cold starts degrade sign-in and first-page experience | Display a bounded reconnect state, measure actual wake time, and upgrade Render when the target is missed. |
| Supabase pauses or reaches its free database quota | Monitor activity and size, keep tested external backups, and upgrade before genuine-use thresholds are crossed. |
| Cross-provider latency makes requests slow | Co-locate regions as closely as possible, use a small connection pool, eliminate query waterfalls, and measure p95 latency. |
| External database traffic consumes Render and Supabase egress | Track both providers' usage and optimize query/result sizes; include egress in the upgrade decision. |
| Browser cookies fail across default provider domains | Use `app` and `api` subdomains under one project domain and test credentialed CORS and cookies on supported browsers. |
| Supabase tables become reachable through its generated API | Disable the Data API or use an unexposed schema and explicit privilege tests. |
| Free Supabase has no managed backups | Run encrypted off-provider logical backups and scheduled restore drills; upgrade when managed recovery is required. |
| SQLite and PostgreSQL behave differently | Test case folding, null semantics, timestamps, generated identifiers, constraints, transactions, and concurrency explicitly. |
| Concurrent check-then-write requests violate loan, reservation, or financial rules | Lock the smallest protecting aggregate, use conditional updates and database constraints, and test competing requests against real PostgreSQL. |
| Transactions deadlock or wait indefinitely | Use one lock order, short transactions, bounded lock/statement timeouts, whole-transaction retry, and lock-wait/deadlock telemetry. |
| Too many FastAPI tasks exhaust database connections or Render memory | Bound the Psycopg pool and waiting queue, limit expensive endpoints, return controlled overload responses, and upgrade from single-instance Free compute when measured thresholds are crossed. |
| A slow report or unbounded list starves circulation traffic | Require pagination, push aggregation to indexed SQL, cap reports, inspect plans, and apply stricter rate limits to expensive operations. |
| Automatic retry duplicates checkout, return, or settlement | Require and persist idempotency keys for sensitive commands and retry only the entire transaction before external side effects. |
| The static dashboard loads but leaves users on an endless spinner | Model warming, unavailable, offline, timeout, and conflict states explicitly; use bounded retry, manual retry, stable skeletons, and accessible status text. |
| Frontend bundles or request waterfalls hide backend improvements | Set regression budgets, analyze bundles, lazy-load heavy routes, parallelize independent reads, and add screen-specific summary endpoints. |
| A monorepo change causes unnecessary Vercel or Render deployments | Set explicit provider roots/build filters and test frontend-only, backend-only, contract, migration, and documentation changes before enabling production automation. |
| Frontend and API generated contracts drift in one repository | Generate deterministically, commit the OpenAPI document and client, prohibit generated-file hand edits, and fail CI on drift or incompatibility. |
| Repository-wide secrets leak into the wrong provider build | Use provider/environment-scoped variables, keep Vercel rooted at `web/`, scan artifacts/logs, and never use a shared catch-all environment file in deployment. |
| Path-filtered mandatory workflows remain pending and block merges | Start one stable CI workflow on every pull request, select component jobs internally, and require only its final summary status. |
| Moving established Python files for layout symmetry introduces needless breakage | Keep the backend at the repository root and reassess a physical move only if an independently justified repository split occurs. |
| Local orchestration hides failures or leaves background processes running | Keep each component independently startable, preserve separate logs, track only child processes created by the wrapper, and make reset/destruction explicit. |
| Frontend production deploys before a required API/schema version | Disable racing production auto-deploys and use the protected migration-to-API-to-frontend workflow for contract/schema releases. |
| CI or startup races database migrations | Give migrations a dedicated locked CI stage; never run them implicitly in each Render process start. |
| Vercel Hobby terms do not cover the intended use | Classify the deployment before release and select an eligible Vercel tier. |
| A provider changes its free allowance | Recheck terms before provisioning and release; keep configuration portable and document provider export procedures. |
| The CLI is removed before the dashboard is complete | Preserve it as an administrative and rollback interface until parity and recovery gates pass. |

## 16. Deliverables

- Architecture decision record for Vercel, Render, and Supabase
- Approved asymmetric monorepo layout and documented repository-split triggers
- PowerShell local-stack preflight/orchestration and clean-clone setup procedure
- Component-aware GitHub CI with one stable required summary result
- Versioned OpenAPI artifact, deterministic frontend client generation, and drift checks
- PostgreSQL schema and versioned Supabase migrations
- PostgreSQL repositories, unit of work, and maintenance adapter
- Concurrency specification covering lock order, conditional transitions, timeouts, idempotency, retry, overload, and observability
- Repeatable SQLite-to-PostgreSQL transfer and reconciliation report
- FastAPI application with versioned OpenAPI contract and browser sessions
- Accessible TypeScript Next.js dashboard
- Cold-start/error-state frontend behavior and warm/cold performance report
- Provider capacity profile with pool configuration, multi-user load results, quotas, and upgrade thresholds
- Render and Vercel deployment definitions with redacted configuration examples
- Isolated local, preview, and production configuration
- Automated quality, migration, deployment, and smoke-test workflow
- Off-provider PostgreSQL backup and tested restore procedure
- Provider quota, availability, and upgrade runbook
- Ordered exact-commit production release, stabilization, and component rollback runbook
- Plans 12-18 execution map with entry gates and exit evidence
- Web-versus-CLI parity and cutover checklist

## 17. Acceptance criteria for this planning milestone

- Vercel, Render, and Supabase have explicit, non-overlapping responsibilities.
- One local/GitHub monorepo is approved, with Python retained at the root, Next.js isolated under `web/`, and explicit conditions for considering a future split.
- Source co-location does not weaken runtime, secret, build, environment, or deployment isolation.
- Local startup, pull-request validation, generated-contract ownership, ordered release, rollback, and follow-up plan execution are defined end to end.
- PostgreSQL replaces SQLite only as the deployed system of record; the existing SQLite database remains a controlled migration source and rollback artifact.
- The frontend has no direct database access and FastAPI remains the sole business and authorization boundary.
- Authentication, cross-origin behavior, migration ownership, backups, and provider limitations have testable controls.
- Read/write concurrency, deadlock recovery, connection limits, database optimization, and multi-user overload behavior have explicit implementation and test rules.
- Existing Python domain/services remain framework-independent, while FastAPI and PostgreSQL are defined as replaceable delivery and persistence adapters.
- The dashboard has a bounded performance and recovery strategy for cold, unavailable, slow, and overloaded backend paths.
- Free tiers are limited to eligible development, demonstration, or approved pilot usage.
- Genuine user deployment is blocked until terms, reliability, recovery, performance, and tier gates pass.
- Implementation can proceed as smaller development plans without reopening the provider selection.

## 18. Research references

- [Render: Deploy for Free](https://render.com/docs/free)
- [Render: Setting Your Python Version](https://render.com/docs/python-version)
- [Render: Deployment Steps and Pre-deploy Commands](https://render.com/docs/deploys)
- [Render: Monorepo Support](https://render.com/docs/monorepo-support)
- [Render: Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Render: Deploy Hooks](https://render.com/docs/deploy-hooks)
- [Render: Outbound Bandwidth](https://render.com/docs/outbound-bandwidth)
- [Supabase: Pricing](https://supabase.com/pricing)
- [Supabase: Compute and Disk](https://supabase.com/docs/guides/platform/compute-and-disk)
- [Supabase: Project Pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Supabase: Database Backups](https://supabase.com/docs/guides/platform/backups)
- [Supabase: PostgreSQL Connections and Supavisor](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase: Connection Management](https://supabase.com/docs/guides/database/connection-management)
- [Supabase: Query Optimization](https://supabase.com/docs/guides/database/query-optimization)
- [Supabase: Index Advisor](https://supabase.com/docs/guides/database/extensions/index_advisor)
- [Supabase: Database Migrations](https://supabase.com/docs/guides/deployment/database-migrations)
- [Supabase: Local Development Workflow](https://supabase.com/docs/guides/local-development/cli-workflows)
- [Supabase: Managing Environments](https://supabase.com/docs/guides/deployment/managing-environments)
- [Supabase: Securing the Data API](https://supabase.com/docs/guides/api/securing-your-api)
- [PostgreSQL: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL: Explicit Locking and Deadlocks](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Psycopg 3: Installation and Python 3.14 Support](https://www.psycopg.org/psycopg3/docs/basic/install.html)
- [Psycopg 3: Connection Pools](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [FastAPI: Concurrency and `async`/`await`](https://fastapi.tiangolo.com/async/)
- [Next.js: Production Checklist](https://nextjs.org/docs/app/guides/production-checklist)
- [Vercel: Hobby Plan](https://vercel.com/docs/plans/hobby)
- [Vercel: Custom Domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [Vercel: Monorepo Support](https://vercel.com/docs/monorepos)
- [Vercel: Git Deployments](https://vercel.com/docs/git)
- [GitHub Actions: Workflow Syntax and Path Filters](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

## 19. Next action

Phase A is complete under `development-plan-12.md`: the asymmetric monorepo, local Supabase/PostgreSQL workflow, minimal FastAPI adapter, deterministic OpenAPI/client boundary, Tailwind/React Compiler Next.js foundation, PowerShell workflows, and component-aware CI are implemented and locally verified without production provisioning.

Phase B1 is complete under Plans 13 and 14. The repository established schema version 2,
bounded pool and transaction primitives, full PostgreSQL repository and Unit of Work
composition, canonical aggregate locking, conditional transitions, keyset pagination,
atomic idempotency claims, and real infrastructure/business concurrency evidence. The
existing CLI continues to use SQLite as a controlled transitional interface.

Phase B2 is complete under Plan 15. A read-only SQLite snapshot source, fresh-target-only
atomic importer, preserved identifier mapping, sequence repair, canonical row digests,
circulation/financial reconciliation, credential-safe logical backup boundary, and native
custom-archive restore drill are implemented and verified with synthetic data. Genuine
SQLite data remains untouched and final import authority remains in Plan 19.

Phase C is complete under Plan 16. PostgreSQL schema version 3 now adds digest-only,
revocable browser sessions; the FastAPI adapter provides exact credentialed CORS,
origin/CSRF enforcement, bounded rate/payload behavior, stable infrastructure errors,
atomic idempotent commands, and typed versioned routes over every web-facing business
service. The deterministic OpenAPI and generated TypeScript contracts are current. The
CLI remains available against SQLite, and PostgreSQL backup/restore remains an offline
operator boundary rather than an HTTP command.

Phase D is complete under Plan 17. The statically rendered public shell now hydrates into
opaque-cookie session recovery and a responsive role-aware dashboard over the committed
FastAPI contract. Members, librarians, and administrators receive their appropriate
catalog, circulation, finance, engagement, insight, inventory, and account workflows.
The credentialed client supplies CSRF and stable command idempotency, bounded safe-read
wake retries, cancellation, read deduplication, and distinct Render-warming and
Supabase-unavailable states. Accessibility contracts, critical browser-like journeys,
frontend quality checks, the production build, and unchanged backend regression tests
pass without introducing direct Supabase access or keep-awake traffic.

Phase E is in progress under Plan 18. The repository now contains redacted Render and
Vercel descriptors, a machine-checked environment/secret boundary, manually protected
exact-commit staging automation, credential-safe smoke/timing/load probes, observable API
timing and security headers, and deployment, pause, quota, backup/restore, incident, and
rollback runbooks. No provider resource, domain, secret, monitoring rule, backup target,
or genuine data has been created or changed.

Plan 18 cannot be completed from local configuration alone. Its remaining gate is an
owner-authorized isolated staging deployment with synthetic data and recorded warm/cold,
20-user mixed, 50-user burst, browser-security, migration, encrypted backup/clean-restore,
alert, quota, and component-rollback evidence. Only a passing report and tier decision
can authorize creation of `development-plan-19.md`; genuine-data migration and production
cutover remain blocked.
