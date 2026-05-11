#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE_PATH="${COMPOSE_FILE_PATH:-docker-compose.yml}"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/storage}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

OUTPUT_FILE="$BACKUP_DIR/app_storage_${TIMESTAMP}.tar.gz"

docker compose -f "$COMPOSE_FILE_PATH" exec -T backend tar czf - -C /app storage > "$OUTPUT_FILE"

echo "Storage backup written to $OUTPUT_FILE"
