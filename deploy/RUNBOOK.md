# Staging deployment, operations, and rollback runbook

This runbook is deliberately procedural. Stop at any failed gate; do not improvise a
production fallback, bypass readiness, or replace an unavailable staging dependency with
a production one.

## 1. One-time non-production setup

1. Confirm the deployment is personal/non-commercial if Vercel Hobby is selected. Use an
   eligible paid plan for organizational or commercial activity.
2. Create a dedicated Supabase staging project, a Render staging service from
   `render.yaml`, and a dedicated Vercel staging project rooted at `web/`. Record region,
   tier, owner, project/service IDs, and quota-reset dates.
3. Configure the same-site custom names `app.staging.<project-domain>` and
   `api.staging.<project-domain>`, then wait for valid TLS. Default provider domains may
   be used for unauthenticated reachability only.
4. Create the variables and secrets exactly as described in `ENVIRONMENTS.md`. Verify
   `DATABASE_URL` uses `sslmode=require` or stronger and a direct or Supavisor
   session-mode endpoint on port 5432.
5. Create one synthetic smoke member and the dedicated synthetic users/data required for
   load testing. Never copy a genuine SQLite database into staging during Plan 18.
6. In Supabase, confirm `lms` is not in exposed Data API schemas and that `anon` and
   `authenticated` cannot select it. Retain the RLS/privilege assertions in migrations.

## 2. Exact-commit deployment

1. Merge only after the stable `CI` result succeeds for the candidate commit. Record its
   full 40-character SHA.
2. In GitHub Actions, manually run **Deploy staging** with that exact SHA and the phrase
   `DEPLOY-STAGING`. Approve the protected `staging` environment only after reviewing the
   target names.
3. The workflow rechecks the SHA's `CI` result, previews and applies only committed
   Supabase migrations, passes the SHA to Render's deploy hook, and waits for both health
   endpoints before building/deploying Vercel.
4. It then checks frontend/backend reachability, exact credentialed CORS, origin
   rejection, hosted cookie flags, current-session resolution, CSRF-protected logout,
   and safe warm latency. Its JSON contains status/timing/size metadata only.
5. Copy the redacted output into the performance report together with Supabase migration
   version, deployment IDs, operator, timestamps, region, and outcome. GitHub runner
   temporary files are not a backup or durable evidence store.

## 3. Browser security gate

In current Chrome, Edge, and Firefox, run the following through the custom staging
domains. Use developer tools only to inspect names/flags—never copy token values.

1. Load the static sign-in page with the API cold. It must remain interactive and change
   from checking to a bounded waking state.
2. Sign in with the synthetic member. Confirm the session cookie is host-only, Secure,
   HttpOnly, SameSite=Lax, and Path `/`; confirm the CSRF cookie is Secure,
   SameSite=Lax, readable, and Path `/api/v1`.
3. Exercise catalog read, reservation create/cancel, session refresh, and sign-out.
   Confirm mutation requests include the CSRF and idempotency headers and no secret is in
   local/session storage.
4. Repeat one member authorization rejection against a staff route. It must be a stable
   403 and no hidden control may be treated as authorization.
5. Change the Origin to an unapproved value using an isolated HTTP test client; unsafe
   requests must be rejected. Never disable browser protections to simulate success.

## 4. Latency and capacity procedure

