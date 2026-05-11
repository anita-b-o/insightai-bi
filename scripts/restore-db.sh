#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/restore-db.sh <backup.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

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

gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE_PATH" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Database restore completed from $BACKUP_FILE"
