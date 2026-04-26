#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FOUND_TOOL=0

step() {
  printf '\n==> %s\n' "$*"
}

if command -v gitleaks >/dev/null 2>&1; then
  FOUND_TOOL=1
  step "Run gitleaks secret scan"
  (cd "$ROOT_DIR" && gitleaks detect --source . --redact --verbose)
else
  echo "Skipping gitleaks: command not found"
fi

if command -v trivy >/dev/null 2>&1; then
  FOUND_TOOL=1
  step "Run Trivy config scan"
  (cd "$ROOT_DIR" && trivy config --severity HIGH,CRITICAL --exit-code 1 .)
else
  echo "Skipping trivy: command not found"
fi

if [[ "$FOUND_TOOL" -eq 0 ]]; then
  echo "No optional security scanners installed. Install gitleaks and/or trivy to use this script."
fi
