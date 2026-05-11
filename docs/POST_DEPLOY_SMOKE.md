# Post-Deploy Smoke Checklist

## Core Health

- `GET /health` returns `200`
- `GET /health/worker` returns `healthy`
- `docker compose ps` shows healthy `db`, `backend`, `frontend`

## Functional Smoke

1. Login with a real user.
2. Upload a CSV dataset.
3. Open the dataset detail page.
4. Run one Ask AI query.
5. Generate insights.
6. Create a dashboard.
7. Save a query widget.
8. Refresh the dashboard.
9. Create a share link.
10. Open the public share page.

## Operational Smoke

- backend logs show structured `event=` lines
- worker logs show cycle completion
- no prompts or tokens appear in logs
- dashboard refresh finishes without leaving `refresh_in_progress=true`

## If Any Step Fails

1. Capture `docker compose logs --tail=200 backend dashboard-refresh-worker frontend`
2. Record the failing route and `X-Request-ID`
3. Check `/health/worker`
4. Decide whether to rollback before expanding traffic
