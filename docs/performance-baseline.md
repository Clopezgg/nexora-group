# NEXORA performance hardening baseline

## Observed architectural bottlenecks before hardening

- Azure Container Apps backend configured for `minReplicas: 0`, allowing scale-to-zero cold starts.
- Backend container allocated only `0.25` vCPU and `0.5Gi` RAM.
- Dashboard summary aggregates six months of accounting movements in Python after fetching journal rows.
- Frontend route table eagerly imports nearly every application module, increasing initial bundle parse/evaluation cost.
- Treasury waits for company discovery before starting company-scoped queries.
- Notification polling runs every 30 seconds.

## Hardening goals

- Remove avoidable cold-start latency from the normal user journey.
- Keep production backend resource usage modest while avoiding starvation.
- Push accounting aggregation to PostgreSQL where possible.
- Split frontend modules by route so users download/execute only what is needed initially.
- Preserve accounting, RBAC, company isolation, scope rules and HNL/multi-currency behavior.

## Verification

Changes must be validated by GitHub Actions, Azure deployment, `/api/healthz`, `/api/readyz` and browser/network timing checks after deployment.
