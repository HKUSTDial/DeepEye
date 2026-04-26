#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_STACK=0

usage() {
  cat <<'USAGE'
Usage: scripts/smoke-compose.sh [--start]

Validates the Docker Compose configuration. With --start, builds and starts the
gateway dependency chain, then checks backend-api and runtime-control health
from inside their containers.

Use --start only in a local environment with a configured .env and Docker access.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start)
      START_STACK=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy env.example to .env and update local values first." >&2
  exit 1
fi

echo "==> Validate Docker Compose config"
docker compose config --quiet

if [[ "$START_STACK" -ne 1 ]]; then
  echo "==> Compose config is valid"
  exit 0
fi

echo "==> Start gateway dependency chain"
docker compose up -d --build gateway

echo "==> Check backend-api health"
docker compose exec -T backend-api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=10)"

echo "==> Check runtime-control health"
docker compose exec -T runtime-control python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health', timeout=10)"

echo "==> Compose smoke test passed"
