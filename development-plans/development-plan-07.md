# Development Plan 07: Fines and Financial History

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-07.md`
- **Depends on:** `development-plan-01.md` through `development-plan-06.md`
- **Milestone:** Deliver auditable overdue charges, manual fines, payments, and waivers.

## 1. Objectives

- Automatically assess an overdue fine when a late copy is returned.
- Preserve the legacy rate of PKR 10 per started overdue day as configurable policy.
- Allow circulation staff to assess explicit loss, damage, or administrative charges.
- Let members inspect their own fine history and outstanding total.
- Let staff record full payments and let administrators waive fines.
- Retain immutable settlement records instead of deleting or silently clearing fines.
- Keep return, copy availability, and automatic fine assessment in one transaction.

## 2. Financial policy and authorization

- Currency: PKR
- Overdue rate: PKR 10.00 per started 24-hour period after the due time
- A return at or before its due time creates no fine.
- Each fine is a positive, two-decimal-place amount stored as integer minor units.
- This milestone supports full settlement only; partial payments are deferred.
- Members may inspect only their own fines.
- Librarians and administrators may inspect accounts, assess manual fines, and record payments.
- Only administrators may waive an outstanding fine.
- Payment and waiver records capture the acting account, timestamp, amount, and note.

## 3. Schema migration

Schema version 3 adds a `fine_settlements` table. Each fine can have at most one settlement record, and every settlement references both its fine and the staff account that recorded it. Existing fines remain unchanged and outstanding.

## 4. CLI commands

- `fines [username]`: show fine history and an outstanding total
- `fine <id>`: show one fine and its settlement details
- `assess-fine <username> <amount>`: create a manual fine after prompting for its reason (staff only)
- `pay-fine <id>`: record full payment after prompting for an optional note (staff only)
- `waive-fine <id>`: waive a fine after prompting for a required reason (administrator only)

Returning an overdue copy reports the automatically assessed amount and fine identifier.

## 5. Deliverables

- Schema migration version 3
- Fine-settlement domain model and validation
- Fine and settlement repository contracts and SQLite implementations
- Configurable fine policy and financial application service
- Transactional automatic assessment during overdue returns
- Financial CLI commands and formatted history/detail views
- Domain, migration, repository, policy, authorization, and end-to-end tests
- Updated README and completion record

## 6. Acceptance criteria

- Schema version 2 databases migrate to version 3 without data loss.
- Returns at or before the due time do not create a fine.
- Any started overdue day is charged at the configured daily rate.
- Overdue return, loan closure, copy availability, and fine creation are atomic.
- Manual fines require an active borrower, positive currency amount, reason, and staff authorization.
- Members cannot inspect another account's financial records.
- Payments settle only outstanding fines and create an immutable payment record.
- Waivers require administrator authorization and a non-empty reason.
- A settled fine cannot be paid or waived again.
- Money is persisted as integer minor units and displayed with two decimal places.
- Pytest, Pyrefly, Ruff lint, Ruff formatting, package, and live CLI smoke checks pass.

## 7. Completion record

Completed on 2026-09-04 with the following results:

- Existing schema version 1 and version 2 databases migrated to version 3 without losing loan or fine data.
- Fine amounts and settlements round-tripped through SQLite as exact integer minor units.
- The configurable fine policy retained the legacy PKR 10.00 rate and charged every started overdue day.
- On-time returns created no charge, while overdue loan closure, copy availability, and fine assessment occurred in one transaction.
- Staff-only manual assessment required an active account, positive two-decimal-place amount, and non-empty reason.
- Members could inspect their own fine history and outstanding total but could not inspect another account.
- Librarians and administrators could record full payments with immutable actor, amount, time, and note history.
- Only administrators could waive an outstanding fine, and every waiver required a reason.
- Paid and waived fines could not be settled a second time.
- Live CLI assessment, payment, waiver, detail, history, authorization, overdue-return, and total-balance workflows passed.
- Pytest: 78 tests passed.
- Pyrefly: no errors.
- Ruff lint and formatting checks passed.
- Package version smoke test passed.

The next plan will be selected after reviewing the remaining legacy workflows and revised product priorities; book requests and feedback are the leading candidates.
