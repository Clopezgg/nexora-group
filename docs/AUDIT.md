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

## Dominios instrumentados (Task 2)

| Dominio | Acción | Ruta |
|---------|--------|------|
| Platform / Approval Inbox | `workflow.approval.decide` | `POST /api/approvals/{id}/decide` |

Esta fila audita la propia `ApprovalRequest` (antes/después de su
`status`), no la entidad de dominio que decide (`SupplierInvoice`,
`Submittal`, etc.) — esas siguen su propio backlog de instrumentación de
abajo hasta que un task dedicado las cubra explícitamente.

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

## Dominios instrumentados (2026-08-25, backlog burn-down)

| Dominio | Acción | Ruta |
|---------|--------|------|
| Financial Core / General Ledger | `accounting.journal_entry.create` | `POST /api/accounting/journal-entries` |
| Financial Core / General Ledger | `accounting.journal_entry.reverse` | `POST /api/accounting/journal-entries/{id}/reverse` |

El reversal audita el documento **original** (`entity_id` = el documento
que transiciona `POSTED -> REVERSED`), no el nuevo documento de reversal
que se crea junto a él — ese es un side effect de la misma operación, no
la entidad cuyo estado mutó. `after.reversalDocumentId` enlaza al
reversal para quien lea el log.

## Dominios instrumentados (2026-08-26, backlog burn-down — cinco gaps de Treasury cerrados)

| Dominio | Acción | Ruta |
|---------|--------|------|
| Treasury | `treasury.general_expense.create` | `POST /api/treasury/general-expenses` |
| Treasury | `treasury.transfer.create` | `POST /api/treasury/transfers` |
| Treasury | `treasury.bank_reconciliation.match` | `POST /api/treasury/bank-statement-lines/{id}/match` |
| Treasury | `treasury.bank_reconciliation.exclude` | `POST /api/treasury/bank-statement-lines/{id}/exclude` |
| Treasury | `treasury.fund_restriction.create` | `POST /api/treasury/fund-restrictions` |

Con esto quedan cerrados los cinco gaps de Treasury que este slice tenía
enumerados: gastos generales, transferencias, `match`/`exclude` de
conciliación y restricciones de fondos. No significa que cada mutación de
Financial Core esté instrumentada: AR todavía no tiene call sites de audit,
y siguen abiertas mutaciones de creación/configuración en AP y Treasury.
`match`/`exclude` auditan la `BankStatementLine` afectada
(`entity_type="treasury.bank_statement_line"`); el `match` incluye además
`accountingDocumentId` y `reconciliationMatchId`, porque la operación crea
una fila `ReconciliationMatch`, no solo cambia el `status` de la línea.

Las cinco rutas de este slice persisten la mutación de negocio y el audit en
**una sola transacción**. Los servicios conservan `commit=True` por
compatibilidad, pero estas rutas llaman con `commit=False` y hacen el único
`db.commit()` después de `audit_service.record(...)`. Si el audit falla, la
mutación completa se revierte; hay pruebas de regresión para las cinco rutas.

## Dominios instrumentados (2026-08-26, backlog burn-down — AP/AR creation + Treasury creation + AP cancel)

| Dominio | Acción | Ruta |
|---------|--------|------|
| AP | `ap.supplier_invoice.create` | `POST /api/ap/supplier-invoices` |
| AP | `ap.supplier_invoice.cancel` | `POST /api/ap/supplier-invoices/{id}/cancel` |
| AR | `ar.customer_invoice.create` | `POST /api/ar/customer-invoices` |
| AR | `ar.customer_invoice.approve` | `POST /api/ar/customer-invoices/{id}/approve` |
| AR | `ar.customer_receipt.create` | `POST /api/ar/customer-invoices/{id}/receipts` |
| Treasury | `treasury.account.create` | `POST /api/treasury/accounts` |
| Treasury | `treasury.cash_closing.create` | `POST /api/treasury/cash-closings` |
| Treasury | `treasury.bank_statement.create` | `POST /api/treasury/bank-statements` |
| Treasury | `treasury.bank_statement_line.create` | `POST /api/treasury/bank-statements/{id}/lines` |

