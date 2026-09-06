# Development Plan 05: Catalog and Inventory Workflows

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-05.md`
- **Depends on:** `development-plan-01.md` through `development-plan-04.md`
- **Milestone:** Deliver searchable catalog and physical-copy management through services and the interactive CLI.

## 1. Objectives

- Allow authenticated users to browse, search, and inspect the catalog.
- Allow librarians and administrators to create and update book records.
- Track each physical copy by a unique normalized barcode.
- Report total and currently available copy counts.
- Let staff mark copies available, damaged, lost, or withdrawn.
- Preserve circulation integrity by reserving the `on_loan` status for the future circulation service.
- Preserve historical book records instead of physically deleting them.

## 2. Domain and authorization decisions

- A book and a physical copy remain separate entities.
- ISBN is optional; supplied ISBN-10 and ISBN-13 values are normalized and checksum validated.
- Title, author, and publication year form a uniqueness fallback when ISBN is absent.
- Members may read catalog information but cannot mutate it.
- Librarians and administrators are catalog staff.
- A withdrawn copy cannot be restored through ordinary catalog commands.
- A copy marked `on_loan` cannot be changed by catalog commands.
- Catalog services reload the acting account so stale or deactivated sessions cannot authorize writes.

## 3. CLI commands

- `books [query]`: list all books or search title, author, and ISBN
- `book <id>`: show one catalog record and availability summary
- `copies <book-id>`: show all physical copies for a book
- `add-book`: interactively create a book record (staff only)
- `update-book <id>`: interactively update a book record (staff only)
- `add-copy <book-id> [barcode]`: create physical inventory (staff only)
- `copy-status <barcode> <status>`: set available, damaged, lost, or withdrawn (staff only)

## 4. Deliverables

- ISBN normalization and validation
- Shared service-level authorization helpers
- Catalog service and presentation-safe catalog entry
- Book metadata update repository operation
- Catalog and copy-management CLI commands
- Service and integration tests for permissions, searching, duplicates, and status transitions
- Updated README and milestone record

## 5. Acceptance criteria

- Valid formatted ISBN values normalize to their canonical compact form.
- Invalid ISBN checksums are rejected before persistence.
- Authenticated members can list, search, and inspect books and copies.
- Missing books and copies produce clear application errors.
- Members cannot create or update catalog records.
- Librarians and administrators can create books and copies.
- Duplicate book identities, ISBNs, and barcodes produce safe conflict errors.
- Book updates retain identity and creation timestamps.
- `on_loan` can only be managed by the circulation layer.
- Withdrawn copies cannot be restored by the catalog layer.
- Pytest, Pyrefly, Ruff lint, Ruff formatting, and live CLI smoke checks pass.

## 6. Completion record

Completed on 2026-09-04 with the following results:

- ISBN-10 and ISBN-13 normalization and checksum validation passed.
- Barcode normalization and validation passed.
- Member catalog browsing, searching, detail, and copy-listing workflows passed.
- Librarian and administrator catalog-write authorization passed.
- Book and copy conflicts were translated into safe application errors.
- Book updates retained persistent identity and creation timestamps.
- Catalog attempts to assign or override `on_loan` status were rejected.
- Withdrawn-copy restoration through catalog management was rejected.
- Live CLI book creation, copy creation, search, detail, availability, and status workflows passed.
- Live availability changed correctly after a copy status update.
- Pytest: 54 tests passed.
- Pyrefly: no errors.
- Ruff lint and formatting checks passed.
- Package version smoke test passed.

The next plan will cover reservations, checkout, return, and circulation policies.
