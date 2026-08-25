# Audit Trail — Track G (Workflow / Approvals / Audit / Notifications)

Cierra `NXR-REQ-0090` (`docs/MASTER_PLAN.md`, bloque PLATFORM) y resuelve
`DEFERRED-FINAL-014` (no existía mecanismo de audit log en el sistema).
Ver `docs/superpowers/specs/2026-08-25-track-g-workflow-audit-design.md`
para el razonamiento completo de diseño.

## Ruling: sin framework genérico de state machine

Track G **no** migra los dominios existentes (AP, Treasury, Procurement,
etc.) a un motor de estados genérico. Cada dominio conserva exactamente su
propia lógica de transición ya probada (`ap_service.approve_supplier_invoice`,
`procurement_service.approve_purchase_order`, etc.) — este task solo agrega
un log de auditoría compartido, invocado explícitamente. Nunca un hook
oculto de SQLAlchemy, nunca un cambio de firma en una función de servicio
existente.

## El modelo `AuditLog`

`app/models/audit.py`, tabla `audit_logs`. **Append-only**: ningún
servicio ni ruta hace `UPDATE` o `DELETE` sobre una fila ya insertada — la
única operación permitida después de `INSERT` es `SELECT`. Mismo criterio
de disciplina que `AccountingDocument` (orden maestra §8, contabilidad).
Deliberadamente no usa `TimestampMixin` (su `onupdate` haría de
`updated_at` una mentira en una tabla que nunca se actualiza).

Columnas:

| Columna           | Tipo               | Notas                                         |
|-------------------|--------------------|------------------------------------------------|
| `id`               | UUID PK            |                                                |
| `actor_user_id`    | UUID, FK `users.id`, nullable | `SET NULL` en cascada — nullable para acciones de sistema |
| `action`           | str(150)           | `"<dominio>.<entidad>.<verbo>"`, ej. `"ap.supplier_invoice.approve"` |
| `entity_type`      | str(100)           | ej. `"ap.supplier_invoice"`                   |
| `entity_id`        | UUID               | fila afectada                                  |
| `company_id`       | UUID, FK `companies.id` | obligatorio — aislamiento INV-COMP-001    |
| `project_id`       | UUID, FK `projects.id`, nullable | solo si la entidad es de un proyecto |
| `before`           | JSONB, nullable    | **solo los campos que valen la pena auditar**, nunca un dump crudo del modelo ni secretos/credenciales |
| `after`            | JSONB, nullable    | idem                                           |
| `correlation_id`   | str(100)           | ver abajo                                      |
| `created_at`       | timestamptz, server_default now() |                                |

## `audit_service.record(...)`

`app/services/audit_service.py`:

```python
def record(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    correlation_id: str,
    project_id: uuid.UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog
```

Internamente hace `audit_repository.create(...)`, que solo `db.add()` +
`db.flush()` — nunca `db.commit()` por sí mismo. El caller (siempre la
ruta) controla el commit, igual que con cualquier otra escritura en este
codebase.

## Call site: la ruta, no el servicio

Verificado contra el código real (`app/api/routes/ap.py`):
`assert_company_access` ya se invoca en el handler de la ruta usando
`user` (de `require_permission`) y la entidad ya resuelta ahí mismo. Las
funciones de servicio (`ap_service.approve_supplier_invoice(db,
invoice_id=...)`) no reciben `actor_user_id` hoy y este task no le agrega
ese parámetro — eso sería exactamente el refactor grande y riesgoso de
código ya probado que la Ruling de scope rechaza. En cambio, cada ruta
instrumentada llama a `audit_service.record` justo después de que su
llamada de servicio tiene éxito, usando el `user.id` y la entidad
resuelta que ya tiene disponibles.

Patrón real (`app/api/routes/ap.py:approve_supplier_invoice`):

```python
@router.post("/supplier-invoices/{invoice_id}/approve", response_model=SupplierInvoiceResponse)
def approve_supplier_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_invoice", "approve")),
    correlation_id: str = Depends(get_correlation_id),
) -> SupplierInvoiceResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(db, user_id=user.id, resource="ap.supplier_invoice", action="approve", company_id=invoice.company_id)
    before_status = invoice.status
    invoice = ap_service.approve_supplier_invoice(db, invoice_id=invoice_id)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="ap.supplier_invoice.approve",
        entity_type="ap.supplier_invoice",
        entity_id=invoice.id,
        company_id=invoice.company_id,
        project_id=invoice.project_id,
        before={"status": before_status},
        after={"status": invoice.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return SupplierInvoiceResponse.model_validate(invoice, from_attributes=True)
```

**Nota de commit**: varias funciones de servicio de dominio (ej.
`ap_service.approve_supplier_invoice`, `procurement_service.approve_purchase_order`)
ya hacen `db.commit()` internamente. Cuando eso ocurre, la ruta agrega un
`db.commit()` propio después de `audit_service.record(...)` para
persistir la fila de auditoría (que solo quedó `flush()`eada, no
committeada, por la mutación de dominio). En rutas con soporte de
idempotencia (`Idempotency-Key`), el `audit_service.record(...)` se
inserta en la misma transacción que la mutación de dominio y el registro
de idempotencia, y el único `db.commit()` al final del bloque los
persiste atómicamente juntos — nunca se audita un replay de idempotencia
(el `return` temprano por `outcome.is_replay` ocurre antes de llegar al
audit call, correcto: un replay no es una mutación nueva).

## `correlation_id`

