---
applyTo: "backend/app/api/routes/**/*.py,backend/app/services/permission_service.py,backend/app/core/security.py"
---

# Authorization Review Rules

For every state-changing endpoint verify:

- authentication occurs;
- `require_permission()` or an equivalent explicit authorization layer is present;
- company/tenant scope is validated;
- project scope is validated where applicable;
- a user cannot reference another company's objects by UUID;
- Protected Edit/lifecycle rules apply to POST/PUT/PATCH/DELETE;
- errors fail closed;
- authorization is performed server-side;
- frontend visibility is never treated as authorization.
