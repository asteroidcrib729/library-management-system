# Development Plan 14: PostgreSQL Repository and Business Concurrency Parity

## Document information

- **Status:** Complete
- **Started:** 2026-09-05
- **Depends on:** Plan 13
- **Scope:** Phase B1b of Plan 11; local synthetic data only.

## 1. Objective

Connect every existing application service to PostgreSQL through repository adapters and a business Unit of Work while preserving SQLite behavior. Establish the locking, conditional-update, pagination, idempotency, query-plan, and concurrent-operation evidence required before any legacy-data import or HTTP business endpoint work.

## 2. Deliverables

1. PostgreSQL adapters for users, books, copies, reservations, loans, fines, immutable settlements, acquisition requests, feedback, and reporting.
2. `PostgresUnitOfWork` implementing the existing repository contract over one Plan 13 transaction and checked-out connection.
3. Stable lock order: users, books, copies, reservations, loans, fines, acquisition requests, feedback. Services lock only the aggregates involved in a state-changing decision and then re-read state.
4. Compare-and-set state transitions remain authoritative. Unique/check/foreign-key database failures are translated into the existing persistence errors without leaking SQL details.
5. Keyset pagination for catalog-facing PostgreSQL paths with a server-side limit. Existing unbounded service methods remain temporarily for CLI compatibility and cannot become web API endpoints in Plan 16.
6. Atomic idempotency claim, in-progress, replay, request-mismatch, stale-takeover, and completion behavior. HTTP integration remains Plan 16.
7. Shared service behavior tests against PostgreSQL, plus simultaneous reservation, checkout, return, renewal, settlement, review, lock-order, idempotency, and index-plan tests.
8. CI/local workflows and documentation updated so PostgreSQL repository tests run for backend changes.

## 3. Safety and correctness rules

- Tests create and remove only uniquely named `lms_test_*` databases on loopback PostgreSQL.
- No existing SQLite or legacy files are read into PostgreSQL.
- Repository constructors perform no I/O; entering a Unit of Work checks out one connection.
- A transaction commits only after an explicit service/UoW commit. Exceptions and uncommitted exits roll back.
- Locks are acquired in ascending identifier order and in the table order above. A caller cannot request a later table and subsequently request an earlier one in the same lock operation.
- Idempotency replay requires the same actor, operation, key, and SHA-256 request digest. Only the current owner token may complete a processing record.
- Settlement history is append-only through repository APIs; duplicate settlement attempts resolve to one success and one domain conflict.

## 4. Verification and exit gate

Run the complete SQLite service suite unchanged, the full PostgreSQL repository/service suite, Ruff, Pyrefly, OpenAPI/client drift, frontend checks, production build, Supabase migration replay, and workflow lint. Record concurrency outcomes and query-plan evidence. Plan 15 may begin only after repository parity is green and no disposable database remains.

## 5. Execution record

Completed on 2026-09-05.

- Added PostgreSQL adapters for every existing repository protocol and composed them in
  `PostgresUnitOfWork` over one checked-out Plan 13 transaction.
- Extended the shared Unit of Work contract with a bootstrap advisory lock and one
  canonical, ascending row-lock operation. SQLite supplies compatibility no-ops while
  the transitional CLI remains single-process; PostgreSQL supplies real `FOR UPDATE`
  locks in users-to-feedback order.
- Updated state-changing account, catalog, circulation, financial, and engagement
  services to acquire their protecting aggregates and re-read authoritative state.
  Conditional updates and database uniqueness remain the final conflict guard.
- Added unbounded PostgreSQL catalog search only for temporary CLI parity and separate
  server-bounded keyset pages for web use. The cursor uses PostgreSQL's returned
  `lower(title)` value, preventing database/Python Unicode-normalization drift.
- Added schema migration 2 and an atomic idempotency repository covering claim,
  in-progress, same-request replay, request-digest conflict, current-owner completion,
  expired-claim takeover, and simultaneous claims. The migration was applied locally
  with `migration up`; no reset or legacy-data import occurred.
- Added real-database round-trip coverage for every repository group, aggregate reports,
  pagination uniqueness, escaped search input, and an `EXPLAIN` assertion for
  `books_page_idx`. Concurrent tests demonstrate exactly one winner for reservation,
  checkout, return, settlement, and request review, serialized renewal counts `{1, 2}`,
  and one `claimed` plus one `in_progress` idempotency result.
- Verification passed: 133 non-PostgreSQL Python tests and 22 disposable-PostgreSQL tests
  (155 total), Ruff lint/format, Pyrefly with zero diagnostics, deterministic OpenAPI and
  generated-client drift checks, ESLint, Next.js type generation/TypeScript, two Vitest
  tests, and the Next.js production build. The CI workflow was unchanged and continues
  to select the PostgreSQL job for either backend or migration changes. All disposable
  `lms_test_*` databases were removed; the final count was zero.

Plan 15 may now begin. It must treat SQLite as an immutable migration source, import
only into a fresh PostgreSQL target, reconcile every entity and financial total, and
prove logical backup/restore before any cutover decision.
