# Development Plan 03: Domain and SQLite Foundation

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-03.md`
- **Depends on:** `development-plan-01.md`, `development-plan-02.md`
- **Milestone:** Establish the domain model, versioned SQLite schema, repository boundaries, and transaction lifecycle.

## 1. Objectives

- Express the core library concepts as validated, UI-independent domain objects.
- Create a relational schema that preserves identity, history, and referential integrity.
- Make schema creation idempotent and prepare for future migrations.
- Define repository contracts without coupling services to SQLite.
- Coordinate repository operations through an explicit Unit of Work transaction.
- Implement and test repositories for users, books, and physical book copies.

## 2. Domain decisions

- Database-generated integer identifiers provide internal identity.
- Usernames are normalized and restricted to an unambiguous portable character set.
- A `Book` represents bibliographic information; a `BookCopy` represents physical inventory.
- Copy status does not encode loans or reservations. Those are separate historical records.
- All timestamps are timezone-aware in Python and stored as UTC ISO-8601 text.
- Monetary values use `Decimal` in Python and integer minor units in SQLite.
- Records with historical value use statuses or deactivation instead of destructive deletion.

## 3. Schema version 1

Schema version 1 contains:

- `schema_migrations`
- `users`
- `books`
- `book_copies`
- `reservations`
- `loans`
- `fines`
- `book_requests`
- `feedback`

Foreign keys, checks, unique constraints, partial indexes, and search indexes enforce the rules that are safe to enforce at the persistence boundary.

## 4. Repository boundaries

Initial contracts:

- `UserRepository`: add, retrieve by ID or username, update a password hash, deactivate
- `BookRepository`: add, retrieve by ID, search, list
- `BookCopyRepository`: add, retrieve, list by book, update status
- `UnitOfWork`: expose repositories and explicitly commit or roll back one transaction

Repositories return domain objects and translate expected SQLite integrity failures into application-specific persistence exceptions.

## 5. Transaction rules

- Repository methods never commit independently.
- A Unit of Work begins one transaction and owns its connection.
- Leaving a Unit of Work without calling `commit()` rolls back.
- Exceptions always roll back before the connection closes.
- SQLite foreign-key enforcement is enabled for every connection.
- Database initialization applies each missing migration once.

## 6. Deliverables

- Domain enums, entities, validation, and exceptions
- Versioned SQLite database initializer
- Complete version 1 relational schema
- Repository protocols and persistence exceptions
- SQLite user, book, and book-copy repositories
- SQLite Unit of Work
- Application startup database initialization
- Domain, schema, repository, and transaction tests
- Updated project documentation

## 7. Acceptance criteria

- Database initialization is repeatable without losing data.
- Every expected table and index is created.
- Foreign-key enforcement is enabled on each connection.
- Invalid domain state is rejected before persistence.
- Duplicate usernames, ISBNs, book identities, and barcodes are rejected consistently.
- Repository queries return correctly typed domain objects.
- Uncommitted Unit of Work changes are rolled back.
- Committed changes remain visible in later Units of Work.
- The CLI initializes the configured database before opening its prompt.
- Pytest, Pyrefly, Ruff lint, Ruff formatting, and CLI smoke checks pass.

## 8. Completion record

Completed on 2026-09-04 with the following results:

- SQLite schema version 1 initialized successfully and idempotently.
- Nine schema tables and all planned indexes were created.
- Domain validation covers identifiers, normalized values, dates, timestamps, and money.
- User, book, and book-copy repositories passed persistence and duplicate tests.
- Unit of Work commit and automatic rollback behavior passed integration tests.
- SQLite foreign-key enforcement passed an explicit negative test.
- The configured application database was created successfully during a live CLI run.
- Pytest: 27 tests passed.
- Pyrefly: no errors.
- Ruff lint and formatting checks passed.
- Package version and interactive CLI smoke tests passed.

The next plan will cover account application services, administrator bootstrapping, authentication, and corresponding CLI commands.
