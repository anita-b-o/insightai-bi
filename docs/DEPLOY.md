# Deploy Guide

## Prerequisites

- Docker and Docker Compose installed
- `deploy/compose.prod.env` populated with public production values
- `deploy/backend.prod.env` populated with production-safe backend secrets
- OpenAI key set if Ask AI and insights should be enabled
- Previous image tags recorded for rollback

## Production Files

Copy and edit:

```bash
cp deploy/compose.prod.env.example deploy/compose.prod.env
cp deploy/backend.prod.env.example deploy/backend.prod.env
```

## Production Compose

Use the production overlay:

```bash
docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml up -d --build
```

The production compose file:

- keeps PostgreSQL off the public host network
- terminates TLS in Caddy on ports `80` and `443`
- enables worker health checks
- expects `APP_ENV=production`

## Recommended Deploy Order

1. Run a database backup.
2. Run a storage backup.
3. Pull or build the new images.
4. Deploy with the production compose file.
5. Wait for `db`, `backend`, and `frontend` to become healthy.
6. Validate `https://<api-domain>/health`.
7. Validate `https://<api-domain>/health/worker`.
8. Run the post-deploy smoke checklist.

## Quick Commands

```bash
docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml build
docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml up -d
docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml ps
docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml logs --tail=200 backend dashboard-refresh-worker
./scripts/deploy-prod.sh
```

## Required Environment

At minimum:

- `APP_ENV=production`
- `SECRET_KEY` set to a non-placeholder value
- `POSTGRES_PASSWORD` set
- `OPENAI_API_KEY` set if AI flows are enabled
- `APP_DOMAIN` and `API_DOMAIN` pointing to the server
- `ACME_EMAIL` set for TLS issuance
- `VITE_SENTRY_DSN` if frontend error reporting should go to Sentry

## Post-Deploy Checks

- `curl https://<api-domain>/health`
- `curl https://<api-domain>/health/worker`
- `docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml ps`
- run [POST_DEPLOY_SMOKE.md](./POST_DEPLOY_SMOKE.md)
