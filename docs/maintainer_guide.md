# Maintainer Guide

This guide captures expectations for maintainers while DeepEye is in active
development preview.

## Review Priorities

Review pull requests in this order:

1. Security impact
2. Behavior changes and regressions
3. Test coverage
4. Documentation updates
5. Code style and maintainability

Security-sensitive areas include:

- authentication and cookies
- datasource credentials
- generated-code execution
- sandbox and Docker runtime control
- workflow artifact persistence
- preview routing

## Required Checks

Before merging, the relevant subset of these checks should pass:

```bash
make check
make compose-config
```

Use `make security-scan` when optional local scanners are installed.

## PR Labels

Suggested labels:

- `type: bug`
- `type: feature`
- `type: docs`
- `type: security`
- `type: refactor`
- `area: backend`
- `area: frontend`
- `area: core`
- `area: docs`
- `good first issue`
- `help wanted`

## Branch Hygiene

- Keep `master` releasable.
- Delete merged work branches.
- Prefer short-lived feature branches.
- Avoid mixing dependency updates with unrelated feature work.

## Security Handling

Do not discuss exploitable details in public issues or PRs. Use the repository
security advisory flow or a private maintainer channel.
