---
applyTo: "infra/**/*.bicep,.github/workflows/**/*.yml,backend/Dockerfile,docker-compose.yml"
---

# Infrastructure / CI Security Rules

- Never deploy Azure from review CI.
- `az bicep build` and `what-if` are allowed; provisioning is not.
- Do not use `pull_request_target` to execute untrusted PR code.
- Do not use `permissions: write-all`.
- Third-party GitHub Actions should be pinned to immutable commit SHAs.
- Never pipe downloaded scripts directly into a privileged shell.
- Do not expose secrets to fork pull requests.
- Keep workflow permissions minimal.
- Container images and dependencies must pass vulnerability scanning.
