# NEXORA GROUP — Merge Certification Model

No pull request is considered safe merely because an AI reviewer says LGTM.

## Layer 1 — Existing CI

- backend compile
- Ruff
- pip-audit
- full pytest
- frontend typecheck
- frontend lint
- frontend Vitest
- frontend build
- Playwright E2E
- Docker Compose runtime smoke
- Azure Bicep compilation

## Layer 2 — AI

- PR-Agent + Groq
- deterministic review coverage
- Greptile
- additional available reviewers

## Layer 3 — Static security

- CodeQL
- Gitleaks
- GitGuardian
- Semgrep
- Trivy
- Checkov

## Layer 4 — Domain certification

- risk classifier
- Financial Guardian
- Authorization/RBAC regression guard
- database migration guardian
- property-based accounting tests

## Layer 5 — Runtime

- Schemathesis OpenAPI fuzzing
- OWASP ZAP dynamic baseline

## Layer 6 — Supply chain

- dependency audits
- Trivy
- SBOM/SPDX with Syft
- immutable SHAs for review-critical Actions

## Risk levels

### R1
Documentation / low-risk metadata.

### R2
Normal application code.

### R3
API or infrastructure.

### R4
Financial, authorization, database migration, or very large change.

R4 invokes the strongest applicable suite.

## Accounting invariants

The canonical definitions remain in `AGENTS.md` and `docs/ACCOUNTING.md`.

This certification workflow does not replace those documents. It enforces them.
