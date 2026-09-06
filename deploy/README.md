# Deployment boundary

This directory describes the non-production three-provider release path introduced by
Plan 18. The committed files are configuration contracts, probes, report templates, and
operator instructions; they do not prove that a hosted deployment exists.

## Provider ownership

| Provider | Owns | Must not receive |
| --- | --- | --- |
| Vercel | Next.js build and static/dashboard delivery from repository Root Directory `web/` | Database URLs/passwords, Supabase tokens, Render hooks, smoke passwords |
| Render | One FastAPI web service built from the repository root | Vercel or GitHub credentials, backup decryption keys |
| Supabase | Private `lms` PostgreSQL schema and migration history | Frontend source/runtime responsibilities |
| GitHub staging environment | Ordered migration/deployment credentials and staging evidence | Production credentials during Plan 18 |

Run the offline consistency gate from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_deployment
```

See [ENVIRONMENTS.md](ENVIRONMENTS.md) before creating any provider variable and
[RUNBOOK.md](RUNBOOK.md) before running the protected staging workflow. Record real,
redacted results in a copy of [PERFORMANCE-REPORT.md](PERFORMANCE-REPORT.md); do not
invent or commit secret-bearing evidence.
