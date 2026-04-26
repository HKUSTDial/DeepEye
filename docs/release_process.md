# Release Process

DeepEye does not have stable public releases yet. Until the first tagged
release, the default branch is the supported development preview.

## Versioning

The intended release scheme is SemVer:

- `MAJOR`: breaking public API, workflow schema, or deployment changes
- `MINOR`: backward-compatible features
- `PATCH`: bug fixes, security fixes, and documentation corrections

Before `1.0.0`, minor versions may still include breaking changes. Breaking
changes must be called out in release notes.

## Release Readiness Checklist

- [ ] `make check` passes locally.
- [ ] GitHub Actions CI is green on the release commit.
- [ ] Dependency audit has no known high or critical findings.
- [ ] Container images are scanned before publication.
- [ ] Database migration notes are documented.
- [ ] `CHANGELOG.md` is updated.
- [ ] `README.md` quickstart still matches the released stack.
- [ ] Security-sensitive changes are reviewed.

## Planned Artifacts

Future releases should publish:

- Git tag and GitHub Release notes
- Docker images for backend, frontend, sandbox, dashboard runtime, and video preview
- SBOMs for container images
- Checksums for release artifacts

## Changelog Policy

Use these groups:

- Added
- Changed
- Fixed
- Removed
- Security

Keep entries user-facing. Internal refactors belong in release notes only when
they affect operators, contributors, or extension authors.
