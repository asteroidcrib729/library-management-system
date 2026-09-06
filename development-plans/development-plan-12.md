# Development Plan 12: Monorepo and Local Platform Foundation

## Document information

- **Status:** Complete
- **Project:** Library Management System
- **Plan:** `development-plan-12.md`
- **Depends on:** `development-plan-11.md`
- **Started:** 2026-09-05
- **Completed:** 2026-09-05
- **Milestone:** Execute Phase A of Plan 11 without provisioning production resources.

## 1. Objective

Establish the executable foundation for the approved asymmetric monorepo:

- retain the Python 3.14 backend and CLI at the repository root;
- add an isolated TypeScript Next.js project under `web/`;
- add a minimal FastAPI delivery adapter without changing business behavior;
- establish deterministic OpenAPI and frontend type/client generation;
- create reproducible local Supabase/PostgreSQL configuration;
- define environment boundaries and safe PowerShell workflows;
- add one stable, component-aware GitHub CI result; and
- capture initial concurrency, connection, latency, and bundle baselines that later plans must refine.

This plan creates foundations only. It does not implement PostgreSQL repositories, migrate SQLite data, implement browser authentication or business routers, create cloud projects, deploy services, or accept genuine user data.

## 2. Verified starting state

| Item | Verified state | Consequence |
| --- | --- | --- |
| Project virtual environment | `.venv` uses Python 3.14.2 with pip 25.3 | Use `.venv/Scripts/python.exe` as the authoritative local Python command. |
| Global Python launcher | `py -3.14` does not currently resolve an installation | Scripts must prefer `.venv`; setup documentation must explain recreation rather than assume the launcher works. |
| Node.js | Node 24.13.0 is installed | Accept Node 24 as the initial local/CI major line after Next.js compatibility is verified. |
| npm | npm 11.10.0 is installed; PowerShell execution policy blocks `npm.ps1` | PowerShell instructions and scripts use `npm.cmd`. |
| Docker | Docker CLI 29.7.2 is installed | Local Supabase is possible after the Docker Desktop engine is started. |
| Docker engine | Not running at plan start | Database startup/integration validation remains incomplete until the engine responds. |
| Supabase CLI | No global command found | Use an explicitly pinned supported CLI invocation or install method; do not assume a global executable. |
| Python application | Domain, services, repository protocols, SQLite adapter, maintenance, CLI, and tests exist | FastAPI wraps existing services; it does not call CLI code or duplicate rules. |
| Git working tree | Existing project files are untracked and the former root C++ file appears moved into `legacy/` | Preserve all existing work and avoid destructive Git operations. |

The first local start found that Windows had reserved TCP ranges containing Supabase's generated `5432x` defaults even though no process was listening. The committed local ports therefore use the unreserved `554xx` range: PostgreSQL `55432`, pooler `55429`, shadow database `55420`, and disabled ancillary services in the same range.

## 3. Decisions for this phase

### 3.1 Repository layout

- Python remains rooted at `src/library_management/` with root `pyproject.toml` and `requirements.txt`.
- Next.js is the only Node project and owns `web/package.json` plus one `web/package-lock.json`.
- Do not add Turborepo, Nx, workspaces, or a root Node package.
- Supabase local configuration and SQL history live under `supabase/`.
- GitHub workflows live under `.github/workflows/`.
- Root `scripts/` owns cross-component PowerShell and contract utilities.

### 3.2 FastAPI foundation

- Add `library_management.api` as a delivery adapter with an application factory.
- Keep imports side-effect free: importing the ASGI application cannot create files, connect to a database, or migrate a schema.
- Add versioned metadata plus `/health/live` and `/health/ready`.
- Readiness is dependency-driven and must not claim database readiness before the PostgreSQL probe exists.
- Add exact-origin CORS configuration for local development; production origins remain unset until deployment configuration is approved.
- Continue using synchronous services. No async persistence rewrite belongs to this phase.

### 3.3 Contract boundary

- Export FastAPI OpenAPI deterministically to `contracts/openapi.json`.
- Provide a check mode that fails when the committed contract is stale.
- Generate TypeScript API types under `web/src/lib/api/generated/`.
- Commit generated output so the Vercel `web/` build has no dependency on root Python source.
- Never hand-edit generated artifacts.

### 3.4 Local database foundation

- Initialize a committed `supabase/config.toml` through a supported CLI.
- Add synthetic-only seed configuration and ignore CLI temporary state.
- Use explicit local commands and never link to or contact a production project in this phase.
- Defer the application schema and PostgreSQL repository implementation to Plan 13.

### 3.5 CI model

- One always-started workflow produces one stable required `ci` result.
- A repository-owned change classifier selects Python, database, contract, frontend, or documentation jobs.
- Contract and deployment changes fan out to all affected checks.
- Pull-request jobs receive no production or migration credentials.

## 4. Work packages

### Package A: Safety and toolchain contracts

