# Development Plan 09: Recommendations and Operational Reporting

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-09.md`
- **Depends on:** `development-plan-01.md` through `development-plan-08.md`
- **Milestone:** Deliver explainable catalog recommendations and a staff operations dashboard.

## 1. Objectives

- Replace the legacy random-title recommendation with deterministic, explainable suggestions.
- Personalize recommendations from a member's borrowing history when available.
- Fall back to circulation popularity and availability for new members.
- Exclude previously borrowed books, books currently held by the member, and unavailable inventory.
- Give librarians and administrators a concise operational snapshot.
- Report inventory, circulation, financial, request, and feedback workload from current data.
- Keep reporting read-only and avoid duplicating operational state.

## 2. Recommendation policy

- Candidate books must have at least one available physical copy.
- Books in the member's loan history are excluded to favor discovery.
- Category affinity has the highest personalization weight, followed by author affinity.
- Historical checkout count provides a popularity signal.
- Available-copy count breaks otherwise similar results in favor of usable inventory.
- Results use stable title and identifier ordering as the final tie-breaker.
- Each recommendation includes a short reason describing its strongest signal.
- The default result limit is five; CLI callers may request between one and twenty.

## 3. Operational dashboard

The staff-only dashboard reports:

- active accounts and catalog title count
- total and available physical copies
- active and overdue loans
- active reservations
- outstanding fine count and amount in PKR
- pending acquisition requests
- new feedback awaiting review
- the five most-circulated books

All values are calculated at read time through a dedicated reporting repository. This milestone requires no schema migration.

## 4. CLI commands

- `recommend [limit]`: show personalized, available catalog recommendations
- `popular [limit]`: show the most-circulated available books
- `dashboard`: show the operational snapshot (staff only)

## 5. Deliverables

- Reporting repository contract and SQLite aggregate-query implementation
- Recommendation scoring policy and explainable result views
- Staff-authorized operational report service
- CLI recommendation, popularity, and dashboard displays
- Tests for personalization, cold starts, exclusions, stable ordering, metrics, and authorization
- Updated README and completion record

## 6. Acceptance criteria

- Recommendations are deterministic for unchanged data.
- Personalized results prefer matching categories and authors.
- Cold-start results use popularity, availability, and stable ordering.
- Books without available copies and previously borrowed books are excluded.
- Invalid limits are rejected clearly.
- Popularity rankings use historical checkout counts and stable tie-breakers.
- Dashboard access requires an active librarian or administrator.
- Dashboard metrics reflect persisted state, including overdue loans and exact fine minor units.
- Reporting operations do not mutate the database.
- Pytest, Pyrefly, Ruff lint, Ruff formatting, package, and live CLI smoke checks pass.

## 7. Completion record

Completed on 2026-09-05 with the following results:

- Replaced the legacy random-title feature with deterministic and explainable recommendations.
- Personalized ranking used category affinity, author affinity, historical circulation, and currently available copy counts.
- Previously borrowed titles and books without available copies were excluded.
- Cold-start users received stable availability- and popularity-based catalog discovery results.
- Result limits were enforced between one and twenty for both recommendation and popularity commands.
- Popular-book ranking used historical checkout totals, availability, title, and identifier tie-breakers.
- Added a dedicated read-only SQLite reporting repository without changing the schema.
- The staff dashboard reported active accounts, titles, copy availability, active and overdue loans, reservations, exact outstanding fines, pending requests, new feedback, and popular books.
- Member dashboard access was rejected while librarian and administrator access passed.
- Live CLI dashboard, popularity, personalized recommendation, history exclusion, and authorization workflows passed.
- Pytest: 95 tests passed.
- Pyrefly: no errors.
- Ruff lint and formatting checks passed.
- Package version smoke test passed.

The next milestone will focus on operational hardening, backup, restoration, and database health checks.
