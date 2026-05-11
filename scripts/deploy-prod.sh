#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f deploy/compose.prod.env ]]; then
  echo "Missing deploy/compose.prod.env"
  echo "Copy deploy/compose.prod.env.example and fill the real values first."
  exit 1
fi

if [[ ! -f deploy/backend.prod.env ]]; then
  echo "Missing deploy/backend.prod.env"
  echo "Copy deploy/backend.prod.env.example and fill the real values first."
  exit 1
fi

set -a
source deploy/compose.prod.env
set +a

docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml build
docker compose --env-file deploy/compose.prod.env -f docker-compose.prod.yml up -d

echo "Waiting for backend health..."
for _ in {1..30}; do
  if curl -fsS "https://${API_DOMAIN}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

curl -fsS "https://${API_DOMAIN}/health"
curl -fsS "https://${API_DOMAIN}/health/worker"

echo
echo "Run docs/POST_DEPLOY_SMOKE.md next."
