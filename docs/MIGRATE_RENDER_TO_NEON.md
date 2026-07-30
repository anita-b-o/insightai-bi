# Render PostgreSQL to Neon PostgreSQL

This runbook migrates InsightAI BI from Render PostgreSQL to Neon PostgreSQL
with a short write freeze and a rollback window. It assumes PostgreSQL 18 on
both providers.

## Connection policy

- `DATABASE_URL`: Neon pooled URL, used by the API and dashboard worker.
- `DATABASE_DIRECT_URL`: Neon direct URL, used by Alembic.
- `pg_dump`, `pg_restore`, schema migrations, and administrative checks always
  use direct URLs.
- Keep `sslmode=require&channel_binding=require` in both Neon URLs.

Neon's pooler runs in transaction mode. The application does not use
session-level `SET`, `LISTEN/NOTIFY`, session advisory locks, or persistent
temporary tables, so its runtime queries are compatible with the pooled URL.

## Preconditions

1. `migration.env.local` exists locally with mode `600` and contains:

   ```text
   RENDER_DATABASE_URL=...
   NEON_DATABASE_URL=...
   NEON_DATABASE_DIRECT_URL=...
   ```

2. The Render source and Neon target use PostgreSQL 18.
3. The Neon target has no user tables.
4. Render is still connected to Render PostgreSQL.
5. The Render PostgreSQL database is retained throughout the rollback window.

Do not commit `migration.env.local` or print its contents.

## Phase 1: prepare an isolated backup directory

```bash
cd /home/anita/Desktop/Workspace/insightai-bi
MIGRATION_DIR="$PWD/backups/neon-migration-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$MIGRATION_DIR"
chmod 700 "$MIGRATION_DIR"
printf '%s\n' "$MIGRATION_DIR"
```

Keep that terminal open so `MIGRATION_DIR` remains defined.

## Phase 2: freeze writes

In Render:

1. Disable automatic deploys temporarily.
2. Suspend the dashboard refresh worker, if one exists.
3. Suspend the web service or otherwise block all write traffic.
4. Confirm there are no uploads, registrations, dashboard refreshes, or AI
   queries in progress.

Do not change `DATABASE_URL` yet. If any step fails before cutover, resume the
services with the original Render database.

## Phase 3: capture the final source signature

```bash
docker run --rm -i \
  --env-file migration.env.local \
  -v "$PWD/scripts:/scripts:ro" \
  postgres:18-alpine \
  sh -eu -c 'psql "$RENDER_DATABASE_URL" -X -v ON_ERROR_STOP=1 \
    -f /scripts/postgres-migration-signature.sql' \
  > "$MIGRATION_DIR/render.signature"
```

## Phase 4: export Render PostgreSQL

```bash
docker run --rm \
  --env-file migration.env.local \
  -v "$MIGRATION_DIR:/backup" \
  postgres:18-alpine \
  sh -eu -c 'pg_dump "$RENDER_DATABASE_URL" \
    --format=custom \
    --no-owner \
    --no-acl \
    --verbose \
    --file=/backup/render.dump'
```

Validate the archive before restore:

```bash
sha256sum "$MIGRATION_DIR/render.dump" \
  | tee "$MIGRATION_DIR/render.dump.sha256"

docker run --rm \
  -v "$MIGRATION_DIR:/backup:ro" \
  postgres:18-alpine \
  pg_restore --list /backup/render.dump \
  > "$MIGRATION_DIR/render.dump.list"

test -s "$MIGRATION_DIR/render.dump"
test -s "$MIGRATION_DIR/render.dump.list"
```

## Phase 5: restore into empty Neon

The target must still have zero user tables. Do not add `--clean` to this
command.

```bash
docker run --rm \
  --env-file migration.env.local \
  -v "$MIGRATION_DIR:/backup:ro" \
  postgres:18-alpine \
  sh -eu -c 'pg_restore \
    --dbname="$NEON_DATABASE_DIRECT_URL" \
    --no-owner \
    --no-acl \
    --single-transaction \
    --exit-on-error \
    --verbose \
    /backup/render.dump'
```

`--single-transaction` ensures a restore error does not leave a partially
restored target.

## Phase 6: compare source and destination

```bash
docker run --rm -i \
  --env-file migration.env.local \
  -v "$PWD/scripts:/scripts:ro" \
  postgres:18-alpine \
  sh -eu -c 'psql "$NEON_DATABASE_DIRECT_URL" -X -v ON_ERROR_STOP=1 \
    -f /scripts/postgres-migration-signature.sql' \
  > "$MIGRATION_DIR/neon.signature"

diff -u "$MIGRATION_DIR/render.signature" "$MIGRATION_DIR/neon.signature"
```

The diff must be empty. Also run from `backend/` with the direct Neon URL:

```bash
alembic current
alembic heads
alembic check
```

All commands must report `20260511_0018 (head)` and no pending schema
operations.

## Phase 7: change Render

Set these variables on the Render web service:

```text
DATABASE_URL=<Neon pooled URL>
DATABASE_DIRECT_URL=<Neon direct URL>
```

Set the same variables on the dashboard refresh worker, if it exists. Do not
change `SECRET_KEY`, CORS, OpenAI, storage, Sentry, JWT, or any other variable.

Save the variables and deploy the reviewed revision. The Blueprint pre-deploy
command runs `alembic upgrade head` through `DATABASE_DIRECT_URL`; because the
restored database is already at head, it should be a no-op.

Vercel requires no database variable changes. Keep `VITE_API_BASE_URL` pointing
to the same Render backend URL.

## Phase 8: production smoke

1. `GET /health` returns `200`.
2. `GET /health/worker` is healthy if the worker is deployed.
3. Existing user login works.
4. Existing datasets open and their row counts match the final source
   signature.
5. Run a read-only Ask AI query.
6. Generate insights.
7. Create and refresh a dashboard.
8. Create and open a public share link.
9. Upload a small disposable CSV and confirm it can be queried.
10. Inspect Render logs for database, pool, SSL, or migration errors.

## Rollback

Until the smoke test is accepted:

1. Keep Render PostgreSQL intact.
2. Keep the final dump and checksum.
3. If cutover validation fails, restore both Render services'
   `DATABASE_URL` values to the original Render connection and redeploy.
4. Do not try to merge writes made independently to both databases.

Retire Render PostgreSQL only after the agreed rollback window and after
retaining the final dump in durable storage.
