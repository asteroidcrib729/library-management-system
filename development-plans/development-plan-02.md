# Development Plan 02: Python Foundation and Interactive CLI

## Document information

- **Status:** Completed
- **Project:** Library Management System
- **Plan:** `development-plan-02.md`
- **Depends on:** `development-plan-01.md`
- **Milestone:** Produce an installable Python 3.14 project with a tested interactive CLI foundation.

## 1. Confirmed decisions

- Python 3.14 is the only supported runtime for this initial development cycle.
- The environment is stored locally in `.venv/`.
- SQLite from the Python standard library will provide persistence.
- The first interface is an interactive, PowerShell-inspired command shell.
- Rich provides styled output; Prompt Toolkit provides prompting, completion, and history.
- The application controls colors and text styling. The terminal profile controls the font.
- Passwords use Argon2id through `argon2-cffi`.
- Pytest provides automated testing.
- Pyrefly provides static type and syntax analysis and is listed in `requirements.txt`.
- Ruff provides deterministic formatting and supplementary lint checks.
- Application code uses a `src/` package layout.

## 2. Password-hashing decision

Generic digest libraries and fast algorithms such as SHA-256 are not suitable for password storage. Argon2id is memory-hard, widely recommended for new systems, and supported on Python 3.14 by `argon2-cffi`.

The application will use the high-level `argon2.PasswordHasher` API with its maintained defaults. Each password receives a random salt automatically. Successful authentication will check whether the stored hash needs upgraded parameters and will persist a replacement hash when required.

Plaintext passwords must never be stored, logged, included in exceptions, or placed in fixtures.

## 3. Deliverables

- `.venv/` created with Python 3.14
- `requirements.txt` containing runtime and development tools
- `pyproject.toml` containing package and tool configuration
- Installable `library_management` package
- Environment-aware local data paths
- Custom Rich and Prompt Toolkit color themes
- PowerShell-inspired interactive prompt
- Initial `help`, `about`, `status`, `clear`, and `exit` commands
- Argon2id password service with rehash support
- Initial Pytest suite
- Setup, appearance, and quality-check documentation

## 4. CLI constraints

The CLI should provide command history, suggestions, completion, readable error messages, and a consistent custom palette. It must remain functional without color.

A process cannot reliably select the host terminal font. Windows Terminal users should configure Cascadia Mono, Cascadia Code, or another preferred monospace font in their terminal profile. No application feature may depend on a particular font being installed.

## 5. Implementation sequence

1. Create and verify the Python 3.14 virtual environment.
2. Add packaging, dependency, and quality-tool configuration.
3. Add configuration and local data-directory handling.
4. Build the interactive shell and initial informational commands.
5. Add the Argon2id password abstraction.
6. Install the package in editable mode.
7. Run Pytest, Pyrefly, Ruff, and a non-interactive CLI smoke test.
8. Record final dependency versions and milestone results.

## 6. Acceptance criteria

- `.venv/Scripts/python.exe` reports Python 3.14.
- Python can import `sqlite3` inside the virtual environment.
- `python -m library_management --version` succeeds.
- The interactive CLI displays the custom prompt and accepts its foundation commands.
- The CLI can run with colors disabled.
- Password hashes identify Argon2id and correct/incorrect password tests pass.
- `pytest`, `pyrefly check`, `ruff check .`, and `ruff format --check .` pass.
- Generated environment, history, database, and cache files are ignored by Git.

## 7. Completion record

Completed on 2026-09-04 with the following verified baseline:

- Python 3.14.2
- SQLite 3.50.4
- `argon2-cffi` 25.1.0 using Argon2id
- Prompt Toolkit 3.0.53
- Rich 14.3.4
- Pytest 9.1.1: 7 tests passed
- Pyrefly 1.2.0: no errors
- Ruff 0.16.5: lint and formatting checks passed
- Package and interactive CLI smoke tests passed

The next plan will cover the SQLite schema, domain entities, repository contracts, and database lifecycle.
