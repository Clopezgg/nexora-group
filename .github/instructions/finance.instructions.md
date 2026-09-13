---
applyTo: "backend/app/services/**/*posting*.py,backend/app/services/**/*financial*.py,backend/app/services/treasury*.py,backend/app/api/routes/accounting.py,backend/app/api/routes/ap.py,backend/app/api/routes/ar.py,backend/app/api/routes/assets.py,backend/app/models/accounting.py"
---

# Financial Review Rules

Treat every financial change as critical.

Verify:

- Debit equals credit.
- Zero-total journals are rejected.
- Negative line amounts are rejected.
- One line cannot contain both debit and credit.
- `effective_date` governs the fiscal period.
- `posted_at` never determines economic period.
- Posting into CLOSED periods is impossible.
- Calendar gaps fail closed.
- POSTED documents cannot be destructively updated/deleted.
- Reversal preserves the original and creates an opposite entry.
- Treasury remains the sole cash authority.
- No module constructs AccountingDocument/JournalLine directly outside the Posting Engine.
- Company/project/account/cost-center references belong to the same tenant.
- Posting and reversal operations remain safe under concurrency.
