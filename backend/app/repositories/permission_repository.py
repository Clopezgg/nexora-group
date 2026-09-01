import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import SCOPE_ANY, SCOPE_OWN, Permission, RolePermission, UserCompanyAccess
from app.models.role import Role

# Matriz de permisos (docs/RBAC.md). Cubre los recursos que YA existen:
# core/company, accounting (Track 1) y project/project.wbs/project.planning/
# project.budget/project.change_order/project.progress (Track B), más
# procurement/inventory (Track C). No se inventan permisos para recursos que
# todavía no existen.
_BASE_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("core.company", "create", "Crear compañías"),
    ("core.company", "read", "Ver compañías"),
    ("core.company", "update", "Actualizar datos de una compañía (Settings)"),
    # DEFERRED-FINAL-015: directorio de usuarios por compañía -- crear
    # usuarios queda deliberadamente Administrator-only (via el grant
    # automático de _BASE_PERMISSIONS más abajo); leer el directorio se
    # otorga por rol igual que "core.company"/"read" (mismo scope, misma
    # razón: cualquier rol que puede ver la compañía puede ver quién
    # trabaja en ella para asignar responsabilidad/aprobación).
    ("core.user", "create", "Crear usuarios y asignarles un rol"),
    ("core.user", "read", "Ver el directorio de usuarios de una compañía"),
    ("accounting.journal_entry", "create", "Crear asientos contables"),
    ("accounting.journal_entry", "read", "Ver asientos contables"),
    ("accounting.journal_entry", "reverse", "Revertir asientos contables"),
    ("accounting.account", "create", "Crear cuentas del catálogo contable"),
    ("accounting.account", "read", "Ver el catálogo contable"),
    ("accounting.account", "update", "Clasificar una cuenta (p.ej. Cash Flow activity)"),
    # NXR-REQ-0006, Tax architecture.
    ("tax.tax_code", "create", "Crear códigos de impuesto"),
    ("tax.tax_code", "read", "Ver códigos de impuesto"),
    # Track A - Financial Core (Treasury/AP/AR, orden maestra §26-36).
    ("treasury.account", "create", "Crear cuentas de tesorería"),
    ("treasury.account", "read", "Ver cuentas de tesorería"),
    ("treasury.remittance", "create", "Registrar remesas"),
    ("treasury.remittance", "read", "Ver remesas"),
    ("treasury.general_expense", "create", "Registrar gastos generales"),
    ("treasury.general_expense", "read", "Ver gastos generales"),
    ("treasury.transfer", "create", "Registrar transferencias de tesorería"),
    ("treasury.transfer", "read", "Ver transferencias de tesorería"),
    ("treasury.cash_closing", "create", "Registrar cierres de caja"),
    ("treasury.cash_closing", "approve", "Aprobar cierres de caja"),
    ("treasury.cash_closing", "read", "Ver cierres de caja"),
    ("treasury.bank_reconciliation", "create", "Cargar estados de cuenta bancarios"),
    ("treasury.bank_reconciliation", "match", "Conciliar líneas bancarias"),
    ("treasury.bank_reconciliation", "read", "Ver conciliación bancaria"),
    ("treasury.fund_restriction", "create", "Registrar restricciones de fondos"),
    ("treasury.fund_restriction", "read", "Ver restricciones de fondos"),
    ("treasury.voucher", "read", "Generar/descargar comprobantes"),
    ("ap.supplier_invoice", "create", "Registrar facturas de proveedor"),
    ("ap.supplier_invoice", "submit", "Enviar una factura de proveedor a aprobación"),
    ("ap.supplier_invoice", "approve", "Aprobar facturas de proveedor"),
    ("ap.supplier_invoice", "update", "Editar el plan de pago / cuotas de una factura de proveedor"),
    ("ap.supplier_invoice", "read", "Ver facturas de proveedor"),
    ("ap.supplier_payment", "create", "Registrar pagos a proveedor"),
    ("ap.supplier_payment", "read", "Ver pagos a proveedor"),
    ("ar.customer_invoice", "create", "Registrar facturas de cliente"),
    ("ar.customer_invoice", "approve", "Aprobar facturas de cliente"),
    ("ar.customer_invoice", "read", "Ver facturas de cliente"),
    ("ar.customer_receipt", "create", "Registrar cobros de cliente"),
    ("ar.customer_receipt", "read", "Ver cobros de cliente"),
    # Track B -- Project Control (orden maestra §37-43, §72).
    ("project", "create", "Crear proyectos"),
    ("project", "read", "Ver proyectos"),
    ("project.wbs", "create", "Crear nodos de WBS"),
    ("project.wbs", "read", "Ver WBS"),
    ("project.planning", "create", "Crear tareas/hitos de planeación"),
    ("project.planning", "read", "Ver planeación del proyecto"),
    ("project.budget", "create", "Crear/aprobar presupuesto de proyecto"),
    ("project.budget", "read", "Ver presupuesto y forecast del proyecto"),
    ("project.change_order", "create", "Crear órdenes de cambio"),
    ("project.change_order", "read", "Ver órdenes de cambio"),
    ("project.change_order", "submit", "Enviar orden de cambio a aprobación"),
    ("project.change_order", "approve", "Aprobar orden de cambio"),
    ("project.progress", "create", "Registrar avance de proyecto"),
    ("project.progress", "read", "Ver avance de proyecto"),
    # Track C -- Supply Chain (orden maestra §44-60).
    ("procurement.supplier", "create", "Crear proveedores"),
    ("procurement.supplier", "read", "Ver proveedores"),
    ("procurement.contract", "create", "Crear contratos/subcontratos"),
    ("procurement.contract", "read", "Ver contratos/subcontratos"),
    ("contract.payment_schedule", "read", "Ver planes de pago contractuales"),
    ("contract.payment_schedule", "manage", "Crear/editar planes de pago contractuales"),
    ("procurement.requisition", "create", "Crear solicitudes de compra"),
    ("procurement.requisition", "read", "Ver solicitudes de compra"),
    ("procurement.requisition", "approve", "Aprobar solicitudes de compra"),
    ("procurement.rfq", "create", "Crear RFQ"),
    ("procurement.rfq", "read", "Ver RFQ"),
    ("procurement.quotation", "create", "Registrar cotizaciones de proveedor"),
    ("procurement.quotation", "read", "Ver cotizaciones de proveedor"),
    ("procurement.quotation", "select", "Seleccionar cotización ganadora"),
    ("procurement.purchase_order", "create", "Crear órdenes de compra"),
    ("procurement.purchase_order", "read", "Ver órdenes de compra"),
    ("procurement.purchase_order", "approve", "Aprobar órdenes de compra"),
    # Supplier Performance (NXR-REQ-0058, 2026-08-25). Mismo scope por rol
    # que procurement.purchase_order/read -- ver
    # reporting_service.supplier_performance.
    ("reports.supplier_performance", "read", "Ver métricas de desempeño de proveedores"),
    ("procurement.goods_receipt", "create", "Registrar recepciones de mercadería"),
    ("procurement.goods_receipt", "read", "Ver recepciones de mercadería"),
    ("procurement.service_entry", "create", "Registrar entradas de servicio"),
    ("procurement.service_entry", "read", "Ver entradas de servicio"),
    ("procurement.three_way_match", "create", "Ejecutar three-way match"),
    ("procurement.three_way_match", "read", "Ver resultados de three-way match"),
    ("inventory.item", "create", "Crear ítems de inventario"),
    ("inventory.item", "read", "Ver ítems de inventario"),
    ("inventory.warehouse", "create", "Crear almacenes"),
    ("inventory.warehouse", "read", "Ver almacenes"),
    ("inventory.stock", "read", "Ver stock y movimientos"),
    ("inventory.stock", "move", "Registrar movimientos de stock"),
    ("inventory.physical_count", "create", "Crear conteos físicos"),
    ("inventory.physical_count", "approve", "Aprobar conteos físicos"),
    # Track D -- Enterprise Resources (orden maestra §62-66).
    ("asset.fixed_asset", "create", "Crear activos fijos"),
    ("asset.fixed_asset", "read", "Ver activos fijos"),
    ("asset.fixed_asset", "update", "Cambiar estado de un activo fijo"),
    ("asset.depreciation", "create", "Generar depreciación de un activo fijo"),
    ("asset.depreciation", "read", "Ver depreciación de un activo fijo"),
    ("equipment.equipment", "create", "Registrar equipos"),
    ("equipment.equipment", "read", "Ver equipos"),
    ("equipment.equipment", "update", "Cambiar estado de un equipo"),
    ("equipment.fuel_log", "create", "Registrar consumo de combustible"),
    ("equipment.fuel_log", "read", "Ver consumo de combustible"),
    ("equipment.maintenance_plan", "create", "Crear planes de mantenimiento"),
    ("equipment.maintenance_plan", "read", "Ver planes de mantenimiento"),
    ("equipment.maintenance_order", "create", "Crear órdenes de mantenimiento"),
    ("equipment.maintenance_order", "read", "Ver órdenes de mantenimiento"),
    ("equipment.maintenance_order", "update", "Actualizar/cerrar órdenes de mantenimiento"),
    ("workforce.worker", "create", "Registrar trabajadores"),
    ("workforce.worker", "read", "Ver trabajadores"),
    ("workforce.time_entry", "create", "Registrar horas trabajadas"),
    ("workforce.time_entry", "read", "Ver horas trabajadas"),
    ("workforce.time_entry", "approve", "Aprobar/rechazar horas trabajadas"),
    ("workforce.crew", "create", "Crear cuadrillas"),
    ("workforce.crew", "read", "Ver cuadrillas"),
    ("workforce.crew", "manage_members", "Agregar/quitar miembros de una cuadrilla"),
    # Track E -- Commercial (orden maestra §72-76). La facturación de un
    # SalesContract llama al ar_service real de Track A (nunca duplica AR);
    # por eso "crm.sales_contract" no otorga por sí mismo ningún permiso
    # ar.* -- el usuario que factura solo necesita el permiso comercial.
    ("crm.customer", "create", "Crear clientes"),
    ("crm.customer", "read", "Ver clientes"),
    ("crm.lead", "create", "Crear leads"),
    ("crm.lead", "read", "Ver leads"),
    ("crm.lead", "convert", "Convertir un lead en cliente/oportunidad"),
    ("crm.opportunity", "read", "Ver oportunidades"),
    ("crm.quotation", "create", "Crear cotizaciones de venta"),
    ("crm.quotation", "read", "Ver cotizaciones de venta"),
    ("crm.quotation", "accept", "Aceptar una cotización de venta"),
    ("crm.quotation", "convert", "Convertir una cotización aceptada en contrato de venta"),
    ("crm.sales_contract", "read", "Ver contratos de venta"),
    ("crm.sales_contract", "bill", "Facturar un contrato de venta (crea factura AR real)"),
    # Track D -- Construction Control: Documents/Evidence (orden maestra
    # §77-79, docs/DOCUMENTS_EVIDENCE.md).
    ("document.document", "create", "Crear documentos (con su primera versión)"),
    ("document.document", "read", "Ver documentos"),
    ("document.document", "version", "Subir una nueva versión de un documento"),
    ("document.evidence", "create", "Subir evidencia (foto/archivo) a Azure Blob"),
    ("document.evidence", "read", "Ver metadata de evidencia subida"),
    # Track D -- Construction Control: RFI / Submittals (orden maestra §80,
    # NXR-REQ-0085/0086).
    ("construction.rfi", "create", "Crear RFI (Request For Information)"),
    ("construction.rfi", "read", "Ver RFI"),
    ("construction.rfi", "respond", "Registrar la respuesta de un RFI"),
    ("construction.rfi", "close", "Cerrar un RFI"),
    ("construction.submittal", "create", "Crear Submittal"),
    ("construction.submittal", "read", "Ver Submittals"),
    ("construction.submittal", "review", "Registrar la respuesta de revisión de un Submittal"),
    ("construction.submittal", "decide", "Aprobar/rechazar un Submittal ya revisado"),
    # Track D -- Construction Control: Daily Site Reports / Quality / Safety
    # (orden maestra §81-84, NXR-REQ-0081/0082/0083/0084).
    ("site.daily_report", "create", "Crear/enviar reportes diarios de obra"),
    ("site.daily_report", "read", "Ver reportes diarios de obra"),
    ("site.daily_report", "approve", "Aprobar/rechazar reportes diarios de obra"),
    ("quality.inspection", "create", "Registrar inspecciones de calidad"),
    ("quality.inspection", "read", "Ver inspecciones de calidad"),
    ("quality.non_conformance", "create", "Registrar no conformidades"),
    ("quality.non_conformance", "read", "Ver no conformidades"),
    ("quality.non_conformance", "close", "Cerrar no conformidades"),
    ("quality.corrective_action", "create", "Registrar acciones correctivas"),
    ("quality.corrective_action", "read", "Ver acciones correctivas"),
    ("quality.corrective_action", "complete", "Completar acciones correctivas"),
    ("safety.observation", "create", "Registrar observaciones de seguridad"),
    ("safety.observation", "read", "Ver observaciones de seguridad"),
    ("safety.observation", "close", "Cerrar observaciones de seguridad"),
    ("safety.incident", "create", "Registrar incidentes de seguridad"),
    ("safety.incident", "read", "Ver incidentes de seguridad"),
    ("safety.incident", "close", "Cerrar incidentes de seguridad"),
    # Track G -- Platform: Audit trail (orden maestra §90, NXR-REQ-0090,
    # docs/AUDIT.md).
    ("audit.log", "read", "Ver bitácora de auditoría"),
    # Track G -- Platform: Approval Inbox / Segregación de Funciones (orden
    # maestra §87-89, NXR-REQ-0087/0088/0089). "decide" solo se otorga a
    # roles que plausiblemente aprueban/rechazan AP o Submittal (Finance
    # Manager, Project Manager) -- "read" es más amplio (también
    # Administrator/Auditor, mismo patrón que audit.log).
    ("workflow.approval", "read", "Ver la bandeja de aprobaciones"),
    ("workflow.approval", "decide", "Aprobar/rechazar una solicitud de aprobación"),
    # Track H -- Reports/Search/Analytics (NXR-REQ-0093/0094). Alcance
    # deliberado de esta fase: Trial Balance + Budget vs Actual únicamente
    # (ver docs/superpowers/specs/2026-08-25-reports-search-analytics-design.md).
    ("reports.trial_balance", "read", "Ver el reporte de Balance de Comprobación"),
    ("reports.budget_vs_actual", "read", "Ver el reporte de Presupuesto vs. Real"),
    # Financial Statements (NXR-REQ-0093, sub-alcance 2026-08-25). Otorgado
    # exactamente donde reports.trial_balance/read ya está otorgado, mismo
    # scope -- ver docs/superpowers/specs/2026-08-25-financial-statements-design.md.
    ("reports.general_ledger", "read", "Ver el Libro Mayor"),
    ("reports.balance_sheet", "read", "Ver el Balance General"),
    ("reports.income_statement", "read", "Ver el Estado de Resultados"),
    # Cash Flow (NXR-REQ-0016/0093, 2026-08-25). Mismo scope por rol que
    # reports.balance_sheet/read -- ver reporting_service.cash_flow_statement.
    ("reports.cash_flow", "read", "Ver el Estado de Flujo de Efectivo"),
    # Closing Center / Subledger<->GL reconciliation (orden maestra FINAL,
    # Phase 4). Mismo scope por rol que reports.trial_balance/read.
    ("accounting.reconciliation", "read", "Ver la conciliación Subledger <-> GL"),
    ("accounting.closing", "read", "Ver el Centro de Cierre contable"),
    ("accounting.closing", "execute", "Ejecutar el cierre duro de un período fiscal"),
    # Track H -- Reports/Search/Analytics (orden maestra §92-96, NXR-REQ-0092
    # Global Search). Se otorga ampliamente (mismo patrón que
    # document.document/read) porque casi todo rol operativo necesita poder
    # buscar entidades por nombre/número dentro de su propio company scope.
    ("search.global", "read", "Buscar entidades globalmente"),
)
# NOTA: ActiveUIContext (GET/PUT /api/context) NO pasa por este motor de
# permisos -- es una preferencia personal del usuario autenticado (su
# proyecto activo en la UI), no un recurso protegido por rol. Solo requiere
# sesión válida, igual que antes de este track.

