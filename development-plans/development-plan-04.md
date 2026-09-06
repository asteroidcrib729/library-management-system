# Development Plan 04: Accounts, Authentication, and Authorization

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-04.md`
- **Depends on:** `development-plan-01.md`, `development-plan-02.md`, `development-plan-03.md`
- **Milestone:** Add secure account workflows, authenticated CLI sessions, and service-level authorization.

## 1. Objectives

- Register member accounts without exposing persistence details to the CLI.
- Bootstrap exactly one initial administrator through an explicit local command.
- Let administrators create librarian accounts.
- Authenticate active accounts with generic failure responses.
- Maintain an in-process authenticated CLI session without retaining passwords.
- Upgrade outdated Argon2id hashes after successful authentication.
- Enforce authorization inside application services.
- Support safe account deactivation while preventing removal of the final active administrator.

## 2. Security decisions

- Passwords must contain 12-128 characters. Passphrases are supported without arbitrary symbol or capitalization rules.
- Password prompts are masked and excluded from persistent command history.
- Account lookup, password mismatch, and inactive-account failures return the same authentication error.
- The CLI receives a principal containing only identity, display name, username, and role.
- Administrator bootstrap closes once any administrator record exists.
- Only administrators may create librarian accounts or deactivate another account.
- The final active administrator cannot be deactivated.
- Authorization is enforced by services even when commands are invoked directly.

## 3. CLI commands

- `register`: create a member account
- `bootstrap-admin`: create the first administrator, then become permanently unavailable
- `login`: begin an authenticated session
- `logout`: end the current session
- `whoami`: display the current principal
- `create-librarian`: administrator-only librarian creation
- `deactivate-account`: deactivate the signed-in account and end the session
- `deactivate-user [username]`: administrator-only deactivation of another account

Passwords are always collected interactively and are never accepted as command-line arguments.

## 4. Deliverables

- Account and authentication application services
- Application-level exceptions and authenticated principal type
- Password policy
- Repository support for role counts
- CLI account and session commands
- Dependency wiring in the composition root
- Unit and integration tests for authentication and authorization paths
- Updated user documentation

## 5. Acceptance criteria

- Member registration persists an Argon2id hash rather than plaintext.
- Duplicate usernames produce a safe, specific registration failure.
- Initial administrator bootstrap succeeds once and is rejected thereafter.
- Only an administrator can create a librarian.
- Valid credentials authenticate active users.
- Invalid, unknown, and inactive accounts receive one generic error.
- A valid outdated hash is upgraded during login.
- The final active administrator cannot be deactivated.
- CLI password entry is masked and does not use file-backed history.
- Pytest, Pyrefly, Ruff lint, Ruff formatting, and live CLI smoke checks pass.

## 6. Completion record

Completed on 2026-09-04 with the following results:

- Member registration stores Argon2id hashes and rejects duplicate usernames safely.
- Password length, maximum length, and whitespace-only validation passed.
- Administrator bootstrap succeeded once and closed after initial setup.
- Administrator-only librarian creation and account-deactivation authorization passed.
- Invalid, unknown, and inactive account authentication returned the same failure.
- Outdated Argon2id parameters were upgraded after successful authentication.
- Final-active-administrator protection passed.
- Live CLI bootstrap, login, identity display, logout, and exit workflows passed.
- Live CLI history inspection confirmed that form fields and passwords were not persisted.
- Pytest: 39 tests passed.
- Pyrefly: no errors.
- Ruff lint and formatting checks passed.
- Package version smoke test passed.

The next plan will cover catalog and physical-copy application services and their CLI workflows.
