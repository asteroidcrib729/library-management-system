# Development Plan 17: Next.js Role Dashboard

## Document information

- **Status:** Complete
- **Started:** 2026-09-06
- **Completed:** 2026-09-07
- **Depends on:** Plan 16
- **Scope:** Phase D of Plan 11; local browser/API workflows only.

## 1. Objective

Build a responsive, accessible Next.js dashboard over the committed FastAPI contract
without introducing direct Supabase access, frontend authorization assumptions, or
request-time rendering that waits for a sleeping backend. Members, librarians, and
administrators must receive coherent role-oriented workflows while FastAPI remains the
sole authentication, authorization, and business boundary.

## 2. Deliverables

1. A static public shell with registration, one-time administrator bootstrap, login,
   current-session recovery, and logout.
2. A credentialed browser client with CSRF, stable per-command idempotency keys,
   cancellation, safe-read deduplication, bounded cold-start retries, timeouts, and
   distinct warming, database-unavailable, authentication, validation, and conflict
   states.
3. A role-aware dashboard shell and capability panels for catalog, recommendations,
   loans/reservations, fines, acquisition requests, feedback, librarian operations,
   administrator account management, and operational reporting.
4. Explicit loading, empty, success, error, and retry presentation with route-level
   loading/error boundaries and no polling intended to keep providers awake.
5. Keyboard-operable semantic navigation/forms, visible focus, accessible labels and
   live announcements, responsive layouts, sufficient contrast, reduced-motion support,
   and destructive-action confirmation.
6. A restrained bundle using the existing App Router, Tailwind CSS, React Compiler,
   locally bundled Geist fonts, native controls, route splitting, and no unnecessary
   component/state library.
7. Component, request-policy, accessibility-contract, and browser-like critical-journey
   tests plus a production build and updated run documentation.

## 3. Execution rules

- The browser calls FastAPI only. It never imports backend source, connects to Supabase,
  stores passwords/session identifiers, or treats decoded client state as authorization.
- Operational data is fetched after hydration. Static layouts and sign-in presentation
  render immediately even if Render is waking or PostgreSQL is paused.
- CSRF values live only in memory/readable CSRF cookie and request headers. Mutations
  generate one idempotency key per user action and reuse it only for a retry of that same
  action.
- Only safe reads retry automatically. Mutations surface ambiguous outcomes and let the
  user deliberately retry with the retained key through the request abstraction.
- Every request is abortable; duplicate simultaneous reads share one promise. No
  keep-awake polling or unbounded retry loop is permitted.
- Role filtering improves usability but does not replace API authorization. Expected API
  errors are rendered as state, while unexpected render failures reach a Next.js error
  boundary.
- Hosted provider setup, genuine data, production deployment, and final cutover remain
  outside this plan.

## 4. Verification and exit gate

Plan 17 is complete when tests cover session recovery, login/logout, CSRF/idempotency
headers, cold/unavailable classification, deduplicated and cancelled reads, member and
staff navigation/workflows, role filtering, confirmation, loading/empty/error recovery,
and accessible names/live feedback. ESLint, TypeScript, Vitest, generated-contract drift,
Next.js production build, and the unchanged backend suite must pass. Bundle output must
remain route-split and no secret, temporary artifact, hosted connection, or provider
mutation may be introduced.

## 5. Execution record

Completed on 2026-09-07.

- Replaced the architecture-demo landing content with a user-facing, statically
  rendered library welcome screen. It offers sign-in, public member registration, and
  explicitly labeled one-time administrator bootstrap without waiting for FastAPI
  during server rendering.
- Added a root session provider that restores the opaque browser session after
  hydration, redirects signed-in users, clears local identity on any API `401`, and
  presents separate checking, Render-waking, signed-out, and unavailable states.
- Added one browser request boundary with credentialed requests, configurable API
  origin and CSRF cookie name, CSRF headers on mutations, stable per-action
  idempotency keys, safe-read promise deduplication, cancellation, 20-second attempt
  timeouts, and bounded wake recovery at 0.8, 2, and 4 seconds. Only GET requests retry
  automatically; ambiguous commands retain their original key for an explicit retry.
- Added stable UI classifications for authentication, authorization, validation,
  conflict, overload/rate limiting, Render/gateway warming, Supabase/database
  unavailability, network failure, and unexpected responses. Provider HTML is never
  rendered as an application error.
- Added a responsive role-aware dashboard with separately loaded capability panels.
  Members can browse/reserve catalog titles, manage loans and reservations, inspect
  fines, submit acquisition requests and feedback, and view recommendations/popularity.
  Staff additionally receive checkout/return, fine assessment/payment, catalog title
  and physical-copy inventory, acquisition review/linking, feedback handling, and
  operational reporting. Administrators additionally receive settlement waiver and
  confirmed account-management controls.
- Kept frontend role filtering as presentation only. Every operation still targets
  the versioned FastAPI routes, and server-side service authorization remains the
  enforcement boundary; no Supabase client or credential was added to `web/`.
- Added route-level loading and error recovery, reusable loading/waking/empty/error and
  command-result states, semantic forms and navigation, live announcements, visible
  focus, a skip link, responsive sidebar behavior, dark color support, locally bundled
  Geist fonts, and reduced-motion handling. Account deactivation requires a named
  browser confirmation before execution.
- Kept the existing Next.js 16 App Router, React 19, React Compiler, and Tailwind CSS 4
  configuration. Capability panels are dynamically split, and no component library,
  client database SDK, global state framework, or keep-awake polling was introduced.
- Added request-policy and jsdom browser-like tests for credentials, CSRF,
  idempotency, read deduplication, bounded warming retries, cancellation, database
  classification, unauthorized-session clearing, session recovery, sign-in,
  account-access semantics, member/administrator navigation, logout, staff inventory,
  approved-request acquisition, and destructive confirmation.
- Final evidence: generated API drift, ESLint, strict TypeScript, and 19 Vitest tests
  across eight files passed. The optimized Next.js 16.3.4 build passed and reported
  `/` and `/dashboard` as statically prerendered routes. The combined local regression
  gate passed Ruff lint/format, Pyrefly with zero errors, OpenAPI/client drift, all
  frontend checks, and 142 Python tests; 29 real-PostgreSQL tests were explicitly gated
  because no disposable test URL was supplied. Their unchanged Plan 16 suite had
  already passed against local PostgreSQL. The sole warning remains Starlette's known
  third-party AnyIO alias deprecation.

## 6. Exit decision

Plan 17 is complete. Plan 18 may prepare provider configuration, deployment manifests,
environment isolation, capacity/latency validation, smoke tests, and operational
runbooks. It must retain the no-genuine-data and no-production-cutover gates until the
provider, recovery, performance, and user authorization checks are explicitly approved.
