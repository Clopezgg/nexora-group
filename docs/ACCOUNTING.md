# NEXORA GROUP — Accounting, Posting Engine & Invariant Registry

Este documento es el contrato del núcleo contable construido por el Track 1
(Foundation). Cualquier track de dominio (Treasury, AP, AR, Procurement,
Inventory, ...) que necesite generar un asiento contable debe leer esta
sección antes de escribir código — no debe reinventar el motor.

## Posting Engine — contrato

Módulo: `backend/app/services/posting_service.py`.

**Ningún módulo de dominio construye `AccountingDocument`/`JournalLine` a
mano.** Siempre se llama a:

```python
from app.services import posting_service

document = posting_service.post_manual(
    db,
    company_id=...,
    document_type_code="JRN",   # tu track registra su propio DocumentType
    scope="CENTRAL" | "GENERAL" | "PROJECT",
    project_id=... | None,       # None salvo scope=PROJECT
    currency_code="HNL",
    lines=[
        posting_service.JournalLineInput(account_id=..., debit_amount=Decimal("100")),
        posting_service.JournalLineInput(account_id=..., credit_amount=Decimal("100")),
    ],
    description="...",
    source_type="remittance",    # opcional: enlaza al documento de negocio origen
    source_id=remittance.id,
)
```

Qué garantiza el servicio (y qué NO hace):

- Valida doble partida (`INV-ACC-001`), `OperationScope` (`INV-OPS-*`) y
  período fiscal abierto (`INV-ACC-003`) **antes** de tocar la base de
  datos. Si algo falla, no se persiste nada.
- Numera el documento vía `NumberSequence` (concurrency-safe, `SELECT ...
  FOR UPDATE`, nunca `MAX()+1`).
- Por defecto persiste y hace `commit()`. Los dominios que necesitan
  componer posting + documento de negocio + idempotencia en una sola unidad
  pasan `commit=False`; en ese modo el servicio hace `flush()` y el caller
  confirma o revierte la transacción completa. Treasury/AP/AR usan este modo
  en toda mutación que mueve efectivo.
- **NO decide qué cuentas usar.** Eso es responsabilidad del módulo de
  dominio (Treasury sabe qué cuenta de banco corresponde a una remesa; AP
  sabe qué cuenta de proveedores usar). Si tu caso es un par
  débito/crédito simple y estable, puedes registrar una fila en
  `PostingRule` (company_id + document_type_code + scope + category ->
  debit_account_id/credit_account_id) y resolverla tú mismo antes de
  llamar a `post_manual` con las líneas ya armadas — este track no incluye
  todavía un `post_via_rule()` automático porque ningún dominio real lo
  necesitó aún; añádelo si tu caso lo amerita, manteniendo el mismo
  contrato de validación.
- Reversal: `posting_service.reverse_document(db, document_id=..., reason=...)`.
  El original **nunca se muta** (ni sus montos ni sus líneas); solo
  transiciona `POSTED -> REVERSED` y queda enlazado al nuevo documento de
  reversal (tipo `ANU`). Intentar revertir algo que no está `POSTED` lanza
  `ImmutableDocumentError` (`NXR-ACCOUNTING-004`, HTTP 409).

## Dimensiones contables — deuda intencional

`JournalLine` tiene FKs reales a `project_id` y `cost_center_id` (ya
existen como tablas). Las dimensiones que todavía no tienen tabla propia
(supplier, customer, asset, warehouse) viven en `extra_dimensions`
(JSONB) hasta que el track dueño construya la entidad real. **Cuando eso
ocurra, ese track debe migrar la dimensión a una columna FK real** — no
dejarla en JSONB indefinidamente. Registrado aquí para que no se olvide.

## Number sequences

`backend/app/services/numbering_service.py`. Formato:
`{PREFIX}-{AÑO}-{consecutivo de 6 dígitos}` (p.ej. `JRN-2026-000001`).
Cada `document_type_code` nuevo que un track agregue debe registrar una
fila en `document_types` (código + prefijo) antes de poder numerar
documentos de ese tipo — ver `app/repositories/catalog_repository.py` para
el patrón de seed idempotente.

## Idempotency — contrato

Módulo: `backend/app/services/idempotency_service.py`.

```python
from app.services import idempotency_service

outcome = idempotency_service.begin(db, key=idem_key, command="create_remittance", payload=payload_dict)
if outcome.is_replay:
    return outcome.record.result  # ya se ejecutó antes con este mismo payload
# ... ejecutar la operación real (puede incluir un posting_service.post_manual) ...
idempotency_service.complete(db, outcome.record, result={...}, entity_type="remittance", entity_id=entity.id)
db.commit()
```

La operación incluida entre `begin()` y `complete()` debe llamar al Posting
Engine y a su servicio de dominio con `commit=False`; ningún commit intermedio
puede dejar un posting confirmado con el registro idempotente aún `PENDING`.