- Extend `.gitignore` for Node, Next.js, environment, Supabase temporary, coverage, log, and database artifacts.
- Add `.python-version`, backend and frontend example environment files, and Node/npm version declarations.
- Document commands that work under the current PowerShell execution policy.

### Package B: Minimal FastAPI adapter

- Add FastAPI and ASGI runtime dependencies with Python 3.14-compatible ranges.
- Implement settings validation, application factory, health schemas/routes, CORS, and central response behavior.
- Add factory, health, import-side-effect, invalid-configuration, and OpenAPI tests.

### Package C: Contract generation

- Add deterministic export/check tooling.
- Commit the first contract and add a drift test.
- Establish frontend generated types and a typed fetch-client construction point.

### Package D: Next.js foundation

- Scaffold `web/` with App Router, strict TypeScript, ESLint, source directory, Tailwind CSS 4, and React Compiler.
- Add accessible foundation styling and a small system-status page without business functionality.
- Add type, lint, test, production-build, and API-generation scripts.

### Package E: Supabase local foundation

- Pin a supported Supabase CLI invocation and initialize root configuration.
- Add safe local seed placeholders and PowerShell preflight/instructions.
- Start/reset the local stack and capture the installed PostgreSQL version once Docker Desktop is running.

### Package F: CI and developer workflow

- Add repository-owned path classification with unit tests.
- Add component jobs and an always-run CI summary.
- Add `scripts/check.ps1` matching local quality gates.
- Add `scripts/dev.ps1` that validates prerequisites and never silently targets remote infrastructure.

## 5. Execution order

1. Record baseline and create this plan.
2. Apply repository/environment safety changes.
3. Add and test the minimal FastAPI adapter.
4. Export and verify the OpenAPI contract.
5. Scaffold and verify Next.js plus generated API types.
6. Initialize and verify local Supabase configuration.
7. Add change-aware CI and PowerShell workflows.
8. Run the complete clean local quality sequence.
9. Update Plan 11/README status and mark this plan complete only after every blocking criterion passes.

Packages may be committed separately later, but their generated contracts and dependency files must remain internally consistent at every review boundary.

## 6. Verification matrix

| Area | Required evidence |
| --- | --- |
| Existing Python behavior | All existing Pytest tests still pass; Ruff and Pyrefly remain clean. |
| FastAPI | Factory and import have no filesystem/database side effects; liveness succeeds; readiness fails closed without a database probe; OpenAPI is stable. |
| Configuration | Unsafe local/production URL combinations fail with actionable messages; secrets are not emitted. |
| Contract | Export is deterministic; check mode detects drift; generated frontend types match the committed contract. |
| Next.js | Tailwind/PostCSS and React Compiler are enabled; locked install, lint, strict type check, component test, and production build pass. |
| Local Supabase | CLI config is reproducible; local reset/start works once the Docker engine is available; no remote project is linked. |
| CI classifier | Representative frontend, backend, database, contract, deployment, and docs-only path sets select the correct jobs. |
| PowerShell | Commands use the project `.venv` and `npm.cmd`; preflight reports missing/stopped dependencies clearly. |
| Repository hygiene | No `.env`, provider token, database dump, `.next`, `node_modules`, Supabase temp state, or runtime data is tracked. |

## 7. Initial baselines and budgets

This phase records mechanisms and initial local measurements, not cloud capacity claims:

- API liveness response and OpenAPI generation time;
- frontend production bundle output and build duration;
- local warm page load and health-request timing where measurable;
- configured future Psycopg pool baseline of zero idle/minimum and five maximum connections;
- one Render process and bounded synchronous database work as the Plan 13/15 starting model; and
- CI duration per selected component.

Provider cold-start, cross-provider latency, real connection pressure, and 20/50-user tests remain Plan 17 responsibilities.

## 8. Risks and controls

| Risk | Control |
| --- | --- |
| Scaffolding overwrites existing Python files | Frontend writes only under new `web/`; inspect the tree before and after generation. |
| Latest dependencies do not support Python 3.14 or Node 24 | Verify package metadata and execute imports/builds before accepting versions. |
| PowerShell chooses the wrong Python or blocked npm shim | Use explicit `.venv/Scripts/python.exe` and `npm.cmd`. |
| Docker/Supabase validation is unavailable | Complete all independent packages, report the precise gate, and do not falsely mark the plan complete. |
| A health endpoint claims readiness without PostgreSQL | Fail readiness closed until Plan 13 supplies the real probe and migration check. |
| Generated artifacts drift | Generate deterministically and fail local/CI checks on differences. |
| Preview or local code receives production secrets | Do not create cloud links; validate environment identity and commit examples only. |
| CI skips a mandatory status | Always run the classifier and final summary even when component jobs are skipped. |

## 9. Acceptance criteria

