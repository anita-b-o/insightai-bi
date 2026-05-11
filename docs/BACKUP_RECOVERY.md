# Backup And Recovery

## Database Backup

Create a compressed PostgreSQL dump:

```bash
./scripts/backup-db.sh
```

For production:

```bash
COMPOSE_FILE_PATH=docker-compose.prod.yml BACKEND_ENV_FILE=deploy/backend.prod.env ./scripts/backup-db.sh
```

Optional output location:

```bash
BACKUP_DIR=/srv/backups/insightai-bi/db ./scripts/backup-db.sh
```

## Storage Backup

Create a compressed archive of uploaded dataset storage:

```bash
./scripts/backup-storage.sh
```

For production:

```bash
COMPOSE_FILE_PATH=docker-compose.prod.yml ./scripts/backup-storage.sh
```

Optional output location:

```bash
BACKUP_DIR=/srv/backups/insightai-bi/storage ./scripts/backup-storage.sh
```

## Database Restore

Restore a compressed database dump:

```bash
./scripts/restore-db.sh backups/db/insightai_bi_20260511T120000Z.sql.gz
```

For production:

```bash
COMPOSE_FILE_PATH=docker-compose.prod.yml BACKEND_ENV_FILE=deploy/backend.prod.env ./scripts/restore-db.sh backups/db/insightai_bi_20260511T120000Z.sql.gz
```

## Manual Storage Restore

1. Stop write traffic to the application.
2. Stop `backend` and `dashboard-refresh-worker`.
3. Extract the archive back into `/app/storage` using the backend container or a temporary container with the `app_storage` volume mounted.
4. Start `backend` and `dashboard-refresh-worker`.
5. Run the post-deploy smoke checklist.

Example:

```bash
cat backups/storage/app_storage_20260511T120000Z.tar.gz | docker compose exec -T backend tar xzf - -C /app
```

## Minimum Retention Recommendation

- database: 7 daily, 4 weekly, 3 monthly
- storage: 7 daily, 4 weekly

## Recovery Validation

After restore:

- `docker compose ps`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/health/worker`
- login works
- dataset opens
- Ask AI works
- dashboard share works