1. Run 25 warm samples from a runner near the intended users:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.deployment_probe measure `
     --api-origin https://api.staging.example `
     --web-origin https://app.staging.example `
     --samples 25 --output C:\outside-repository\warm.json
   ```

2. Record client elapsed time and response bytes separately from `Server-Timing`'s
   application and readiness database spans. Capture Vercel Web Analytics/Core Web
   Vitals and both provider region names alongside—not as substitutes for—the probe.
3. Allow Render to become naturally idle for more than 15 minutes. Make one real
   `/health/ready` request, record total wake time and intermediate status, then repeat
   warm samples. Do not poll to keep the service awake.
4. Run the 30-minute, 20-user mixed scenario and separate 50-user read burst using the
   dedicated synthetic users `load.user.01` through `load.user.50`. Store their shared
   synthetic-only password in a process variable and run:

   ```powershell
   $env:STAGING_LOAD_PASSWORD = '<set outside repository>'
   .\.venv\Scripts\python.exe -m scripts.deployment_probe load `
     --api-origin https://api.staging.example `
     --web-origin https://app.staging.example `
     --password-environment STAGING_LOAD_PASSWORD `
     --users 20 --duration-seconds 1800 --write-every 20 `
     --output C:\outside-repository\mixed-load.json

   .\.venv\Scripts\python.exe -m scripts.deployment_probe load `
     --api-origin https://api.staging.example `
     --web-origin https://app.staging.example `
     --password-environment STAGING_LOAD_PASSWORD `
     --users 50 --duration-seconds 60 --write-every 0 --think-time 0 `
     --output C:\outside-repository\read-burst.json
   Remove-Item Env:STAGING_LOAD_PASSWORD
   ```

   The mixed test deliberately creates synthetic feedback records and therefore must
   never point at production. Record
   operation counts, p50/p95/max, controlled 429/503, unexpected 5xx, connection/pool
   pressure, lock/deadlock logs, CPU/RAM, database size, and egress. The current
   Blueprint ceiling is one Render instance and five application pool connections.
5. Fail the gate if warm reads exceed 500 ms p95, ordinary writes exceed 1 second p95,
   any state is lost/duplicated, queues are unbounded, health is starved, or an
   unexpected 5xx occurs. A cold start is reported separately, never averaged away.

## 5. Supabase pause and dependency incident

- On Free, watch the owner mailbox for the inactivity warning. Monitoring must not send
  artificial traffic solely to defeat pausing.
- If already paused, the owner opens Supabase Studio, selects the staging project, and
  chooses **Resume project**. Render/browser traffic does not perform this action.
- During the pause, `/health/live` may be 200 while `/health/ready` is 503 and API errors
  classify the database as unavailable. Verify this presentation before resuming.
- After resume, wait for readiness, then run smoke checks. If it remains unavailable,
  verify project state, connection mode, password rotation, TLS, network restrictions,
  pool exhaustion, and schema version—in that order—without printing the URL.

## 6. Backup and restore drill

1. Generate an age identity offline. Store its private identity in a separate password
   manager/offline recovery location and put only its public recipient in the GitHub
   staging variable `BACKUP_AGE_RECIPIENT`. Add the administrative TLS connection as the
   protected secret `STAGING_DATABASE_ADMIN_URL`.
2. Supply the administrative direct/session URL only through process/protected
   environment `DATABASE_URL`. Run the existing `backup` and `verify-backup` commands in
   `supabase/DATA_MIGRATION.md`; record SHA-256, size, entry count, and elapsed time.
3. Manually run **Backup staging** with `BACKUP-STAGING`. It creates and verifies a
   custom archive, verifies the pinned age download checksum, encrypts before upload,
   removes the plaintext runner copy, and creates a uniquely named seven-day GitHub
   artifact plus encrypted checksum. It has no schedule so it cannot become Free-tier
   keep-awake traffic. Never overwrite the previous known-good archive.
4. Create a clean disposable PostgreSQL target, download/decrypt one retained archive,
   run the guarded restore, and reconcile schema 1-3, counts, digests, circulation,
   financial totals, RLS, readiness, and synthetic login. Record recovery-point age and
   recovery time.
5. Delete only the disposable restore target after evidence review. Database restore in
   production remains a Plan 19 maintenance/data-loss decision.

Free Supabase supplies no automatic backups. The encrypted seven-day GitHub artifact is
adequate only for the staging spike. Durable storage, longer retention, deletion
protection, rotation ownership, and alerting must be selected before genuine-user
admission; scheduled backup remains blocked until it cannot be mistaken for keep-awake
traffic or an adequate production recovery policy.

## 7. Monitoring and quota inspection

At the start/end of the spike and weekly during any pilot, record:

- Render instance hours, outbound bandwidth, pipeline minutes, CPU/RAM, restart/suspend
  notices, request errors, application duration, pool/transaction duration, and health;
- Supabase project state, database size/500 MB, egress/5 GB, connection counts, slow
  queries, lock waits/deadlocks, and backup status;
- Vercel plan eligibility, edge requests, transfer, build/deployment use, Web Vitals,
  error logs, and allowance notices; and
- GitHub migration/deployment/backup failures and the age of the last verified restore.

Use provider-native notifications during the spike. Continuous unattended availability,
durable backups, alert routing, or support expectations are upgrade triggers, not reasons
to create keep-awake probes.

## 8. Component rollback

1. Stop promotion and record the failing commit/deployment ID. Do not reverse an applied
   migration automatically.
2. If Render fails after an expand migration, deploy the prior compatible API SHA and
   verify both health endpoints. If it is incompatible, roll forward with a corrective
   migration/code release.
3. If Vercel fails, select/promote the previous staging deployment while retaining the
   healthy compatible API. Re-run browser smoke.
4. If Supabase migration fails, leave frontend/backend promotion stopped. Diagnose from
   migration history and transaction result; never edit history merely to make it green.
5. A data restore requires maintenance mode, explicit owner approval, a verified archive,
   clean-target rehearsal, and a stated data-loss window.

Complete rollback only after readiness, smoke, data invariants, logs, and deployment
identities are recorded for the resulting state.
