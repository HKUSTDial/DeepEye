#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUN_PYTHON=1
RUN_FRONTEND=1
RUN_VIDEO_PREVIEW=1
RUN_AUDIT=1
INSTALL=0

usage() {
  cat <<'USAGE'
Usage: scripts/check.sh [options]

Runs the same quality gates used by GitHub Actions.

Options:
  --install           Install dependencies first (uv sync, npm ci)
  --python-only       Run only backend/core checks
  --frontend-only     Run only frontend checks
  --video-only        Run only video preview app checks
  --audit-only        Run only dependency audits
  --no-audit          Skip dependency audits
  -h, --help          Show this help

Environment:
  DEEPEYE_UV_CACHE    uv cache directory (default: existing uv default)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install)
      INSTALL=1
      ;;
    --python-only)
      RUN_PYTHON=1
      RUN_FRONTEND=0
      RUN_VIDEO_PREVIEW=0
      RUN_AUDIT=0
      ;;
    --frontend-only)
      RUN_PYTHON=0
      RUN_FRONTEND=1
      RUN_VIDEO_PREVIEW=0
      RUN_AUDIT=0
      ;;
    --video-only)
      RUN_PYTHON=0
      RUN_FRONTEND=0
      RUN_VIDEO_PREVIEW=1
      RUN_AUDIT=0
      ;;
    --audit-only)
      RUN_PYTHON=0
      RUN_FRONTEND=0
      RUN_VIDEO_PREVIEW=0
      RUN_AUDIT=1
      ;;
    --no-audit)
      RUN_AUDIT=0
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

uv_cmd=(uv)
if [[ -n "${DEEPEYE_UV_CACHE:-}" ]]; then
  uv_cmd+=(--cache-dir "$DEEPEYE_UV_CACHE")
fi

step() {
  printf '\n==> %s\n' "$*"
}

if [[ "$INSTALL" -eq 1 ]]; then
  step "Install Python workspace dependencies"
  (cd "$ROOT_DIR" && "${uv_cmd[@]}" sync --all-groups)
fi

if [[ "$RUN_PYTHON" -eq 1 ]]; then
  step "Run Python lint baseline"
  (cd "$ROOT_DIR" && "${uv_cmd[@]}" run ruff check packages/core/deepeye/workflows packages/core/tests packages/backend/app/test)

  step "Run backend/core tests"
  (cd "$ROOT_DIR" && "${uv_cmd[@]}" run pytest packages/backend/app/test packages/core/tests -q)
fi

if [[ "$RUN_FRONTEND" -eq 1 ]]; then
  if [[ "$INSTALL" -eq 1 ]]; then
    step "Install frontend dependencies"
    (cd "$ROOT_DIR/packages/frontend" && npm ci)
  fi

  step "Run frontend lint"
  (cd "$ROOT_DIR/packages/frontend" && npm run lint)

  step "Run frontend tests"
  (cd "$ROOT_DIR/packages/frontend" && npm test -- --maxWorkers=1 --no-file-parallelism)

  step "Build frontend"
  (cd "$ROOT_DIR/packages/frontend" && npm run build)
fi

if [[ "$RUN_VIDEO_PREVIEW" -eq 1 ]]; then
  if [[ "$INSTALL" -eq 1 ]]; then
    step "Install video preview app dependencies"
    (cd "$ROOT_DIR/docker/video-preview-app" && npm ci)
  fi

  step "Build video preview app"
  (cd "$ROOT_DIR/docker/video-preview-app" && npm run build)
fi

if [[ "$RUN_AUDIT" -eq 1 ]]; then
  step "Audit Python dependencies"
  requirements_file="${TMPDIR:-/tmp}/deepeye-check-requirements.txt"
  (cd "$ROOT_DIR" && "${uv_cmd[@]}" export --all-packages --all-extras --all-groups --no-hashes --no-emit-workspace --frozen --output-file "$requirements_file" >/dev/null)
  (cd "$ROOT_DIR" && "${uv_cmd[@]}" run --with pip-audit pip-audit -r "$requirements_file" --format columns --progress-spinner off)

  step "Audit frontend dependencies"
  (cd "$ROOT_DIR/packages/frontend" && npm audit --registry=https://registry.npmjs.org --audit-level=high)

  step "Audit video preview dependencies"
  (cd "$ROOT_DIR/docker/video-preview-app" && npm audit --registry=https://registry.npmjs.org --audit-level=high)
fi

step "All selected checks passed"
