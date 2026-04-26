# Changelog

All notable project changes should be recorded here.

This project is in active development preview. Public versioning and release cadence are not yet stable.

## Unreleased

### Added

- Public project governance files and GitHub contribution templates.
- Documentation index for architecture, runtime, and remediation notes.
- Dependabot configuration for Python, npm, Docker, Docker Compose, and GitHub Actions.
- CI coverage for Python, frontend, and dependency audit checks.
- Local `make check` quality gate and Docker Compose smoke helper scripts.
- Security model, local quickstart, release process, maintainer guide, artifact protocol RFC, and maintainability refactor plan.
- CodeQL workflow and Compose config validation in CI.
- CODEOWNERS for default ownership of high-risk areas.

### Changed

- Clarified the open-source project status and contribution expectations.
- Contribution docs now point contributors to the same local checks used by CI.

### Security

- Added a security policy and reporting guidance.
- Documented runtime-control, generated-code, Docker socket, and preview trust boundaries.
