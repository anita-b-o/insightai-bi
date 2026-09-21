# Scheduled dashboard refresh

Scheduled refresh is a best-effort, zero-cost path for the portfolio deployment:

```text
GitHub Actions (every 10 minutes)
-> authenticated POST /internal/scheduled-refresh/run
-> FastAPI scheduled refresh cycle
-> PostgreSQL dashboard state and locks
```

`next_refresh_at` in PostgreSQL is the source of truth. The workflow only asks
the backend to evaluate due dashboards; it cannot select a dashboard or submit
SQL.

## Required production configuration

Set the same randomly generated `SCHEDULER_SECRET` only in:

1. Render backend environment variables.
2. GitHub repository Actions secret named `SCHEDULER_SECRET`.

Do not add it to Vercel, frontend build variables, local committed files, or
workflow logs. Until both values are configured, the internal endpoint returns
`503` and no scheduled work runs.

The request signs `timestamp.invocation_id` with HMAC-SHA256. The backend uses
a five-minute request-age limit, constant-time signature comparison, and a
unique PostgreSQL invocation record. Replays never run a second cycle.

## Health semantics

The worker health endpoint reports real cycle state. Its stale threshold is
derived from `SCHEDULER_EXPECTED_INTERVAL_SECONDS` (600) plus
`SCHEDULER_HEARTBEAT_GRACE_SECONDS` (300), not from an arbitrary continuous
worker heartbeat. A healthy cycle may therefore be up to 15 minutes old.

GitHub schedules are best-effort, and a Render Free cold start can delay a
cycle. A stale `/health/worker` result is intentionally an operational signal,
not a request to suppress the check.

## Free Render storage limitation

Render Free cannot attach a persistent disk. InsightAI currently stores the
original CSV at `Dataset.storage_path`, so a restart, deploy, or sleep can
remove those source files. Dataset tables already materialized in PostgreSQL
remain, but operations that require rereading the original CSV can fail. This
is a separate storage architecture issue; this scheduler change does not solve
or hide it.
