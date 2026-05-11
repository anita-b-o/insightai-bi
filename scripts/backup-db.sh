#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE_PATH="${COMPOSE_FILE_PATH:-docker-compose.yml}"
BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-backend/.env}"

read_env_value() {
  local key="$1"
  grep -E "^${key}=" "$BACKEND_ENV_FILE" | tail -n 1 | cut -d= -f2-
}

POSTGRES_USER="${POSTGRES_USER:-$(read_env_value POSTGRES_USER)}"
POSTGRES_DB="${POSTGRES_DB:-$(read_env_value POSTGRES_DB)}"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/db}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

OUTPUT_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

docker compose -f "$COMPOSE_FILE_PATH" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$OUTPUT_FILE"

echo "Database backup written to $OUTPUT_FILE"
