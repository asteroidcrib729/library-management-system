# Plan 18 staging evidence template

Do not mark a row passed without attached redacted evidence. Do not include credentials,
cookie/token values, database URLs, genuine data, or complete response bodies.

## Release identity

| Field | Recorded value |
| --- | --- |
| Date/time and operator | Pending |
| Full Git commit SHA | Pending |
| Supabase project/region/tier | Pending |
| Schema versions | Pending |
| Render service/region/tier/deploy ID | Pending |
| Vercel project/region/tier/deploy ID | Pending |
| Custom staging domains/TLS | Pending |

## Timing and capacity

| Measurement | Target | Result/evidence |
| --- | --- | --- |
| Vercel/static root warm p95 and bytes | Recorded baseline | Pending |
| API ready warm client p95 | <= 500 ms | Pending |
| Server application span | Recorded separately | Pending |
| Readiness database span | Recorded separately | Pending |
| Ordinary authenticated read p95 | <= 500 ms | Pending |
| Ordinary write p95 | <= 1 second | Pending |
| Natural Render cold-start duration | Report separately | Pending |
| 20 users, mixed read/write, 30 minutes | No lost state/leaks/unexpected 5xx | Pending |
| 50-user read burst | Bounded queue and controlled overload | Pending |
| Core Web Vitals and route chunks | Pass/record provider results | Pending |

## Security, recovery, and operations

| Gate | Result/evidence |
| --- | --- |
| Same-site custom-domain cookies in Chrome/Edge/Firefox | Pending |
| Exact credentialed CORS and unapproved-origin rejection | Pending |
| CSRF, idempotency, authorization rejection, logout/revocation | Pending |
| Supabase private schema/RLS/Data API denial | Pending |
| Migration dry-run/apply/history/readiness | Pending |
| Encrypted off-provider backup and checksum | Pending |
| Clean-target restore, reconciliation, measured RPO/RTO | Pending |
| Render cold wake and Supabase manual-resume presentation | Pending |
| Provider alert delivery and quota visibility | Pending |
| Prior API and frontend component rollback | Pending |
| Browser bundle/log/artifact secret scan | Pending |

## Tier recommendation and decision

- Intended use classification: Pending.
- Expected genuine users/concurrency/catalog/traffic: Pending.
- Render decision and upgrade trigger: Pending.
- Supabase decision and upgrade trigger: Pending.
- Vercel decision and eligibility evidence: Pending.
- Residual risks and owners: Pending.
- Phase E decision: **Pending — not authorized for genuine users or Plan 19 cutover.**
