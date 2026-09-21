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

The PostgreSQL dump is the complete persistent dataset backup. It must include
normal application tables, every dynamic `dataset_<id>` table, and
`alembic_version`. Model metadata and Alembic migrations cannot recreate the
contents of dynamic dataset tables. Any future Neon migration must copy those
tables as well as the regular schema.

## Database Restore

Restore a compressed database dump:

```bash
./scripts/restore-db.sh backups/db/insightai_bi_20260511T120000Z.sql.gz
```

For production:

```bash
COMPOSE_FILE_PATH=docker-compose.prod.yml BACKEND_ENV_FILE=deploy/backend.prod.env ./scripts/restore-db.sh backups/db/insightai_bi_20260511T120000Z.sql.gz
```

CSV storage is not backed up or restored: uploads are transient ingestion
artifacts and PostgreSQL is the sole persistent source of truth.

## Minimum Retention Recommendation

- database: 7 daily, 4 weekly, 3 monthly

## Recovery Validation

After restore:

- `docker compose ps`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/health/worker`
- login works
- dataset opens
- Ask AI works
- dashboard share works