# (resource, action, company_scope). company_scope=OWN significa que el
# otorgamiento solo aplica a las companies que el usuario tiene en
# UserCompanyAccess (INV-COMP-001); ANY = sin restricción de company.
# Administrator/Auditor son ANY (necesitan ver/administrar todo). Los roles
# operativos (Finance Manager, Accountant) son OWN por defecto -- un
# Accountant normal no debe poder escribir en una company a la que no fue
# asignado explícitamente.
_ROLE_GRANTS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "Administrator": tuple((resource, action, SCOPE_ANY) for resource, action, _ in _BASE_PERMISSIONS),
    "Finance Manager": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("core.company", "update", SCOPE_OWN),
        ("accounting.journal_entry", "create", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.journal_entry", "reverse", SCOPE_OWN),
        ("accounting.account", "create", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
        ("accounting.account", "update", SCOPE_OWN),
        ("tax.tax_code", "create", SCOPE_OWN),
        ("tax.tax_code", "read", SCOPE_OWN),
        ("treasury.account", "create", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "create", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("treasury.general_expense", "create", SCOPE_OWN),
        ("treasury.general_expense", "read", SCOPE_OWN),
        ("treasury.transfer", "create", SCOPE_OWN),
        ("treasury.transfer", "read", SCOPE_OWN),
        ("treasury.cash_closing", "create", SCOPE_OWN),
        ("treasury.cash_closing", "approve", SCOPE_OWN),
        ("treasury.cash_closing", "read", SCOPE_OWN),
        ("treasury.bank_reconciliation", "create", SCOPE_OWN),
        ("treasury.bank_reconciliation", "match", SCOPE_OWN),
        ("treasury.bank_reconciliation", "read", SCOPE_OWN),
        ("treasury.fund_restriction", "create", SCOPE_OWN),
        ("treasury.fund_restriction", "read", SCOPE_OWN),
        ("treasury.voucher", "read", SCOPE_OWN),
        ("ap.supplier_invoice", "create", SCOPE_OWN),
        ("ap.supplier_invoice", "submit", SCOPE_OWN),
        ("ap.supplier_invoice", "approve", SCOPE_OWN),
        ("ap.supplier_invoice", "update", SCOPE_OWN),
        ("ap.supplier_invoice", "read", SCOPE_OWN),
        ("ap.supplier_payment", "create", SCOPE_OWN),
        ("ap.supplier_payment", "read", SCOPE_OWN),
        ("procurement.supplier", "read", SCOPE_OWN),
        ("crm.customer", "read", SCOPE_OWN),
        ("ar.customer_invoice", "create", SCOPE_OWN),
        ("ar.customer_invoice", "approve", SCOPE_OWN),
        ("ar.customer_invoice", "read", SCOPE_OWN),
        ("ar.customer_receipt", "create", SCOPE_OWN),
        ("ar.customer_receipt", "read", SCOPE_OWN),
        ("asset.fixed_asset", "create", SCOPE_OWN),
        ("asset.fixed_asset", "read", SCOPE_OWN),
        ("asset.fixed_asset", "update", SCOPE_OWN),
        ("asset.depreciation", "create", SCOPE_OWN),
        ("asset.depreciation", "read", SCOPE_OWN),
        ("audit.log", "read", SCOPE_OWN),
        ("workflow.approval", "read", SCOPE_OWN),
        ("workflow.approval", "decide", SCOPE_OWN),
        ("reports.trial_balance", "read", SCOPE_OWN),
        ("accounting.reconciliation", "read", SCOPE_OWN),
        ("accounting.closing", "read", SCOPE_OWN),
        ("accounting.closing", "execute", SCOPE_OWN),
        ("reports.budget_vs_actual", "read", SCOPE_OWN),
        ("reports.general_ledger", "read", SCOPE_OWN),
        ("reports.balance_sheet", "read", SCOPE_OWN),
        ("reports.cash_flow", "read", SCOPE_OWN),
        ("reports.income_statement", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Treasury Manager": (
        ("core.company", "read", SCOPE_ANY),
        ("core.user", "read", SCOPE_ANY),
        ("accounting.account", "read", SCOPE_OWN),
        ("treasury.account", "create", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "create", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("treasury.general_expense", "create", SCOPE_OWN),
        ("treasury.general_expense", "read", SCOPE_OWN),
        ("treasury.transfer", "create", SCOPE_OWN),
        ("treasury.transfer", "read", SCOPE_OWN),
        ("treasury.cash_closing", "create", SCOPE_OWN),
        ("treasury.cash_closing", "approve", SCOPE_OWN),
        ("treasury.cash_closing", "read", SCOPE_OWN),
        ("treasury.bank_reconciliation", "create", SCOPE_OWN),
        ("treasury.bank_reconciliation", "match", SCOPE_OWN),
        ("treasury.bank_reconciliation", "read", SCOPE_OWN),
        ("treasury.fund_restriction", "create", SCOPE_OWN),
        ("treasury.fund_restriction", "read", SCOPE_OWN),
        ("treasury.voucher", "read", SCOPE_OWN),
        ("ap.supplier_payment", "create", SCOPE_OWN),
        ("ap.supplier_payment", "read", SCOPE_OWN),
        ("ar.customer_receipt", "create", SCOPE_OWN),
        ("ar.customer_receipt", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Accountant": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("accounting.journal_entry", "create", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("treasury.general_expense", "read", SCOPE_OWN),
        ("treasury.transfer", "read", SCOPE_OWN),
        ("treasury.bank_reconciliation", "read", SCOPE_OWN),
        ("treasury.voucher", "read", SCOPE_OWN),
        ("ap.supplier_invoice", "create", SCOPE_OWN),
        ("ap.supplier_invoice", "submit", SCOPE_OWN),
        ("ap.supplier_invoice", "update", SCOPE_OWN),
        ("ap.supplier_invoice", "read", SCOPE_OWN),
        ("procurement.supplier", "read", SCOPE_OWN),
        ("crm.customer", "read", SCOPE_OWN),
        ("ar.customer_invoice", "create", SCOPE_OWN),
        ("ar.customer_invoice", "read", SCOPE_OWN),
        ("asset.fixed_asset", "read", SCOPE_OWN),
        ("asset.depreciation", "read", SCOPE_OWN),
        ("reports.trial_balance", "read", SCOPE_OWN),
        ("accounting.reconciliation", "read", SCOPE_OWN),
        ("accounting.closing", "read", SCOPE_OWN),
        ("accounting.closing", "execute", SCOPE_OWN),
        ("reports.general_ledger", "read", SCOPE_OWN),
        ("reports.balance_sheet", "read", SCOPE_OWN),
        ("reports.cash_flow", "read", SCOPE_OWN),
        ("reports.income_statement", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Auditor": (
        ("core.company", "read", SCOPE_ANY),
        ("core.user", "read", SCOPE_ANY),
        ("accounting.journal_entry", "read", SCOPE_ANY),
        ("accounting.account", "read", SCOPE_ANY),
        ("tax.tax_code", "read", SCOPE_ANY),
        ("treasury.account", "read", SCOPE_ANY),
        ("treasury.remittance", "read", SCOPE_ANY),
        ("treasury.general_expense", "read", SCOPE_ANY),
        ("treasury.transfer", "read", SCOPE_ANY),
        ("treasury.cash_closing", "read", SCOPE_ANY),
        ("treasury.bank_reconciliation", "read", SCOPE_ANY),
        ("treasury.fund_restriction", "read", SCOPE_ANY),
        ("treasury.voucher", "read", SCOPE_ANY),
        ("ap.supplier_invoice", "read", SCOPE_ANY),
        ("ap.supplier_payment", "read", SCOPE_ANY),
        ("ar.customer_invoice", "read", SCOPE_ANY),
        ("ar.customer_receipt", "read", SCOPE_ANY),
        ("project", "read", SCOPE_ANY),
        ("project.wbs", "read", SCOPE_ANY),
        ("project.planning", "read", SCOPE_ANY),
        ("project.budget", "read", SCOPE_ANY),
        ("project.change_order", "read", SCOPE_ANY),
        ("project.progress", "read", SCOPE_ANY),
        ("procurement.supplier", "read", SCOPE_ANY),
        ("procurement.contract", "read", SCOPE_ANY),
        ("contract.payment_schedule", "read", SCOPE_ANY),
        ("contract.payment_schedule", "manage", SCOPE_ANY),
        ("procurement.requisition", "read", SCOPE_ANY),
        ("procurement.rfq", "read", SCOPE_ANY),
        ("procurement.quotation", "read", SCOPE_ANY),
        ("procurement.purchase_order", "read", SCOPE_ANY),
        ("reports.supplier_performance", "read", SCOPE_ANY),
        ("procurement.goods_receipt", "read", SCOPE_ANY),
        ("procurement.service_entry", "read", SCOPE_ANY),
        ("procurement.three_way_match", "read", SCOPE_ANY),
        ("inventory.item", "read", SCOPE_ANY),
        ("inventory.warehouse", "read", SCOPE_ANY),
        ("inventory.stock", "read", SCOPE_ANY),
        ("asset.fixed_asset", "read", SCOPE_ANY),
        ("asset.depreciation", "read", SCOPE_ANY),
        ("equipment.equipment", "read", SCOPE_ANY),
        ("equipment.fuel_log", "read", SCOPE_ANY),
        ("equipment.maintenance_plan", "read", SCOPE_ANY),
        ("equipment.maintenance_order", "read", SCOPE_ANY),
        ("workforce.worker", "read", SCOPE_ANY),
        ("workforce.crew", "read", SCOPE_ANY),
        ("workforce.time_entry", "read", SCOPE_ANY),
        ("crm.customer", "read", SCOPE_ANY),
        ("crm.lead", "read", SCOPE_ANY),
        ("crm.opportunity", "read", SCOPE_ANY),
        ("crm.quotation", "read", SCOPE_ANY),
        ("crm.sales_contract", "read", SCOPE_ANY),
        ("document.document", "read", SCOPE_ANY),
        ("document.evidence", "read", SCOPE_ANY),
        ("construction.rfi", "read", SCOPE_ANY),
        ("construction.submittal", "read", SCOPE_ANY),
        ("site.daily_report", "read", SCOPE_ANY),
        ("quality.inspection", "read", SCOPE_ANY),
        ("quality.non_conformance", "read", SCOPE_ANY),
        ("quality.corrective_action", "read", SCOPE_ANY),
        ("safety.observation", "read", SCOPE_ANY),
        ("safety.incident", "read", SCOPE_ANY),
        ("audit.log", "read", SCOPE_ANY),
        ("workflow.approval", "read", SCOPE_ANY),
        ("reports.trial_balance", "read", SCOPE_ANY),
        ("accounting.reconciliation", "read", SCOPE_ANY),
        ("accounting.closing", "read", SCOPE_ANY),
        ("accounting.closing", "execute", SCOPE_ANY),
        ("reports.budget_vs_actual", "read", SCOPE_ANY),
        ("reports.general_ledger", "read", SCOPE_ANY),
        ("reports.balance_sheet", "read", SCOPE_ANY),
        ("reports.cash_flow", "read", SCOPE_ANY),
        ("reports.income_statement", "read", SCOPE_ANY),
        ("search.global", "read", SCOPE_ANY),
    ),
    "Viewer": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("ap.supplier_invoice", "read", SCOPE_OWN),
        ("ar.customer_invoice", "read", SCOPE_OWN),
        ("project", "read", SCOPE_OWN),
        ("project.wbs", "read", SCOPE_OWN),
        ("project.planning", "read", SCOPE_OWN),
        ("project.budget", "read", SCOPE_OWN),
        ("project.change_order", "read", SCOPE_OWN),
        ("project.progress", "read", SCOPE_OWN),
        ("document.document", "read", SCOPE_OWN),
        ("document.evidence", "read", SCOPE_OWN),
        ("construction.rfi", "read", SCOPE_OWN),
        ("construction.submittal", "read", SCOPE_OWN),
        ("site.daily_report", "read", SCOPE_OWN),
        ("quality.inspection", "read", SCOPE_OWN),
        ("quality.non_conformance", "read", SCOPE_OWN),
        ("quality.corrective_action", "read", SCOPE_OWN),
        ("safety.observation", "read", SCOPE_OWN),
        ("safety.incident", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Project Manager": (
        ("core.company", "read", SCOPE_ANY),
        ("core.user", "read", SCOPE_ANY),
        ("project", "create", SCOPE_OWN),
        ("project", "read", SCOPE_OWN),
        ("project.wbs", "create", SCOPE_OWN),
        ("project.wbs", "read", SCOPE_OWN),
        ("project.planning", "create", SCOPE_OWN),
        ("project.planning", "read", SCOPE_OWN),
        ("project.budget", "read", SCOPE_OWN),
        ("project.change_order", "create", SCOPE_OWN),
        ("project.change_order", "read", SCOPE_OWN),
        ("project.change_order", "submit", SCOPE_OWN),
        ("project.progress", "create", SCOPE_OWN),
        ("project.progress", "read", SCOPE_OWN),
        ("workforce.time_entry", "approve", SCOPE_OWN),
        ("workforce.time_entry", "read", SCOPE_OWN),
        ("equipment.equipment", "read", SCOPE_OWN),
        ("equipment.maintenance_order", "read", SCOPE_OWN),
        ("document.document", "create", SCOPE_OWN),
        ("document.document", "read", SCOPE_OWN),
        ("document.document", "version", SCOPE_OWN),
        ("document.evidence", "create", SCOPE_OWN),
        ("document.evidence", "read", SCOPE_OWN),
        ("construction.rfi", "create", SCOPE_OWN),
        ("construction.rfi", "read", SCOPE_OWN),
        ("construction.rfi", "respond", SCOPE_OWN),
        ("construction.rfi", "close", SCOPE_OWN),
        ("construction.submittal", "create", SCOPE_OWN),
        ("construction.submittal", "read", SCOPE_OWN),
        ("construction.submittal", "review", SCOPE_OWN),
        ("construction.submittal", "decide", SCOPE_OWN),
        ("site.daily_report", "create", SCOPE_OWN),
        ("site.daily_report", "read", SCOPE_OWN),
        ("site.daily_report", "approve", SCOPE_OWN),
        ("quality.inspection", "create", SCOPE_OWN),
        ("quality.inspection", "read", SCOPE_OWN),
        ("quality.non_conformance", "create", SCOPE_OWN),
        ("quality.non_conformance", "read", SCOPE_OWN),
        ("quality.non_conformance", "close", SCOPE_OWN),
        ("quality.corrective_action", "create", SCOPE_OWN),
        ("quality.corrective_action", "read", SCOPE_OWN),
        ("quality.corrective_action", "complete", SCOPE_OWN),
        ("safety.observation", "create", SCOPE_OWN),
        ("safety.observation", "read", SCOPE_OWN),
        ("safety.observation", "close", SCOPE_OWN),
        ("safety.incident", "create", SCOPE_OWN),
        ("safety.incident", "read", SCOPE_OWN),
        ("safety.incident", "close", SCOPE_OWN),
        ("workflow.approval", "read", SCOPE_OWN),
        ("workflow.approval", "decide", SCOPE_OWN),
        ("reports.budget_vs_actual", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Project Controller": (
        ("core.company", "read", SCOPE_ANY),
        ("core.user", "read", SCOPE_ANY),
        ("project", "read", SCOPE_OWN),
        ("project.wbs", "read", SCOPE_OWN),
        ("project.planning", "read", SCOPE_OWN),
        ("project.budget", "create", SCOPE_OWN),
        ("project.budget", "read", SCOPE_OWN),
        ("reports.budget_vs_actual", "read", SCOPE_OWN),
        ("project.change_order", "read", SCOPE_OWN),
        ("project.change_order", "approve", SCOPE_OWN),
        ("project.progress", "read", SCOPE_OWN),
        ("asset.depreciation", "read", SCOPE_OWN),
        ("workforce.time_entry", "read", SCOPE_OWN),
        ("document.document", "read", SCOPE_OWN),
        ("document.evidence", "read", SCOPE_OWN),
        ("construction.rfi", "read", SCOPE_OWN),
        ("construction.submittal", "read", SCOPE_OWN),
        ("site.daily_report", "read", SCOPE_OWN),
        ("quality.inspection", "read", SCOPE_OWN),
        ("quality.non_conformance", "read", SCOPE_OWN),
        ("quality.corrective_action", "read", SCOPE_OWN),
        ("safety.observation", "read", SCOPE_OWN),
        ("safety.incident", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Procurement Manager": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("procurement.supplier", "create", SCOPE_OWN),
        ("procurement.supplier", "read", SCOPE_OWN),
        ("procurement.contract", "create", SCOPE_OWN),
        ("procurement.contract", "read", SCOPE_OWN),
        ("contract.payment_schedule", "read", SCOPE_OWN),
        ("contract.payment_schedule", "manage", SCOPE_OWN),
        ("procurement.requisition", "read", SCOPE_OWN),
        ("procurement.requisition", "approve", SCOPE_OWN),
        ("procurement.rfq", "create", SCOPE_OWN),
        ("procurement.rfq", "read", SCOPE_OWN),
        ("procurement.quotation", "create", SCOPE_OWN),
        ("procurement.quotation", "read", SCOPE_OWN),
        ("procurement.quotation", "select", SCOPE_OWN),
        ("procurement.purchase_order", "create", SCOPE_OWN),
        ("procurement.purchase_order", "read", SCOPE_OWN),
        ("reports.supplier_performance", "read", SCOPE_OWN),
        ("procurement.purchase_order", "approve", SCOPE_OWN),
        ("procurement.goods_receipt", "read", SCOPE_OWN),
        ("procurement.service_entry", "read", SCOPE_OWN),
        ("procurement.three_way_match", "create", SCOPE_OWN),
        ("procurement.three_way_match", "read", SCOPE_OWN),
        ("inventory.item", "read", SCOPE_OWN),
        ("inventory.warehouse", "read", SCOPE_OWN),
        ("inventory.stock", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Buyer": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("procurement.supplier", "read", SCOPE_OWN),
        ("procurement.requisition", "create", SCOPE_OWN),
        ("procurement.requisition", "read", SCOPE_OWN),
        ("procurement.rfq", "create", SCOPE_OWN),
        ("procurement.rfq", "read", SCOPE_OWN),
        ("procurement.quotation", "create", SCOPE_OWN),
        ("procurement.quotation", "read", SCOPE_OWN),
        ("procurement.purchase_order", "create", SCOPE_OWN),
        ("procurement.purchase_order", "read", SCOPE_OWN),
        ("reports.supplier_performance", "read", SCOPE_OWN),
        ("procurement.goods_receipt", "read", SCOPE_OWN),
        ("procurement.service_entry", "read", SCOPE_OWN),
        ("procurement.three_way_match", "read", SCOPE_OWN),
        ("inventory.item", "read", SCOPE_OWN),
        ("inventory.warehouse", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    "Warehouse Manager": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("procurement.purchase_order", "read", SCOPE_OWN),
        ("reports.supplier_performance", "read", SCOPE_OWN),
        ("procurement.goods_receipt", "create", SCOPE_OWN),
        ("procurement.goods_receipt", "read", SCOPE_OWN),
        ("inventory.item", "create", SCOPE_OWN),
        ("inventory.item", "read", SCOPE_OWN),
        ("inventory.warehouse", "create", SCOPE_OWN),
        ("inventory.warehouse", "read", SCOPE_OWN),
        ("inventory.stock", "read", SCOPE_OWN),
        ("inventory.stock", "move", SCOPE_OWN),
        ("inventory.physical_count", "create", SCOPE_OWN),
        ("inventory.physical_count", "approve", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    # Track D -- Enterprise Resources. "Equipment Manager" tiene la custodia
    # física de activos/equipos/mantenimiento; no otorga asset.depreciation
    # (eso es contabilización, dueño de Finance Manager/Accountant).
    "Equipment Manager": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("asset.fixed_asset", "create", SCOPE_OWN),
        ("asset.fixed_asset", "read", SCOPE_OWN),
        ("asset.fixed_asset", "update", SCOPE_OWN),
        ("equipment.equipment", "create", SCOPE_OWN),
        ("equipment.equipment", "read", SCOPE_OWN),
        ("equipment.equipment", "update", SCOPE_OWN),
        ("equipment.fuel_log", "create", SCOPE_OWN),
        ("equipment.fuel_log", "read", SCOPE_OWN),
        ("equipment.maintenance_plan", "create", SCOPE_OWN),
        ("equipment.maintenance_plan", "read", SCOPE_OWN),
        ("equipment.maintenance_order", "create", SCOPE_OWN),
        ("equipment.maintenance_order", "read", SCOPE_OWN),
        ("equipment.maintenance_order", "update", SCOPE_OWN),
        ("workforce.worker", "create", SCOPE_OWN),
        ("workforce.worker", "read", SCOPE_OWN),
        ("workforce.crew", "create", SCOPE_OWN),
        ("workforce.crew", "read", SCOPE_OWN),
        ("workforce.crew", "manage_members", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    # "Operations User": personal de campo/site que registra combustible,
    # abre órdenes de mantenimiento y reporta sus propias horas -- no
    # aprueba nada (eso corresponde a Project Manager/Equipment Manager).
    "Operations User": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("equipment.equipment", "read", SCOPE_OWN),
        ("equipment.fuel_log", "create", SCOPE_OWN),
        ("equipment.fuel_log", "read", SCOPE_OWN),
        ("equipment.maintenance_order", "create", SCOPE_OWN),
        ("equipment.maintenance_order", "read", SCOPE_OWN),
        ("workforce.worker", "read", SCOPE_OWN),
        ("workforce.crew", "read", SCOPE_OWN),
        ("workforce.time_entry", "create", SCOPE_OWN),
        ("workforce.time_entry", "read", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
    # Track E -- Commercial. "Sales Manager" es dueño del flujo Lead ->
    # Opportunity -> Customer/Quotation -> SalesContract; para facturar
    # necesita ver companies/cuentas contables (selector de cuentas de
    # ingreso/CxC en el formulario de facturación), pero NUNCA obtiene
    # permisos ar.* -- la facturación real la sigue controlando Track A.
    "Sales Manager": (
        ("core.company", "read", SCOPE_OWN),
        ("core.user", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
        ("project", "read", SCOPE_OWN),
        ("crm.customer", "create", SCOPE_OWN),
        ("crm.customer", "read", SCOPE_OWN),
        ("crm.lead", "create", SCOPE_OWN),
        ("crm.lead", "read", SCOPE_OWN),
        ("crm.lead", "convert", SCOPE_OWN),
        ("crm.opportunity", "read", SCOPE_OWN),
        ("crm.quotation", "create", SCOPE_OWN),
        ("crm.quotation", "read", SCOPE_OWN),
        ("crm.quotation", "accept", SCOPE_OWN),
        ("crm.quotation", "convert", SCOPE_OWN),
        ("crm.sales_contract", "read", SCOPE_OWN),
        ("crm.sales_contract", "bill", SCOPE_OWN),
        ("search.global", "read", SCOPE_OWN),
    ),
}


def ensure_base_permissions(db: Session) -> None:
    """Idempotente. Crea el catálogo de permisos y los otorgamientos por rol
    si aún no existen (y corrige company_scope si la matriz cambió)."""
    existing_permissions = {
        (permission.resource, permission.action): permission
        for permission in db.execute(select(Permission)).scalars()
    }
    for resource, action, description in _BASE_PERMISSIONS:
        if (resource, action) not in existing_permissions:
            permission = Permission(resource=resource, action=action, description=description)
            db.add(permission)
            db.flush()
            existing_permissions[(resource, action)] = permission

    roles_by_name = {role.name: role for role in db.execute(select(Role)).scalars()}
    existing_grants = {
        (grant.role_id, grant.permission_id): grant
        for grant in db.execute(select(RolePermission)).scalars()
    }

    for role_name, grants in _ROLE_GRANTS.items():
        role = roles_by_name.get(role_name)
        if role is None:
            continue
        for resource, action, company_scope in grants:
            permission = existing_permissions.get((resource, action))
            if permission is None:
                continue
            key = (role.id, permission.id)
            if key not in existing_grants:
                db.add(
                    RolePermission(
                        role_id=role.id, permission_id=permission.id, company_scope=company_scope
                    )
                )
            elif existing_grants[key].company_scope != company_scope:
                existing_grants[key].company_scope = company_scope

    db.flush()


def grant_company_access(db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID) -> UserCompanyAccess:
    """DEFERRED-FINAL-015: mismo modelo `UserCompanyAccess` que ya usa
    INV-COMP-001 en todo el motor de permisos, ahora con un caller real
    fuera de tests (antes solo `db_session.add(UserCompanyAccess(...))`
    directo en `tests/helpers.py`)."""
    grant = UserCompanyAccess(user_id=user_id, company_id=company_id)
    db.add(grant)
    db.flush()
    return grant
