# PostgreSQL migrations

`migrations/20260905000100_initial_lms.sql` creates application schema version 1.
`migrations/20260905000200_idempotency_claims.sql` advances schema version 2 with
atomic processing/completed idempotency records. Migrations are immutable once applied;
subsequent changes require a new timestamped SQL file.
Dashboard-only schema changes are prohibited. The CLI owns migration history, while
`lms.schema_version` is the API compatibility marker. Migration SQL acquires a
transaction advisory lock and executes atomically; API startup never migrates.

Apply pending migrations to the local development database from the repository root:

```powershell
& "C:\Program Files\nodejs\npx.cmd" --yes supabase@2.116.0 migration up --local
```

Application tables use a private `lms` schema with RLS and no public policies. The
development owner account bypasses RLS; hosted application roles and grants must be
explicitly reviewed before deployment. Constraints enforce row invariants and
uniqueness; cross-row circulation/financial rules and immutable settlement operations
are additionally enforced by the repositories and canonical row locks from Plan 14.

Integration tests create a uniquely named `lms_test_*` database, apply these files
there, and drop only the database they created. They never reset the working database.
The fresh-target SQLite import and logical backup/restore procedure is documented in
`DATA_MIGRATION.md`.
