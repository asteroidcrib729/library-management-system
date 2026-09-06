# Development Plan 18: Three-Provider Deployment Readiness and Spike

## Document information

- **Status:** In progress
- **Started:** 2026-09-07
- **Depends on:** Plan 17
- **Scope:** Phase E of Plan 11; non-production infrastructure and synthetic data only.

## 1. Objective

Prepare and rehearse the Render, Supabase, and Vercel delivery path as one ordered,
observable release without weakening the existing application, database, browser, or
monorepo boundaries. Produce reproducible configuration, protected automation,
performance/security probes, backup and incident runbooks, and a dated provider-tier
recommendation. A real hosted spike is required before this plan can be marked complete,
but provisioning and credential use require explicit owner authorization.

## 2. Current provider facts and decisions

These findings were rechecked against official provider documentation on 2026-09-07 and
must be checked again immediately before a hosted rehearsal.

- Render Free is explicitly not for production. It supplies 0.1 CPU and 512 MB RAM,
  spins down after 15 minutes without inbound HTTP/WebSocket traffic, wakes on a new
  connection in about one minute, has an ephemeral filesystem, cannot scale beyond one
  instance, and can be suspended for unusually high outbound traffic such as an
  external database. It remains eligible only for this synthetic spike or an approved
  personal demonstration.
- Render Blueprints now use `runtime` and `autoDeployTrigger`; the older `env` and
  `autoDeploy` fields are deprecated. Production-style auto-deploy is disabled. A
  protected workflow supplies an exact commit SHA to the deploy hook using `ref` and
  waits for both liveness and database readiness.
- Vercel must set the project Root Directory to `web/`. This repository is not a Node
  workspace, so Vercel's workspace-aware automatic monorepo skipping cannot be assumed;
  the Root Directory and reviewed project settings are the isolation controls. Only the
  public FastAPI origin and CSRF cookie name may be exposed at build time.
- Vercel Hobby remains limited to personal, non-commercial use and can pause when an
  included allowance is exhausted. Any institutional, team, or commercial pilot must
  select an eligible paid tier before Plan 19.
- Supabase Free currently includes a 500 MB database on shared CPU/500 MB RAM, 5 GB
  egress, two active projects, no automatic backups, and pausing after one week of low
  activity. A paused project requires an owner to choose **Resume project** in Studio;
  application traffic cannot resume an already paused project.
- Render is a persistent backend. Use the Supabase direct connection when Render can
  reach IPv6; otherwise use shared Supavisor **session mode** on port 5432. Do not use
  transaction mode: it does not support the session behavior needed by this code's
  transaction settings and migration advisory locks. Migration, dump, and restore jobs
  use a separate direct or session-mode administrative URL with TLS.

Official references:

- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Render free-service limits](https://render.com/docs/free)
- [Render exact-commit deploys](https://render.com/docs/deploys)
- [Vercel monorepo configuration](https://vercel.com/docs/monorepos)
- [Vercel Hobby terms and allowances](https://vercel.com/docs/plans/hobby)
- [Supabase connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase Free pricing](https://supabase.com/pricing)
- [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [GitHub deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)

## 3. Deliverables

1. A schema-addressed `render.yaml` with Python 3.14.2, an exact start command, liveness
   health check, disabled automatic deployment, build filters, redacted environment
   variables, bounded single-instance pool settings, and no migration-at-startup step.
2. A `web/vercel.json` and dashboard setup contract fixing `web/` as the provider Root
   Directory, Next.js as the framework, Node 24, isolated preview/staging/production
   variables, and no database/backend secrets.
3. A redacted environment matrix naming every public value, runtime secret, migration
   secret, deployment credential, scope, rotation owner, and forbidden destination.
4. A manually dispatched GitHub staging workflow ordered as CI gate -> migration
   dry-run -> protected migration -> exact-SHA Render deploy -> readiness -> Vercel
   build/deploy -> security/smoke probes -> release record. It must never run on a pull
   request or silently target production.
5. Credential-safe deployment validation, smoke/security checks, warm/cold latency and
   bounded-concurrency measurement tooling that emits machine-readable evidence without
   logging cookies, passwords, tokens, database URLs, or response bodies.
6. Off-provider backup/export and clean-target restore instructions using the existing
   native PostgreSQL tooling, including encryption/retention ownership and a scheduled
   workflow design that cannot overwrite its only recovery point.
7. Runbooks for deployment, rollback, provider pause/suspension, database recovery,
   quota inspection, incident triage, stabilization, and release evidence.
8. A measured staging report covering topology/region, versions, exact commit,
   deployment identifiers, warm and cold timing, bundle size, 20-user mixed load,
   50-user burst, database/pool/lock behavior, browser security, recovery, quotas, and
   the free-versus-paid tier decision.

## 4. Safety and execution rules

- Hosted actions require explicit owner approval, dedicated non-production projects,
  synthetic accounts/data, and protected environment secrets. The repository may
  prepare automation without possessing or requesting secret values.
- `DATABASE_URL` belongs only to Render. The migration/backup URL belongs only to the
  protected GitHub environment. Neither belongs in Vercel, `NEXT_PUBLIC_*`, artifacts,
  command output, provider build logs, or committed files.
- Preview deployments never connect to production. A frontend preview uses an isolated
  preview API/database or a contract mock; absence of either disables authenticated
  preview workflows instead of falling back to production.
- Migration is never part of Render build/start and never runs concurrently from each
  application instance. The protected workflow acquires the existing migration lock,
  applies committed migrations, verifies schema history, then deploys the API.
- Each release uses `github.sha` as identity. Vercel builds the checked-out SHA and the
  Render hook receives that SHA explicitly. The frontend cannot promote until the API
  reports both `/health/live` and `/health/ready` successfully.
- Probes default to safe reads. Login/logout testing may create and revoke only a
  synthetic test session. Mixed mutation load requires dedicated synthetic users and
  catalog copies plus an explicit write flag; it must never target production.
- Monitoring verifies genuine availability and quotas but must not create keep-awake
  traffic to evade provider free-tier policies.
- A database backup is useful only after restoration into a clean disposable target and
  reconciliation pass. Backup output must be encrypted before off-provider storage and
  must never be committed or uploaded as a general workflow artifact.
- Applied migrations roll forward. Component rollback must prove schema compatibility;
  database restore is a last-resort, explicitly approved maintenance operation.

## 5. Implementation sequence

1. Add and validate provider descriptors, environment contracts, and path classification.
2. Add local deployment-config tests and credential-safe probe/report tooling.
3. Add protected staging automation and operator runbooks with provider actions disabled
   until the required GitHub environment and secrets exist.
4. Re-run the complete local Python, PostgreSQL, contract, frontend, and build gates.
5. With owner authorization, create isolated provider projects in compatible nearby
   regions, load synthetic seed data, configure same-site test subdomains where possible,
   and execute the exact-commit staging workflow.
6. Measure warm operation first, then allow a natural Render idle spin-down and record
   the first-request wake. Manually pause/resume only the disposable Supabase project if
   the selected plan and UI permit the rehearsal; never fabricate keep-awake traffic.
7. Execute safe, mixed, burst, security, backup/restore, and component rollback drills;
   capture redacted evidence and compare it with Plan 11's targets.
8. Record a tier recommendation and complete/no-go decision. Do not begin genuine-data
   import or production cutover until every Phase E gate has evidence.

## 6. Verification and exit gate

Plan 18 is complete only when configuration validation, action/workflow linting, all
local quality gates, a real isolated hosted deployment, exact-SHA traceability,
credentialed browser security, TLS/origin/CSRF/logout tests, migration/backup/restore,
warm/cold measurements, the 30-minute 20-user mixed run, the separate 50-user burst,
quota inspection, monitoring alerts, and API/frontend rollback have passed. Ordinary
warm reads must meet 500 ms p95 and writes 1 second p95 from the intended region, with
cold start reported separately. Unexpected 5xx, lost updates, connection leaks,
unbounded waits, exposed secrets, production access, or unreconciled restore results are
blocking failures.

## 7. Execution record

Repository preparation completed locally on 2026-09-07.

- Added a current Render Blueprint using the official schema address, Python 3.14.2,
  one Free spike instance, bounded PostgreSQL settings, backend-only build filters,
  liveness health checks, graceful shutdown, redacted runtime values, and disabled
  automatic deployment. Database migration is absent from both build and startup.
- Added the Vercel project descriptor under `web/` with locked installation/build
  commands and baseline browser security headers. The operator contract requires Root
  Directory `web/`, Node 24, a dedicated staging project, and no access to repository
  source outside that root.
- Added a machine-readable environment contract and an offline validator that detects
  drift between Render, Vercel, GitHub staging secrets/variables, and forbidden browser
  values. Deployment-related path changes now fail open to the complete CI graph, and
  the root check plus CI backend job run the validator explicitly.
- Added a manual, environment-protected staging workflow. It requires an exact
  40-character commit with a successful stable `CI` check and explicit
  `DEPLOY-STAGING` confirmation, previews/applies committed migrations, sends that SHA
  to Render, blocks on liveness/readiness, builds the isolated Vercel project, and runs
  redacted smoke and timing probes. It has no push/pull-request trigger and no production
  environment or credential reference.
- Added credential-safe smoke, security, timing, and synthetic-load tooling. It validates
  HTTPS origins, frontend headers, readiness, exact credentialed CORS, untrusted-origin
  rejection, hosted cookie flags, current session, CSRF logout, client/server/database
  readiness timings, 20-user mixed load, and a 50-user read burst without printing URLs,
  credentials, cookies, bodies, or tokens in its JSON evidence.
- Added safe application observability headers and structured request logs. Allowed
  browser origins can read request IDs and `Server-Timing`; readiness distinguishes the
  application span from its database probe. Hosted responses add HSTS, no-sniff,
  anti-framing, and no-referrer headers without exposing provider/database details.
- Added environment, exact-commit release, browser security, cold-start, manual Supabase
  resume, load/capacity, monitoring/quota, backup/clean-restore, incident, stabilization,
  and component rollback procedures plus a staging evidence/tier-decision template.
- Added a manual protected staging backup workflow. It validates a PostgreSQL custom
  archive, downloads a pinned/checksummed age 1.3.2 binary, encrypts to an offline-owned
  public recipient before upload, deletes runner plaintext, and retains a uniquely named
  encrypted GitHub artifact for seven days. It has no schedule and cannot overwrite the
  prior recovery point; durable production retention remains a Plan 19 tier decision.
- The offline deployment validator, Ruff, formatting, Pyrefly with zero errors, and 21
  focused configuration/API/probe tests pass. Full local and hosted evidence is recorded
  below after the final gates.
- The complete local quality command passed after these changes: 150 Python tests passed
  and 29 explicitly gated PostgreSQL tests skipped without a disposable URL; Ruff and
  formatting passed; Pyrefly reported zero errors; OpenAPI, generated TypeScript, and
  deployment contracts were current; all 19 Vitest tests, ESLint, strict TypeScript, and
  the optimized Next.js production build passed. `/` and `/dashboard` remain statically
  prerendered. The only warning is Starlette's known third-party AnyIO alias deprecation.

### 7.1 Remaining hosted gate

Plan 18 remains **in progress**. No Render, Supabase, Vercel, GitHub environment, custom
domain, monitoring rule, or backup storage was created or changed; no credentials or
genuine data were requested. The local Docker/Supabase rehearsal could not run because
Docker Desktop's Linux engine was not running. Completion now requires explicit owner
authorization plus dedicated staging projects/domains, protected secret configuration,
synthetic accounts/data, an encrypted off-provider backup destination, and execution of
the measured security/load/recovery/rollback spike. `PERFORMANCE-REPORT.md` remains
intentionally pending rather than substituting invented results.
