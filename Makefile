.PHONY: check check-install check-python check-frontend check-video audit compose-config compose-smoke security-scan

check:
	scripts/check.sh

check-install:
	scripts/check.sh --install

check-python:
	scripts/check.sh --python-only

check-frontend:
	scripts/check.sh --frontend-only

check-video:
	scripts/check.sh --video-only

audit:
	scripts/check.sh --audit-only

compose-config:
	scripts/smoke-compose.sh

compose-smoke:
	scripts/smoke-compose.sh --start

security-scan:
	scripts/security-scan.sh
