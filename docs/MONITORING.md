# Monitoring

## Sentry

### Backend

Set in `deploy/backend.prod.env`:

- `SENTRY_DSN`
- `SENTRY_ENVIRONMENT=production`
- `SENTRY_RELEASE=<image-tag-or-commit>`
- `SENTRY_TRACES_SAMPLE_RATE=0`

### Frontend

Set in `deploy/compose.prod.env`:

- `VITE_SENTRY_DSN`
- `VITE_SENTRY_ENVIRONMENT=production`
- `VITE_SENTRY_TRACES_SAMPLE_RATE=0`

The frontend reports:

- uncaught browser errors
- unhandled promise rejections
- explicit runtime error reports from the app

The backend reports:

- unhandled FastAPI exceptions
- worker crashes when the DSN is configured

## Uptime Monitoring

Recommended checks:

- `https://api.example.com/health`
- `https://api.example.com/health/worker`
- `https://app.example.com/`

Recommended tools:

- UptimeRobot
- Better Stack

## Alert Suggestions

- `/health` not `200`
- `/health/worker` returns `degraded`
- repeated Sentry issues for:
  - `openai_request_failed`
  - `dashboard_refresh_failed`
  - `auth_bootstrap_failed`