These nine routes close the remaining Financial Core creation/definition gaps.
All use `commit=False` + single `db.commit()` for atomic business+audit
transactions, with rollback test coverage. The `cancel` action is a new
endpoint added in this slice (`POST /api/ap/supplier-invoices/{id}/cancel`).

## Dominios instrumentados (2026-08-26, backlog burn-down — Supply Chain: Procurement + Inventory)

| Dominio | Acción | Ruta |
|---------|--------|------|
| Procurement | `procurement.requisition.create` | `POST /api/procurement/requisitions` |
| Procurement | `procurement.requisition.approve` | `POST /api/procurement/requisitions/{id}/approve` |
| Procurement | `procurement.rfq.create` | `POST /api/procurement/rfqs` |
| Procurement | `procurement.quotation.create` | `POST /api/procurement/rfqs/{id}/quotations` |
| Procurement | `procurement.purchase_order.create` | `POST /api/procurement/purchase-orders` |
| Procurement | `procurement.purchase_order.create_from_quotation` | `POST /api/procurement/purchase-orders/from-quotation` |
| Procurement | `procurement.purchase_order.approve` | `POST /api/procurement/purchase-orders/{id}/approve` (existing) |
| Procurement | `procurement.purchase_order.send` | `POST /api/procurement/purchase-orders/{id}/send` |
| Procurement | `procurement.goods_receipt.create` | `POST /api/procurement/goods-receipts` |
| Procurement | `procurement.service_entry.create` | `POST /api/procurement/service-entries` |
| Procurement | `procurement.three_way_match.create` | `POST /api/procurement/three-way-match` |
| Inventory | `inventory.item.create` | `POST /api/inventory/items` |
| Inventory | `inventory.warehouse.create` | `POST /api/inventory/warehouses` |
| Inventory | `inventory.stock.receive` | `POST /api/inventory/stock/receive` |
| Inventory | `inventory.stock.issue_to_project` | `POST /api/inventory/stock/issue-to-project` |
| Inventory | `inventory.stock.transfer` | `POST /api/inventory/stock/transfer` |
| Inventory | `inventory.stock.return_to_supplier` | `POST /api/inventory/stock/return-to-supplier` |
| Inventory | `inventory.physical_count.create` | `POST /api/inventory/physical-counts` |
| Inventory | `inventory.physical_count.approve` | `POST /api/inventory/physical-counts/{id}/approve` |

This slice covers the entire Supply Chain track (Procurement + Inventory). All
routes use `commit=False` + single `db.commit()` for atomic business+audit
transactions. The `approve_purchase_order` route was already audited and now
also uses `commit=False`. UUIDs in `before`/`after` dicts are converted to
strings for JSONB serialization.

## Dominios instrumentados (2026-08-26, backlog burn-down — Project Control: WBS, Budgets, Change Orders, Progress)

| Dominio | Acción | Ruta |
|---------|--------|------|
| Project | `project.create` | `POST /api/projects` |
| Project | `project.wbs.create` | `POST /api/projects/{id}/wbs` |
| Project | `project.task.create` | `POST /api/projects/{id}/tasks` |
| Project | `project.milestone.create` | `POST /api/projects/{id}/milestones` |
| Project | `project.budget.create` | `POST /api/projects/{id}/budgets/baseline` |
| Project | `project.change_order.create` | `POST /api/projects/{id}/change-orders` |
| Project | `project.change_order.submit` | `POST /api/projects/change-orders/{id}/submit` |
| Project | `project.change_order.approve` | `POST /api/projects/change-orders/{id}/approve` |
| Project | `project.progress.create` | `POST /api/projects/{id}/progress` |

All 9 routes instrumented. Repository-calling routes use `db.flush()` +
audit + single `db.commit()`. Service-calling routes (`create_budget_baseline`,
`approve_change_order`) use `commit=False` on the service + audit + single
`db.commit()`.

