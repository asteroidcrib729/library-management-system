# Development Plan 06: Reservations and Loan Circulation

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-06.md`
- **Depends on:** `development-plan-01.md` through `development-plan-05.md`
- **Milestone:** Deliver transactional reservation, checkout, renewal, and return workflows.

## 1. Objectives

- Maintain a first-in, first-out reservation queue for each book.
- Let members create, inspect, and cancel their reservations.
- Let librarians and administrators check copies out to active accounts and process returns.
- Track loan dates, due dates, return dates, and renewal counts.
- Enforce loan limits and renewal policy in application services.
- Keep book-copy, loan, and reservation state synchronized in one transaction.
- Expose circulation workflows through the interactive CLI.

## 2. Initial circulation policy

- Standard loan period: 14 days
- Maximum active loans per account: 5
- Maximum renewals per loan: 2
- Reservation order: oldest active reservation first
- A user cannot reserve a book they already have on active loan.
- Duplicate active reservations for the same user and book are rejected.
- If a reservation queue exists, only its first user may receive an available copy.
- Checkout fulfills that user's active reservation atomically.
- Renewal is unavailable after the due time or while another active reservation exists.
- Catalog management cannot override copies currently on loan.
- Librarians and administrators perform checkout and return operations.

Policy values will be represented by a configurable object so later plans can load them from application configuration.

## 3. Schema migration

Schema version 2 adds a non-negative `renewal_count` column to `loans`. Existing loan records receive a value of zero. The migration must apply once to both new and existing version 1 databases.

## 4. CLI commands

- `reserve <book-id>`: join a reservation queue
- `reservations`: show the signed-in user's reservations and active queue positions
- `cancel-reservation <id>`: cancel an owned reservation; staff may cancel another
- `checkout <username> <barcode>`: check out an available copy (staff only)
- `return-copy <barcode>`: return an active loan (staff only)
- `renew <loan-id>`: renew an eligible loan
- `loans [username]`: show personal loans; staff may inspect another account

## 5. Deliverables

- Schema migration version 2
- Reservation and loan repository contracts and SQLite implementations
- Unit of Work exposure for circulation repositories
- Configurable circulation policy and injectable clock
- Circulation service and presentation-safe view types
- CLI circulation commands and formatted tables
- Domain, migration, repository, policy, authorization, and end-to-end tests
- Updated README and completion record

## 6. Acceptance criteria

- Schema version 1 databases migrate to version 2 without data loss.
- Reservation positions follow creation order and close gaps after cancellation.
- Duplicate and already-borrowed reservations are rejected.
- Checkout requires staff authorization and an available copy.
- Reservation queue priority cannot be bypassed.
- Checkout updates loan, copy, and reservation records atomically.
- Return records its timestamp and makes the copy available atomically.
- Renewals extend the existing due date and increment their count.
- Overdue, maximum-count, and queued-demand renewals are rejected.
- Members cannot inspect other users' loans.
- Pytest, Pyrefly, Ruff lint, Ruff formatting, and live CLI smoke checks pass.

## 7. Completion record

Completed on 2026-09-04 with the following results:

- Existing schema version 1 databases migrated to version 2 without losing account, catalog, copy, reservation, or loan data.
- Reservation and loan repository contracts and SQLite implementations passed persistence tests.
- Reservation queues retained first-in, first-out ordering and recalculated active positions after cancellation.
- Duplicate reservations, reservations for books already borrowed, and queue-priority bypass attempts were rejected.
- Checkout required staff authorization, enforced copy availability and account loan limits, created the loan, marked the copy `on_loan`, and fulfilled the matching reservation atomically.
- Returns recorded their timestamp and restored the copy to `available` atomically.
- Eligible renewals extended the current due date and incremented `renewal_count`; overdue, maximum-count, and queued-demand renewals were rejected.
- Members could inspect only their own loans and reservations, while staff inspection workflows passed.
- Live CLI reservation, checkout, renewal, return, loan history, reservation status, and copy availability workflows passed.
- Pytest: 68 tests passed.
- Pyrefly: no errors.
- Ruff lint and formatting checks passed.
- Package version smoke test passed.

The next plan will cover overdue fine assessment, payments, waivers, and financial history.
