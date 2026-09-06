# Development Plan 16: FastAPI Browser API

## Document information

- **Status:** Complete
- **Started:** 2026-09-06
- **Depends on:** Plans 14-15
- **Scope:** Phase C of Plan 11; local and disposable PostgreSQL data only.

## 1. Objective

Turn the framework-neutral Python application into a production-shaped, versioned
FastAPI backend without moving business rules into HTTP handlers or granting the
frontend direct database access. The API must authenticate browsers with revocable
opaque server-side sessions, defend cookie-authenticated mutations, map expected
application and infrastructure failures into a stable contract, and retain the CLI's
service behavior while PostgreSQL is used by the web adapter.

## 2. Deliverables

1. PostgreSQL session persistence with hashed opaque tokens, absolute and idle expiry,
   revocation, account-state validation, and no recoverable bearer credential at rest.
2. Login, current-session, CSRF rotation, and logout endpoints using a host-only,
   `HttpOnly`, appropriately `Secure`, `SameSite=Lax` cookie.
3. Exact credentialed CORS plus origin and CSRF checks for unsafe browser requests.
4. Capability routers under `/api/v1` for accounts, catalog, circulation, finance,
   engagement, and insights, delegating to the existing application services.
5. Typed and bounded request/response models, stable error envelopes, request IDs,
   payload limits, authentication/mutation rate controls, and controlled database
   overload/unavailable responses.
6. Required idempotency keys for sensitive commands, with claim, service mutation, and
   stored response committed in the same PostgreSQL transaction. Confirmed deadlock or
   serialization aborts retry the complete command only.
7. Deterministic OpenAPI and generated TypeScript contract updates plus unit, contract,
   security, PostgreSQL integration, authorization, and replay tests.

## 3. Execution rules

- FastAPI routers may call services and API-specific session/idempotency adapters only;
  they may not call CLI screens, SQLite repositories, or embed domain authorization.
- Authentication failures do not reveal whether a username exists. Session cookies and
  CSRF tokens are never logged or persisted in clear text.
- Public credential endpoints still require an allowed browser origin. Every
  cookie-authenticated unsafe request requires both an allowed origin and matching CSRF
  token; CORS is not treated as CSRF protection.
- A request owns at most one checked-out connection at a time. Idempotent commands lend
  their outer transaction to the service so the claim, domain changes, and response are
  atomic. Retried attempts rerun the whole service command.
- Idempotency keys are scoped by actor and operation. A different request body with the
  same key is a conflict; a completed request replays its status and JSON body.
- List responses are bounded at the HTTP boundary. Passwords, hashes, internal errors,
  database URLs, and provider details do not enter OpenAPI responses.
- No hosted Supabase, Render, Vercel, genuine SQLite database, production credential,
  or production deployment is touched by this plan.

## 4. Verification and exit gate

The plan is complete only when session creation/expiry/revocation, inactive-user
rejection, origin and CSRF rejection, CORS preflight, role/ownership enforcement,
validation bounds, login throttling, database busy/unavailable mapping, idempotency
replay/conflict/concurrency, and every service capability have automated coverage.
Migration replay, the full Python/PostgreSQL suites, Ruff, formatting, Pyrefly, OpenAPI
and generated-client drift, frontend checks/build, and workflow validation must pass.
The CLI must remain operational and no disposable database or secret artifact may remain.

## 5. Execution record

Completed on 2026-09-06.

- Added PostgreSQL schema version 3 with `browser_sessions`, token/CSRF digest checks,
  absolute and idle expiry, active-session indexes, RLS, least-privilege revocation, and
  a database trigger that revokes every session when an account becomes inactive. The
  local development database was migrated from versions 1-2 to 1-3 without reset.
- Added an opaque session adapter. It generates independent 256-bit session and CSRF
  values, persists only SHA-256 digests, validates active accounts and both expiry
  boundaries, extends bounded idle activity, and revokes logout tokens. The session is
  a host-only `HttpOnly`, `SameSite=Lax` cookie; hosted environments require `Secure`.
- Integrated the existing Argon2id authentication service and reused one process-scoped
  password/authentication composition instead of generating the dummy timing hash per
  request. Login, registration, and bootstrap hashing receive bounded process-local
  admission control; authenticated mutations have a separate actor-scoped limit.
- Added exact credentialed CORS, mandatory allowed origins for unsafe browser requests,
  double-bound CSRF cookie/header verification against the stored digest, request IDs,
  `no-store` responses, declared-body limits, safe configuration bounds, and stable
  validation/authentication/conflict/busy/unavailable error envelopes with retry hints.
- Added typed capability routers under `/api/v1` for session/account, catalog/inventory,
  reservation/loan, fine/settlement, request/feedback, recommendation/popularity, and
  operational-report workflows. Every collection has an explicit maximum page/window;
  authorization and ownership remain inside the existing services. PostgreSQL logical
  backup/restore deliberately remains an offline operator capability rather than a
  remotely invokable browser endpoint; health/readiness remain available over HTTP.
- Added transaction lending to `PostgresUnitOfWork`. Sensitive HTTP commands require an
  actor/operation-scoped `Idempotency-Key`; claim, service changes, serialized response,
  and 24-hour replay retention share one commit. Reused keys with changed bodies fail,
  live claims return a retryable conflict, and confirmed deadlock/serialization aborts
  retry the whole command up to the established bound.
- Updated the snapshot importer and recovery validator for schema version 3 and the new
  twelfth RLS-protected table. Regenerated `contracts/openapi.json` and the committed
  TypeScript schema consumed from `web/`.
- Added browser/PostgreSQL tests for opaque-at-rest credentials, invalid credentials,
  session resolution, CSRF, origin rejection, login throttling, idle expiry, logout,
  automatic deactivation revocation, bounded reads, idempotent create/replay/body
  conflict, and safe dependency/overload/payload errors. Existing shared PostgreSQL
  service and concurrency suites continue to cover role, ownership, and every business
  capability reached by the routers.
- Final evidence: 142 non-PostgreSQL tests passed; 28 PostgreSQL tests passed with only
  the separately gated native recovery drill skipped; that schema-v3 Docker
  `pg_dump`/`pg_restore` drill then passed independently. Ruff lint/format, Pyrefly with
  zero errors, deterministic OpenAPI/client checks, frontend ESLint/TypeScript/Vitest,
  and the Next.js production build passed. The unchanged workflow had already passed
  actionlint in Plan 15. The only warning is the known third-party Starlette/AnyIO test
  alias deprecation. No `lms_test_*` database, browser session, temporary archive, or
  temporary recovery directory remained.

## 6. Exit decision

Plan 16 is complete. Plan 17 may now implement the role-aware Next.js dashboard against
the committed session and capability contract. Hosted provisioning, deployment, genuine
data migration, and remotely triggered database recovery remain outside this gate.