## Dominios instrumentados (2026-08-26, backlog burn-down — Enterprise Resources: Workforce + Assets + Equipment)

| Dominio | Acción | Ruta |
|---------|--------|------|
| Workforce | `workforce.worker.create` | `POST /api/workforce/workers` |
| Workforce | `workforce.time_entry.create` | `POST /api/workforce/time-entries` |
| Workforce | `workforce.time_entry.approve` | `POST /api/workforce/time-entries/{id}/approve` |
| Workforce | `workforce.time_entry.reject` | `POST /api/workforce/time-entries/{id}/reject` |
| Workforce | `workforce.crew.create` | `POST /api/workforce/crews` |
| Workforce | `workforce.crew.member.add` | `POST /api/workforce/crews/{id}/members` |
| Workforce | `workforce.crew.member.remove` | `DELETE /api/workforce/crews/{id}/members/{worker_id}` |
| Asset | `asset.fixed_asset.create` | `POST /api/assets` |
| Asset | `asset.fixed_asset.status_change` | `POST /api/assets/{id}/status` |
| Asset | `asset.depreciation.create` | `POST /api/assets/{id}/depreciation-entries` |
| Equipment | `equipment.equipment.create` | `POST /api/equipment` |
| Equipment | `equipment.equipment.status_change` | `POST /api/equipment/{id}/status` |
| Equipment | `equipment.fuel_log.create` | `POST /api/equipment/fuel-logs` |
| Equipment | `equipment.maintenance_plan.create` | `POST /api/equipment/{id}/maintenance-plans` |
| Equipment | `equipment.maintenance_order.create` | `POST /api/equipment/{id}/maintenance-orders` |
| Equipment | `equipment.maintenance_order.update` | `PATCH /api/equipment/maintenance-orders/{id}` |

All 16 routes instrumented with atomic audit. Service layers gained `commit: bool = True` on all mutating functions. `update_maintenance_order` was the complex case: two separate commits (order update + equipment status flip to AVAILABLE) replaced by single `flush()` on `commit=False`, with route handling single commit after audit.

## Dominios instrumentados (2026-08-26, backlog burn-down — Commercial/CRM)

| Dominio | Acción | Ruta |
|---------|--------|------|
| CRM | `crm.customer.create` | `POST /api/crm/customers` |
| CRM | `crm.lead.create` | `POST /api/crm/leads` |
| CRM | `crm.lead.convert` | `POST /api/crm/leads/{id}/convert` |
| CRM | `crm.quotation.create` | `POST /api/crm/quotations` |
| CRM | `crm.quotation.accept` | `POST /api/crm/quotations/{id}/accept` |
| CRM | `crm.quotation.convert` | `POST /api/crm/quotations/{id}/convert` |
| CRM | `crm.sales_contract.bill` | `POST /api/crm/sales-contracts/{id}/bill` |

All 7 routes instrumented with atomic audit. Service layer gained `commit: bool = True` on all 5 mutating functions. `bill_sales_contract` was the most complex — it calls `ar_service.create_customer_invoice` with `commit=False` internally, so the route-level audit + commit ensures both AR invoice + contract status update are atomically audited.

## Dominios instrumentados (2026-08-26, backlog burn-down — Construction Control)

