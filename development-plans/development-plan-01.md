# Development Plan 01: Python Revamp Foundation

## Document information

- **Status:** Proposed
- **Project:** Library Management System
- **Plan:** `development-plan-01.md`
- **Legacy reference:** `../legacy/LMS_PRJ_ALG.cpp`
- **Primary objective:** Rebuild the legacy C++ console application as a maintainable, modular, object-oriented Python application.

## Planning document convention

All development plans must be stored in the `development-plans/` directory and named using this pattern:

```text
development-plan-xx.md
```

`xx` is a zero-padded, sequential number beginning with `01`. Examples include `development-plan-02.md`, `development-plan-03.md`, and `development-plan-04.md`. Existing plan numbers must not be reused or renumbered.

## 1. Background

The legacy application is a single-file C++ console program. It combines user interaction, business rules, in-memory state, and text-file persistence in the same functions. Its implemented features provide a useful requirements baseline, but the new application should be a redesign rather than a line-by-line translation.

The legacy source will remain unchanged in `legacy/` for reference. New Python code must not depend on or write data into that directory.

## 2. Revamp goals

The revamp will:

- Separate domain models, business services, persistence, and user-interface code.
- Apply object-oriented design where objects express meaningful domain behavior.
- Replace global mutable state with explicit dependencies and method-local state.
- Replace ad hoc text-file persistence with a transactional SQLite database.
- Store passwords using a secure password-hashing algorithm.
- Model reservations, loans, book copies, and fines as separate records.
- Preserve the useful behavior of the legacy project while correcting its data and authorization flaws.
- Provide automated tests for business rules and persistence behavior.
- Keep the first user interface as a CLI while allowing a web or desktop interface to be added later.

## 3. Initial scope

### Included

- User and administrator accounts
- Authentication and role-based authorization
- User-account management
- Book catalog management
- Search and catalog browsing
- Physical book-copy availability
- Reservations and cancellations
- Loans, due dates, and returns
- Fine assessment, settlement, and waiver
- Book acquisition requests
- User feedback
- Basic book recommendations
- Import of usable legacy text data, if those files become available
- A command-line interface
- Unit and integration tests

### Deferred

- Web and mobile interfaces
- Email, SMS, or push notifications
- Online payment processing
- Multi-branch inventory
- Advanced recommendation algorithms
- Third-party identity providers
- Cloud deployment and multi-user database servers

## 4. Legacy behavior requiring correction

The following behaviors must not be copied directly into the Python implementation:

- A single `Reserved` Boolean cannot represent the reserving user, reservation time, queue order, or status.
- Book titles cannot be treated as unique identifiers.
- Reservation and borrowing are distinct workflows and require separate records.
- Passwords must not be stored in plaintext.
- Public administrator registration must not be enabled by default.
- A user must not clear their own fine without a recorded settlement or an authorized waiver.
- Student-fee records must not disappear when a menu closes.
- Duplicate book requests must be compared as complete records, not unrelated strings.
- Recommendations must handle an empty catalog safely.
- Account deletion must address related loans, reservations, and fines without leaving orphaned data.
- File parsing, prompts, and business decisions must not be combined in the same methods.

## 5. Proposed architecture

The application will use a layered structure:

```text
src/library_management/
├── domain/          # Entities, value objects, enums, and domain exceptions
├── repositories/    # Persistence contracts and SQLite implementations
├── services/        # Application use cases and business rules
├── cli/             # Menus, prompts, formatting, and input validation
├── config.py        # Application configuration
├── database.py      # Connection and schema lifecycle
└── main.py          # Composition root and CLI entry point
```

Dependency direction must remain inward:

```text
CLI -> Services -> Repository interfaces -> SQLite implementations
             \-> Domain models
```

Domain models and services must not call `input()`, print output, open files, or create database connections. The application entry point will construct dependencies and inject them into the CLI and services.

## 6. Proposed domain model

### User

- Generated identifier
- Display name
- Unique normalized username
- Password hash
- Role: member, librarian, or administrator
- Active status
- Created timestamp

### Book

- Generated identifier
- ISBN, when available
- Title
- Author
- Publication year
- Optional category and description

### BookCopy

- Generated identifier or barcode
- Parent book identifier
- Status: available, on loan, lost, damaged, or withdrawn

### Reservation

- User identifier
- Book identifier
- Creation timestamp
- Queue position derived from creation order
- Status: active, fulfilled, cancelled, or expired

### Loan

- User and book-copy identifiers
- Checkout and due timestamps
- Return timestamp
- Status derived from the record and dates

### Fine

- User identifier
- Optional related loan identifier
- Reason
- Monetary amount represented with `Decimal`, never `float`
- Status: outstanding, paid, or waived
- Assessment and settlement timestamps

### BookRequest and Feedback

- Requesting/submitting user identifier
- Submitted content
- Creation timestamp
- Processing status where applicable

### Student fees

