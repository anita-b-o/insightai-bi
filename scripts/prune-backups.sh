#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_RETENTION_DAYS="${DB_RETENTION_DAYS:-14}"
STORAGE_RETENTION_DAYS="${STORAGE_RETENTION_DAYS:-14}"

find "$ROOT_DIR/backups/db" -type f -name '*.sql.gz' -mtime +"$DB_RETENTION_DAYS" -delete 2>/dev/null || true
find "$ROOT_DIR/backups/storage" -type f -name '*.tar.gz' -mtime +"$STORAGE_RETENTION_DAYS" -delete 2>/dev/null || true

echo "Pruned backups older than ${DB_RETENTION_DAYS}d (db) and ${STORAGE_RETENTION_DAYS}d (storage)"
