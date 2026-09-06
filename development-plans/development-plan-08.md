# Development Plan 08: Book Requests and Feedback

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-08.md`
- **Depends on:** `development-plan-01.md` through `development-plan-07.md`
- **Milestone:** Deliver traceable member book-request and feedback workflows.

## 1. Objectives

- Let authenticated members submit and inspect book acquisition requests.
- Prevent duplicate pending requests from the same member for the same work.
- Let library staff approve or reject pending requests with review metadata.
- Link approved requests to a catalog record when acquisition is completed.
- Let authenticated users submit and inspect their feedback.
- Let library staff review and archive feedback without deleting its history.
- Replace the legacy append-only text files with validated domain models and SQLite repositories.

## 2. Workflow and authorization decisions

- Book requests move from `pending` to `approved` or `rejected`.
- Only an `approved` request can move to `acquired`, and acquisition links an existing book ID.
- Rejected requests require a review note; approval notes are optional.
- Pending requests have no reviewer or review timestamp.
- Feedback moves from `new` to `reviewed` and then `archived`.
- Members see only their own requests and feedback.
- Librarians and administrators can view all submissions and perform state transitions.
- Historical requests and feedback are retained; this milestone does not physically delete records.

## 3. Schema migration

Schema version 4 adds reviewer, review timestamp, review note, and acquisition metadata to `book_requests`. It also adds status, reviewer, and review timestamp fields to `feedback`. Existing requests remain pending and existing feedback remains new.

## 4. CLI commands

- `request-book`: submit an acquisition request interactively
- `requests [status]`: show personal requests; staff see all and may filter by status
- `review-request <id> <approved|rejected>`: review a pending request (staff only)
- `acquire-request <request-id> <book-id>`: link an approved request to the catalog (staff only)
- `submit-feedback`: submit feedback interactively
- `feedbacks [status]`: show personal feedback; staff see all and may filter by status
- `review-feedback <id>`: mark new feedback reviewed (staff only)
- `archive-feedback <id>`: archive reviewed feedback (staff only)

## 5. Deliverables

- Schema migration version 4
- Extended request and feedback domain state validation
- Request and feedback repository contracts and SQLite implementations
- Engagement application service and presentation-safe view types
- CLI submission, listing, review, acquisition, and archive commands
- Domain, migration, repository, authorization, transition, and live CLI tests
- Updated README and completion record

## 6. Acceptance criteria

- Schema version 3 databases migrate to version 4 without losing submissions.
- Existing requests default to pending and existing feedback defaults to new.
- Blank submissions and invalid publication years are rejected.
- Duplicate pending requests by the same member are rejected case-insensitively.
- Members cannot inspect another account's submissions or perform staff transitions.
- Review metadata identifies the acting staff account and timestamp.
- Invalid request and feedback state transitions are rejected without changing persistence.
- Acquired requests reference an existing catalog record.
- History remains available after requests or feedback reach a terminal state.
- Pytest, Pyrefly, Ruff lint, Ruff formatting, package, and live CLI smoke checks pass.

## 7. Completion record

Completed on 2026-09-04 with the following results:

- Existing schema version 3 databases migrated to version 4 without losing book requests or feedback.
- Existing requests retained `pending` status and existing feedback received `new` status.
- Book-request and feedback domain models enforced state-specific reviewer, timestamp, note, catalog-link, and acquisition metadata.
- Members submitted and inspected their own requests and feedback through persistent SQLite repositories.
- Case-insensitive duplicate pending requests from the same member were rejected.
- Staff could view all submissions and filter them by status; members remained limited to their own records.
- Request approval and rejection captured the reviewing staff account and timestamp, with a mandatory rejection note.
- Only approved requests could be marked acquired, and acquisition required and retained a valid catalog link and acting staff metadata.
- Feedback followed the enforced `new` → `reviewed` → `archived` lifecycle without record deletion.
- Invalid and unauthorized transitions left persisted state unchanged.
- Live CLI member submission, personal history, duplicate rejection, authorization, staff review, catalog linkage, filtering, and feedback archive workflows passed.
- Pytest: 89 tests passed.
- Pyrefly: no errors.
- Ruff lint and formatting checks passed.
- Package version smoke test passed.

The next plan will consider catalog recommendations, reporting, and operational hardening.