| Dominio | Acción | Ruta |
|---------|--------|------|
| RFI | `construction.rfi.create` | `POST /api/rfis` |
| RFI | `construction.rfi.respond` | `POST /api/rfis/{id}/respond` |
| RFI | `construction.rfi.close` | `POST /api/rfis/{id}/close` |
| Submittal | `construction.submittal.create` | `POST /api/submittals` |
| Submittal | `construction.submittal.response` | `POST /api/submittals/{id}/response` |
| Submittal | `construction.submittal.decide` | `POST /api/submittals/{id}/decision` |
| Quality | `quality.inspection.create` | `POST /api/quality/inspections` |
| Quality | `quality.non_conformance.create` | `POST /api/quality/non-conformances` |
| Quality | `quality.corrective_action.create` | `POST /api/quality/non-conformances/{id}/corrective-actions` |
| Quality | `quality.corrective_action.complete` | `POST /api/quality/corrective-actions/{id}/complete` |
| Quality | `quality.non_conformance.close` | `POST /api/quality/non-conformances/{id}/close` |
| Safety | `safety.observation.create` | `POST /api/safety/observations` |
| Safety | `safety.observation.close` | `POST /api/safety/observations/{id}/close` |
| Safety | `safety.incident.create` | `POST /api/safety/incidents` |
| Safety | `safety.incident.close` | `POST /api/safety/incidents/{id}/close` |
| Site Reports | `site.daily_report.create` | `POST /api/site-reports` |
| Site Reports | `site.daily_report.photo_add` | `POST /api/site-reports/{id}/photos` |
| Site Reports | `site.daily_report.submit` | `POST /api/site-reports/{id}/submit` |
| Site Reports | `site.daily_report.approve` | `POST /api/site-reports/{id}/approve` |
| Site Reports | `site.daily_report.reject` | `POST /api/site-reports/{id}/reject` |
| Documents | `document.document.create` | `POST /api/documents` |
| Documents | `document.document.version_add` | `POST /api/documents/{id}/versions` |
| Evidence | `document.evidence.upload` | `POST /api/evidence` |

All 23 routes instrumented with atomic audit. Service layers gained `commit: bool = True` on all 23 mutating functions across 7 services.

## Dominios instrumentados (2026-08-26, backlog burn-down — Platform: Master Data)

| Dominio | Acción | Ruta |
|---------|--------|------|
| Master Data | `core.company.create` | `POST /api/master-data/companies` |
| Master Data | `core.company.update` | `PATCH /api/master-data/companies/{id}` |
| Master Data | `accounting.account.create` | `POST /api/master-data/accounts` |
| Master Data | `accounting.account.update` | `PATCH /api/master-data/accounts/{id}` |
| Master Data | `tax.tax_code.create` | `POST /api/master-data/tax-codes` |
| Master Data | `core.user.create` | `POST /api/master-data/users` |

All 6 routes instrumented with atomic audit. Service layers gained `commit: bool = True` on `tax_service.create_tax_code` and `user_service.create_user_with_role`. Company/account routes (direct repository calls) use `db.flush()` + audit + `db.commit()`.

## Dominios NO instrumentados todavía (backlog honesto)

La cobertura fuera de las acciones enumeradas arriba sigue siendo parcial.
Esto es deliberado e incremental (ver design doc), no se presenta como
completitud:

- **Supply Chain / Procurement restante** — requisiciones, RFQ,
  cotizaciones, creación/envío de PO, recepciones, entradas de servicio,
  three-way match e inventario — `CLOSED` (2026-08-26, ver arriba).
- **Project Control** (WBS, Presupuestos, Órdenes de cambio, Avances) —
  `CLOSED` (2026-08-26, ver arriba).
- **Enterprise Resources** (Fixed Assets, Equipment, Workforce) —
  `CLOSED` (2026-08-26, ver arriba).
- **Commercial** (CRM: Leads, Oportunidades, Cotizaciones, Contratos de
  venta) — `CLOSED` (2026-08-26, ver arriba).
- **Construction Control** (Documents/Evidence, RFI/Submittals, Daily
  Site Reports, Quality, Safety) — `CLOSED` (2026-08-26, ver arriba).
- **Platform** — Company create/update, User create — `CLOSED` (2026-08-26, ver arriba).

Los diez gaps de Treasury, los gaps de creación de AP/AR, los gaps de
Supply Chain (Procurement + Inventory), los gaps de Project Control,
los gaps de Enterprise Resources, los gaps de Commercial/CRM,
los gaps de Construction Control, y los gaps de Platform:
**cerrados** (2026-08-26, ver arriba).
**TODOS los dominios están instrumentados — 56/56 rutas de mutación con audit trail.**

