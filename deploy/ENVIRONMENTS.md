# Environment and secret contract

`deploy/environment-contract.json` is the machine-checked name inventory. Values are
created directly in the owning provider; none belong in Git, `.env.example`, screenshots,
release output, or issue comments.

## Vercel staging project

Set repository Root Directory to `web/`, framework preset to Next.js, Node.js to 24, and
keep access to files outside the Root Directory disabled. Use a dedicated staging
project rather than a preview connected to production.

| Name | Classification | Value rule |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Public build value | Exact HTTPS Render staging API origin; never a Supabase origin and no path |
| `NEXT_PUBLIC_CSRF_COOKIE_NAME` | Public build value | Must equal Render's `LMS_CSRF_COOKIE`; default `lms_csrf` |
| `VERCEL_TOKEN` | GitHub staging secret | Narrow deployment token; rotate after suspected disclosure |
| `VERCEL_ORG_ID` | GitHub staging secret | Vercel linkage metadata; keep out of browser configuration |
| `VERCEL_PROJECT_ID` | GitHub staging secret | ID of the dedicated staging project |

The staging dashboard's custom hostname should be `app.staging.<project-domain>`. Do not
use a `vercel.app`/`onrender.com` pair for the final cookie test because those domains are
cross-site and do not represent the approved browser design.

## Render staging service

Create the service from `render.yaml`. Automatic deployment must remain off. The service
root is the repository root and the start command only launches Uvicorn.

| Name | Classification | Value rule |
| --- | --- | --- |
| `DATABASE_URL` | Render secret | TLS Supabase direct URL when IPv6 works, otherwise Supavisor session-mode port 5432; application role only |
| `LMS_ALLOWED_ORIGINS` | Restricted runtime value | Exact Vercel staging HTTPS origin; comma-separated only when each origin is explicitly approved |
| `LMS_ENVIRONMENT` | Non-secret runtime value | `staging` |
| `LMS_SESSION_COOKIE` / `LMS_CSRF_COOKIE` | Non-secret runtime values | Must remain distinct and match the dashboard CSRF name |
| `LMS_DB_*` | Non-secret capacity controls | Begin with the bounded Blueprint values; change only with measured evidence |
| `RENDER_DEPLOY_HOOK` | GitHub staging secret | Hook for this staging service only; regenerate after suspected disclosure |

Use `api.staging.<project-domain>` as the custom hostname. Confirm managed TLS before
testing credentials. Render receives no administrative/migration database URL.

## Supabase staging project

Select a region as close as practical to Render and the intended user region. Use a
dedicated non-production project and synthetic records only.

| Name | Classification | Value rule |
| --- | --- | --- |
| `SUPABASE_PROJECT_REF` | GitHub staging variable | Dedicated staging project reference |
| `SUPABASE_ACCESS_TOKEN` | GitHub staging secret | Token able to link/apply staging migrations; never supplied to Render or Vercel |
| `SUPABASE_DB_PASSWORD` | GitHub staging secret | Staging owner password used by the CLI; never the Render application URL |

The Data API is not an application boundary. Keep LMS tables in the private `lms` schema,
retain RLS, grant no access to `anon` or `authenticated`, and do not add a Supabase client
to the dashboard.

## GitHub staging environment

Create an environment named exactly `staging`. Restrict its deployment branch/tag rules,
add a required reviewer where the repository/plan supports it, prevent self-review when
available, and add only the names in `environment-contract.json`. Variables are:
`STAGING_API_BASE_URL`, `STAGING_WEB_BASE_URL`, `STAGING_SMOKE_USERNAME`, and
`SUPABASE_PROJECT_REF`. The smoke account must contain synthetic data and the password is
stored only as `STAGING_SMOKE_PASSWORD`.

Backup-only protected values are `STAGING_DATABASE_ADMIN_URL` (secret) and
`BACKUP_AGE_RECIPIENT` (non-secret variable). The URL is a TLS administrative direct or
session-mode connection used only by the backup job. The age recipient is generated from
an offline private identity; the private identity must never be stored in GitHub, Render,
Vercel, Supabase, or the repository.

Production uses different projects, domains, tokens, database roles, and a separately
protected GitHub environment. Copying a staging secret into production or a production
secret into staging is a release blocker.