`begin()` con la misma key y payload distinto lanza `IdempotencyConflictError`
(`NXR-IDEMPOTENCY-001`, HTTP 409) — mapeado automáticamente si tu endpoint
deja que la excepción se propague (ver `app/api/error_handlers.py`).

## RBAC — motor de permisos

Ver `docs/RBAC.md` para el catálogo de roles y el contrato de
`app.services.permission_service` (`require_permission`,
`assert_company_access`).

## Catálogo de invariantes (orden maestra §130)

| ID | Descripción | Implementado por | Test | Estado |
|---|---|---|---|---|
| INV-ACC-001 | Débitos = Créditos en cada AccountingDocument | `posting_service._validate_balance` | `test_posting_engine.py::test_unbalanced_journal_entry_is_rejected` | ✅ VERIFIED |
| INV-ACC-002 | Documento posted es inmutable | `posting_service.reverse_document` / `assert_document_is_mutable_or_raise` | `test_posting_engine.py::test_reverse_preserves_original_and_swaps_debit_credit`, `::test_reverse_of_already_reversed_document_is_rejected` | ✅ VERIFIED |
| INV-ACC-003 | Período CLOSED no admite posting nuevo | `posting_service._assert_fiscal_period_open` | `test_fiscal_period_closed.py` | ✅ VERIFIED |
| INV-TRE-001 | El dinero real pertenece a Treasury | — (Track A) | — | NOT_STARTED — dueño: Track A |
| INV-TRE-002 | Project nunca posee saldo monetario | — (Track A/B) | — | NOT_STARTED — dueño: Track A + B |
| INV-OPS-001 | scope=CENTRAL ⇒ project_id NULL | CHECK constraint `ck_accounting_documents_operation_scope` + `posting_service._validate_scope` | `test_operation_scope_constraint.py::test_check_constraint_rejects_central_scope_with_project` | ✅ VERIFIED |
| INV-OPS-002 | scope=GENERAL ⇒ project_id NULL | ídem | `test_posting_engine.py::test_general_scope_with_project_id_is_rejected` | ✅ VERIFIED |
| INV-OPS-003 | scope=PROJECT ⇒ project_id requerido | ídem | `test_operation_scope_constraint.py::test_check_constraint_rejects_project_scope_without_project`, `test_posting_engine.py::test_project_scope_without_project_id_is_rejected` | ✅ VERIFIED |
| INV-CTX-001 | Una operación con project_id=NULL nunca muta ActiveUIContext | Independencia arquitectónica: `user_context` no se toca desde `posting_service` | `test_active_context_independence.py` | ✅ VERIFIED |
| INV-BUD-001 | Gasto GENERAL no consume Project Budget | — (Track B) | — | NOT_STARTED — dueño: Track B |
| INV-BUD-002 | Commitments de Project siguen budget policy | — (Track B) | — | NOT_STARTED — dueño: Track B |
| INV-PROC-001 | Diferencias de 3-way match no desaparecen silenciosamente | — (Track C) | — | NOT_STARTED — dueño: Track C |
| INV-INV-001 | Stock no se duplica silenciosamente | — (Track C) | — | NOT_STARTED — dueño: Track C |
| INV-INV-002 | Issue a Project reduce warehouse stock | — (Track C) | — | NOT_STARTED — dueño: Track C |
| INV-IDEM-001 | Replay exacto no duplica la transacción | `idempotency_service.begin` | `test_idempotency_service.py::test_same_key_and_payload_replays_completed_result` | ✅ VERIFIED |
| INV-IDEM-002 | Misma key + payload distinto ⇒ rechazo | `idempotency_service.begin` | `test_idempotency_service.py::test_same_key_different_payload_conflicts` | ✅ VERIFIED |
| INV-AUD-001 | Historial posted no se elimina destructivamente | Sin `DELETE` expuesto sobre `AccountingDocument`/`JournalLine` en ningún repositorio/servicio de este track | (cubierto indirectamente por INV-ACC-002; falta un test de auditoría dedicado cuando el Track G construya el módulo de Audit) | 🔶 IN_PROGRESS — dueño: Track G |
| INV-SOD-001 | Segregación de funciones configurada no se puede bypassear | — (Track G, motor de workflow) | — | NOT_STARTED — dueño: Track G |
| INV-COMP-001 | Aislamiento de company | `permission_service.assert_company_access` + `RolePermission.company_scope` | `test_rbac_and_company_isolation.py` (4 tests) | ✅ VERIFIED |

**Nota de honestidad**: "VERIFIED" aquí significa que el invariante tiene
constraint/servicio real + test real pasando dentro de este track. La
verificación end-to-end del coordinador (integración a
`feat/nexora-greenfield`) es la que actualiza el estado equivalente en
`docs/REQUIREMENTS_TRACEABILITY.md` — este documento describe lo que el
Track 1 construyó y probó por su cuenta, en su propio worktree.
