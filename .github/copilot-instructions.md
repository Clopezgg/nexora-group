# NEXORA GROUP — AI Code Review Policy

Before reviewing or proposing code, read:

1. `AGENTS.md`
2. `docs/MASTER_PLAN.md`
3. `docs/ACCOUNTING.md`
4. `docs/RBAC.md`
5. `docs/REQUIREMENTS_TRACEABILITY.md`

NEXORA is an enterprise construction ERP.

## Review priority

Prioritize, in order:

1. financial correctness;
2. tenant/company isolation;
3. RBAC and authorization;
4. transaction integrity;
5. concurrency and idempotency;
6. fiscal-period correctness;
7. database migration safety;
8. API contract regressions;
9. runtime security;
10. frontend correctness.

Do not report cosmetic issues unless they create a real defect.

## Non-negotiable rules

- Treasury is the only owner of real cash.
- Projects never own cash.
- General Ledger is the accounting source of truth.
- Every AccountingDocument must satisfy debit == credit.
- POSTED documents are immutable.
- Corrections use reversal/correction flows.
- All accounting creation goes through the central Posting Engine.
- `effective_date` selects the economic/fiscal period.
- `posted_at` is only technical audit time.
- Configured fiscal-calendar gaps fail closed.
- CLOSED fiscal periods reject postings.
- Cross-company references are forbidden.
- New mutation endpoints require explicit authorization.
- Existing permission guards must never disappear silently.
- No production data may be hard-coded.
- No workflow may make CI green by suppressing a real failure.

A review is incomplete if material parts of the diff were excluded.