The legacy student fee feature appears separate from library circulation. Before implementing it, decide whether it represents institutional tuition balances or library charges. Institutional fee management should become a separate module or project; library charges should be represented through the fine/payment model.

## 7. Technology baseline

The initial implementation should use:

- A currently supported Python 3 release, with the minimum version recorded in `pyproject.toml`
- SQLite for local persistence
- `dataclasses`, enums, type hints, and repository protocols or abstract base classes
- A dedicated password-hashing library using Argon2id or an equivalently established password hash
- `pytest` for automated testing
- Ruff for formatting and linting
- Static type checking as part of the development workflow

Dependencies should be kept small and introduced only when they provide a clear maintenance or security benefit.

## 8. Delivery phases

### Phase 1: Project foundation

- Create the Python package and `pyproject.toml`.
- Add application configuration and a CLI entry point.
- Configure formatting, linting, type checking, and tests.
- Define domain exceptions and repository contracts.
- Document local setup and common commands.

**Exit criteria:** The package installs locally, the CLI starts, and automated quality checks pass.

### Phase 2: Database and domain models

- Design the SQLite schema with foreign keys, uniqueness rules, and indexes.
- Implement the initial domain objects.
- Implement connection and transaction management.
- Implement repository classes and integration tests.

**Exit criteria:** Core records can be created and retrieved reliably, and failed operations roll back cleanly.

### Phase 3: Accounts and authorization

- Implement member creation and secure password storage.
- Implement authentication without exposing whether a username or password was incorrect.
- Bootstrap the first administrator through a controlled setup command.
- Enforce roles in services, not only in CLI menus.
- Define safe account deactivation rules.

**Exit criteria:** Authentication and privileged actions are covered by positive and negative tests.

### Phase 4: Catalog and inventory

- Add, update, withdraw, search, and list books.
- Manage multiple physical copies of the same title.
- Normalize searches while preserving original display values.
- Reject invalid publication years and duplicate identifiers.

**Exit criteria:** Catalog workflows work through services and the CLI, including empty and duplicate cases.

### Phase 5: Circulation

- Implement reservations, cancellation, and queue ordering.
- Implement checkout, renewal, return, and overdue detection.
- Prevent checkout of unavailable copies.
- Define how an available copy fulfills the oldest active reservation.

**Exit criteria:** Reservation and loan state transitions are transactional and thoroughly tested.

### Phase 6: Fines and supplementary features

- Calculate fines through a configurable policy.
- Record payments and authorized waivers rather than deleting fine history.
- Add book requests and feedback.
- Add a safe basic recommendation strategy with deterministic test support.
- Resolve the student-fee scope decision.

**Exit criteria:** Financial history is auditable, and supplementary features handle empty and duplicate data safely.

### Phase 7: Legacy import

- Inventory any available `LMS_*.txt` files and document their formats.
- Build an idempotent import command with validation and an error report.
- Hash imported plaintext passwords immediately and require a reset when appropriate.
- Never modify the source legacy files.

**Exit criteria:** A repeatable dry run and import can be performed without duplicating records.

### Phase 8: Hardening and release

- Complete end-to-end CLI tests.
- Review authorization, error handling, transaction boundaries, and logs.
- Add backup and restore documentation.
- Add sample data and user/admin usage guides.
- Tag the first stable Python release.

**Exit criteria:** All documented workflows pass, setup is reproducible, and no critical security or data-integrity issues remain.

## 9. Testing strategy

- **Unit tests:** Domain rules and services with in-memory repository substitutes.
- **Integration tests:** SQLite repositories using isolated temporary databases.
- **CLI tests:** Input/output behavior for successful operations, invalid input, and permission failures.
- **Migration tests:** Representative valid, malformed, duplicated, and incomplete legacy records.
- **Regression tests:** Every corrected legacy defect receives a test that would fail if it returned.

Tests must not depend on execution order or a developer's local database.

## 10. Cross-cutting requirements

- Validate all input at the application boundary and enforce important invariants again in the domain or database.
- Use database foreign keys and transactions for related changes.
- Use timezone-aware timestamps.
- Use `Decimal` for monetary values.
- Avoid sensitive information in logs and error messages.
- Prefer account deactivation and record statuses over destructive deletion when history must be retained.
- Keep UI-specific strings outside domain and persistence code.
- Add docstrings where behavior is not clear from names and types.

## 11. Definition of done

A phase is complete only when:

- Its acceptance and exit criteria are satisfied.
- New behavior has automated tests.
- Formatting, linting, type checking, and tests pass.
- Database changes are reproducible.
- User-facing behavior and architectural decisions are documented.
- No known critical security or data-integrity defect remains in the completed scope.

## 12. Follow-up planning

This document defines the overall direction. Later plans should describe a bounded implementation milestone, reference relevant decisions from earlier plans, include explicit acceptance criteria, and record dependencies or migrations.

The anticipated next document is `development-plan-02.md`, covering project scaffolding, concrete dependency selection, the initial database schema, and the first executable CLI shell.