- The approved asymmetric directory structure exists without relocating existing Python code.
- Python 3.14 CLI behavior remains green after FastAPI dependencies and modules are added.
- The ASGI factory, closed readiness behavior, and deterministic OpenAPI contract are tested.
- Next.js builds independently from `web/` using only its committed files and public example configuration.
- Frontend API types can be regenerated from the root contract and pass a drift check.
- Local Supabase configuration is committed and successfully validated against a running local engine.
- PowerShell setup/check/development commands are safe, documented, and use explicit executable paths.
- Component-aware CI has a stable always-reported summary design and valid workflow syntax.
- No production account, provider deployment, real secret, or genuine user data is created or used.
- Plan 13 can start without relying on undocumented local state.

## 10. Completion record

Phase A completed on 2026-09-05 without provisioning or linking any hosted resource.

### 10.1 Delivered foundation

- Added a side-effect-free `library_management.api` adapter, validated local/production settings, exact-origin CORS, liveness, and dependency-driven readiness. Readiness deliberately returns HTTP 503 until Plan 13 injects the PostgreSQL probe.
- Added deterministic FastAPI OpenAPI export/check tooling, committed `contracts/openapi.json`, generated TypeScript types, and a typed `openapi-fetch` construction point.
- Added an isolated Next.js 16.3.4 App Router project under `web/` with strict TypeScript, ESLint, Vitest/Testing Library, self-hosted Geist fonts, Tailwind CSS 4.3.3, and React Compiler 1.0.0 enabled for the application.
- Added pinned Supabase CLI 2.116.0 configuration with local-only network restrictions, synthetic seeding, PostgreSQL, and the session-mode pooler. No hosted project was linked.
- Added conservative repository-owned change classification, unit coverage, component-aware GitHub jobs, and one always-run `CI` summary job. Contract changes fan out to producer and consumer checks; database changes include the backend; deployment and unknown paths fail open to every check.
- Added safe `scripts/check.ps1` and `scripts/dev.ps1` workflows. They use the project virtual environment and `npm.cmd`; the development script requires an explicit switch before starting local containers and cannot link to remote Supabase.
- Expanded root and frontend documentation, environment examples, version contracts, and ignore rules for secrets, generated builds, database files, and Supabase temporary state.

### 10.2 Verification evidence

| Gate | Result |
| --- | --- |
| Complete local quality workflow | `scripts/check.ps1` passed through process-scoped execution-policy bypass. |
| Python | Ruff lint and formatting passed; Pyrefly reported 0 errors; Pytest passed 121 tests with one third-party Starlette/AnyIO deprecation warning. |
| API contract | Root OpenAPI check passed in approximately 0.91 seconds; generated frontend types were current. |
| Live API | `/health/live` returned `200`/`ok`; the minimum of five warm local calls was approximately 2.95 ms. `/health/ready` correctly returned 503 before PostgreSQL adapter integration. |
| Frontend | ESLint, route type generation, strict TypeScript, two Vitest component tests, and the production build passed. The verified build compiled in 2.2 seconds and emitted static `/` and `/_not-found` routes. |
| Tailwind and React Compiler | Locked top-level packages are Tailwind CSS 4.3.3, `@tailwindcss/postcss` 4.3.3, and `babel-plugin-react-compiler` 1.0.0; the compiler is enabled in `next.config.ts`. |
| Local database | Supabase start and `db reset` passed. PostgreSQL 17.6, the database on `55432`, and the pooler on `55429` reported healthy. |
| Windows port control | Generated `5432x` ports were inside Windows-reserved TCP ranges; all committed local Supabase ports were moved to the available `554xx` range and examples were synchronized. |
| Developer workflow | `dev.ps1 -StartDatabase` passed and reported only the local database URL plus separate API/dashboard commands. |
| CI | Representative backend, frontend, database, contract, docs, deployment, and unknown path selections are covered by six classifier tests. Official current `actions/checkout`, `setup-python`, and `setup-node` v6 majors are used. |
| Hygiene | `.env`, `node_modules`, `.next`, `supabase/.temp`, and database/dump patterns were confirmed ignored; no matching unignored build, secret, or database artifact was found. |

### 10.3 Deferred by design

- Plan 13 owns the Psycopg pool (starting target: zero minimum and five maximum application connections), PostgreSQL unit of work/repositories, real migrations, readiness probe, query/index baselines, and concurrent correctness tests.
- Plans 14-18 retain SQLite migration/recovery, full FastAPI capability/session work, dashboard workflows, provider deployment measurements, and production cutover respectively.
- GitHub-hosted execution will begin only after these currently uncommitted repository files are committed and pushed. The workflow has been locally reviewed and its classifier/test commands have passed; the first remote workflow run remains repository-host evidence, not a Phase A local blocker.

All acceptance criteria for this plan are satisfied. `development-plan-13.md` is now the next implementation plan.

Subsequent sequencing note (2026-09-05): Plan 13 split the original persistence scope
into infrastructure in Plan 13 and repository/business parity in Plan 14. The authoritative
updated sequence is Plan 11 Section 12.1; later phases now extend through Plan 19.