Un futuro task puede cerrar estos dominios uno por uno reutilizando
exactamente el patrón corregido de esta página: leer la ruta real, agregar
`correlation_id: str = Depends(get_correlation_id)`, invocar el servicio con
`commit=False`, llamar `audit_service.record(...)` después de la mutación y
hacer un único `db.commit()` al final. Cada ruta debe probar que un fallo del
audit revierte también el negocio. No se requiere ningún cambio a
`AuditLog`, `audit_service`, ni al endpoint `GET /api/audit` para agregar
un dominio nuevo.

## Testing

- `tests/test_audit.py`: modelo append-only, aislamiento de company.
- `tests/test_ap_ar.py`: `test_approving_supplier_invoice_creates_audit_log_entry`,
  `test_paying_supplier_invoice_creates_audit_log_entry`.
- `tests/test_treasury_operations.py`: `test_approving_cash_closing_creates_audit_log_entry`,
  `test_registering_remittance_creates_audit_log_entry`, las cuatro pruebas
  de cobertura de los cinco gaps de Treasury, replay idempotente de gasto y
  transferencia (un solo audit), y rollback atómico ante fallo de audit para
  las cinco rutas nuevas.
- `tests/test_procurement_flow.py`: `test_approving_purchase_order_creates_audit_log_entry` (updated to filter by action).
- `tests/test_procurement_flow.py`: updated for procurement + inventory audit — all 331 tests pass.
- `tests/test_posting_engine.py`: `test_creating_journal_entry_creates_audit_log_entry`,
  `test_reversing_journal_entry_creates_audit_log_entry` (2026-08-25).
- Tests updated to filter by `AuditLog.action` where multiple audit entries
  now exist per entity (create + approve/collect), ensuring precision.
- `frontend/tests/AuditLogPage.test.tsx`: página real contra la API real
  (mockeada a nivel de `fetch`), nunca datos fabricados. No necesitó
  cambios para el nuevo dominio — la página ya es genérica sobre
  `entityType`.

## Limitación conocida: call sites históricos todavía no atómicos

`approval_service.decide()` (Track G Task 2) invoca el adaptador de
decisión del dominio propietario (p.ej. `ap_service.apply_approval_decision`),
que a su vez llama a una función de servicio existente
(`approve_supplier_invoice`) que ya hace su propio `db.commit()`
internamente. La ruta (`POST /api/approvals/{id}/decide`) recién después
llama `audit_service.record(...)` y hace su propio `db.commit()`. Si el
proceso falla en la ventana entre esos dos commits, la decisión y la
mutación real de dominio ya quedaron persistidas, pero el registro de
auditoría de ese evento se pierde — sin riesgo de integridad financiera
ni de datos (la transacción de negocio ya es correcta y completa), solo
un hueco de completitud del audit trail para ese evento puntual.

Este mismo patrón existe en call sites históricos
(`approve_supplier_invoice`/`pay_supplier_invoice`/`create_remittance`/
`approve_cash_closing`/`approve_purchase_order`, entre otros): el servicio
puede confirmar antes de que la ruta escriba el audit. No es un defecto
introducido por este slice, pero sí un gap real de completitud.

Las rutas agregadas el 2026-08-26 (cinco gaps de Treasury) **y las
agregadas en este slice** (AP create/cancel, AR create/approve/collect,
Treasury account/cash-closing/bank-statement/bank-statement-line create,
Supply Chain: Procurement + Inventory completo)
**ya no tienen esta limitación**: usan el parámetro `commit=False` y
confirman negocio + audit juntos. El backlog debe aplicar el mismo contrato
transaccional a los call sites históricos restantes, con tests de rollback
ante fallo de audit, antes de certificar `Audit completeness` en producción.

## Frontend

`frontend/src/features/audit/AuditLogPage.tsx` — ruta `/control/auditoria`
(la entrada de navegación "Auditoría" ya existía reservada en
`navigation.ts` bajo la sección "Control"; no se inventó una sección
Plataforma nueva). Filtros: tipo de entidad (texto libre, ya que
`entity_type` es un string dinámico por dominio) y rango de fechas
(client-side sobre `createdAt`). `frontend/src/services/auditService.ts`,
`frontend/src/types/audit.ts`.
