# NEXORA Performance Hardening

This workstream targets production latency without changing financial semantics.

Targets:
- Avoid backend scale-to-zero cold starts for interactive production usage.
- Reduce initial frontend JavaScript via route-level lazy loading.
- Aggregate dashboard accounting metrics in PostgreSQL instead of iterating movement rows in Python.
- Preserve RBAC, company isolation, CENTRAL/GENERAL/PROJECT scope rules, double-entry accounting and HNL/multi-currency behavior.
- Validate through CI, E2E, Azure deployment, health/ready endpoints and browser timing.