`app/api/deps_correlation.py`: dependencia FastAPI `get_correlation_id`
que lee el header `X-Correlation-Id` si el cliente lo manda, o genera un
`uuid4()` nuevo por request si no. Se pasa explícitamente a cada
`audit_service.record(...)` de esa misma request. Task 2/Task 3
(`ApprovalRequest`/`Notification`) reutilizan la misma dependencia — no se
crea un segundo mecanismo de correlación.

## API: `GET /api/audit`

`app/api/routes/audit.py`. Filtra por `companyId` (obligatorio),
`entityType` y `entityId` (opcionales). Aislamiento de company real vía
`assert_company_access(resource="audit.log", action="read", ...)` —
`INV-COMP-001`. Permiso `audit.log`/`read` (`app/repositories/permission_repository.py`):
- `Administrator`: `SCOPE_ANY` (automático, vía la lista base — mismo
  criterio que cualquier otro permiso base).
- `Auditor`: `SCOPE_ANY` explícito (coherente con el resto de los grants
  de este rol — un auditor necesita ver auditoría de todas las
  companies).
- `Finance Manager`: `SCOPE_OWN` (solo las companies asignadas vía
  `UserCompanyAccess`).

**Nota de test**: el test de aislamiento de company
(`tests/test_audit.py::test_company_access_blocks_cross_company_audit_log`)
usa el rol `Finance Manager`, no `Auditor`, porque `Auditor` es `SCOPE_ANY`
para este permiso (igual que para todos los demás que ya tiene) — usar
`Auditor` ahí no probaría aislamiento de ninguna forma, el request
pasaría igual.

## Dominios instrumentados (Task 1)

| Dominio | Acción | Ruta |
|---------|--------|------|
| AP | `ap.supplier_invoice.approve` | `POST /api/ap/supplier-invoices/{id}/approve` |
| AP | `ap.supplier_payment.create` | `POST /api/ap/supplier-invoices/{id}/payments` |
| Treasury | `treasury.cash_closing.approve` | `POST /api/treasury/cash-closings/{id}/approve` |
| Treasury | `treasury.remittance.create` | `POST /api/treasury/remittances` |
| Procurement | `procurement.purchase_order.approve` | `POST /api/procurement/purchase-orders/{id}/approve` |

**Desviación deliberada respecto al plan original**: el plan original
mencionaba instrumentar "la ruta de aprobación de remesas" (remittance-
approval) en Treasury. Verificado contra `app/models/treasury.py` y
`app/api/routes/treasury.py`: `Remittance` no tiene columna `status` ni
ningún paso de aprobación posterior a su creación (siempre
`scope=CENTRAL`, se contabiliza inmediatamente al crearse vía
`posting_service`) — no existe una ruta "remittance-approval" en este
codebase, ni tiene sentido de dominio que exista una. La mutación
auditable real para esa entidad es su creación
(`POST /api/treasury/remittances`), así que se instrumentó esa en su
lugar.

## Dominios NO instrumentados todavía (backlog honesto)

Ningún otro dominio tiene audit log todavía. Esto es deliberado e
incremental (ver design doc), no un olvido:

- **Project Control** (WBS, Presupuestos, Órdenes de cambio, Avances) —
  `NOT_STARTED`.
- **Enterprise Resources** (Fixed Assets, Equipment, Workforce) —
  `NOT_STARTED`.
- **Commercial** (CRM: Leads, Oportunidades, Cotizaciones, Contratos de
  venta, AR) — `NOT_STARTED`.
- **Construction Control** (Documents/Evidence, RFI/Submittals, Daily
  Site Reports, Quality, Safety) — `NOT_STARTED`.
- Dentro de Financial Core: General Ledger (asientos manuales / reversal),
  Transfers, General Expenses, Fund Restrictions, Bank Reconciliation
  (match/exclude) tampoco están instrumentados todavía — solo se cubrieron
  las rutas de aprobación/creación de mayor valor de auditoría de este
  task (AP approve/pay, Treasury cash-closing approve + remittance
  create, Procurement PO approve).

Un futuro task puede cerrar estos dominios uno por uno reutilizando
exactamente el patrón de esta página: leer la ruta real, agregar
`correlation_id: str = Depends(get_correlation_id)`, llamar
`audit_service.record(...)` justo después de la llamada de servicio que
tiene éxito, y asegurar que haya un `db.commit()` después si el servicio
de dominio ya committeó internamente. No se requiere ningún cambio a
`AuditLog`, `audit_service`, ni al endpoint `GET /api/audit` para agregar
un dominio nuevo.

## Testing

- `tests/test_audit.py`: modelo append-only, aislamiento de company.
- `tests/test_ap_ar.py`: `test_approving_supplier_invoice_creates_audit_log_entry`,
  `test_paying_supplier_invoice_creates_audit_log_entry`.
- `tests/test_treasury_operations.py`: `test_approving_cash_closing_creates_audit_log_entry`,
  `test_registering_remittance_creates_audit_log_entry`.
- `tests/test_procurement_flow.py`: `test_approving_purchase_order_creates_audit_log_entry`.
- `frontend/tests/AuditLogPage.test.tsx`: página real contra la API real
  (mockeada a nivel de `fetch`), nunca datos fabricados.

## Frontend

`frontend/src/features/audit/AuditLogPage.tsx` — ruta `/control/auditoria`
(la entrada de navegación "Auditoría" ya existía reservada en
`navigation.ts` bajo la sección "Control"; no se inventó una sección
Plataforma nueva). Filtros: tipo de entidad (texto libre, ya que
`entity_type` es un string dinámico por dominio) y rango de fechas
(client-side sobre `createdAt`). `frontend/src/services/auditService.ts`,
`frontend/src/types/audit.ts`.
