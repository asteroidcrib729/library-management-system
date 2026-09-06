# Library Management System Dashboard

This directory is the isolated Next.js 16 App Router dashboard in the project monorepo. It communicates only with the versioned FastAPI contract and never receives database credentials. Tailwind CSS 4 provides utility styling through the official PostCSS adapter, and React Compiler is enabled for the complete application.

## Local commands (PowerShell)

Copy `.env.local.example` to `.env.local`, then use the executable shim because this system's PowerShell policy blocks `npm.ps1`:

```powershell
& "C:\Program Files\nodejs\npm.cmd" ci
& "C:\Program Files\nodejs\npm.cmd" run dev
```

Run FastAPI separately from the repository root before testing signed-in workflows:

```powershell
.\.venv\Scripts\python.exe -m library_management.api
```

Quality and contract commands:

```powershell
& "C:\Program Files\nodejs\npm.cmd" run generate:api
& "C:\Program Files\nodejs\npm.cmd" run check
```

Generated API files under `src/lib/api/generated/` must not be edited manually. Regenerate them after exporting `../contracts/openapi.json` from FastAPI.

## Frontend configuration

- `postcss.config.mjs` loads `@tailwindcss/postcss`, and `src/app/globals.css` imports Tailwind.
- Global design tokens are exposed to Tailwind with `@theme inline`; CSS Modules remain available for complex component-specific styling.
- `next.config.ts` enables `reactCompiler: true`, backed by the locked `babel-plugin-react-compiler` development dependency.
- `npm run check` verifies contract drift, ESLint, strict TypeScript, Vitest, and the optimized production build.
- `NEXT_PUBLIC_API_BASE_URL` is the FastAPI origin. Browser code must never point it at Supabase or receive database credentials.
- `NEXT_PUBLIC_CSRF_COOKIE_NAME` must match the readable CSRF cookie configured by FastAPI; its default is `lms_csrf`.

## Dashboard behavior

The public route is statically rendered and restores a browser session only after
hydration. The dashboard exposes member workflows for catalog, circulation, fines,
requests, feedback, and recommendations; staff receive inventory, circulation,
financial, engagement, and reporting controls; administrators additionally receive
account management and fine-waiver controls. These role-specific controls improve the
interface but do not replace FastAPI authorization.

Safe reads use bounded retries when Render is waking. Mutations never retry
automatically: a deliberate retry retains the same idempotency key so an ambiguous
response cannot duplicate the command. The client distinguishes a waking backend from
an unavailable database and does not poll either provider to keep it active.

## Vercel staging boundary

`vercel.json` fixes the locked install/build commands and response security headers. In
Vercel project settings, select this directory (`web/`) as Root Directory, Node.js 24,
and keep access to source files outside the Root Directory disabled. Configure only
`NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_CSRF_COOKIE_NAME`; follow
`../deploy/ENVIRONMENTS.md` and never add database or provider credentials here.
