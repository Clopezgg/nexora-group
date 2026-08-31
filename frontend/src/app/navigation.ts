import type { IconName } from '../design-system'

export interface NavItem {
  path: string
  label: string
  icon: IconName
  requiredAny?: string[]
}

export interface NavGroup {
  key: string
  label: string
  items: NavItem[]
}

const read = (...permissions: string[]) => permissions

export const navGroups: NavGroup[] = [
  {
    key: 'inicio',
    label: 'Inicio',
    items: [
      { path: '/inicio', label: 'Inicio', icon: 'home' },
      { path: '/inicio/aprobaciones', label: 'Aprobaciones', icon: 'inbox', requiredAny: read('workflow.approval:read') },
    ],
  },
  {
    key: 'finanzas',
    label: 'Finanzas',
    items: [
      { path: '/finanzas/control', label: 'Centro de Control Financiero', icon: 'chart', requiredAny: read('treasury.account:read', 'accounting.journal_entry:read') },
      { path: '/finanzas/contabilidad', label: 'Contabilidad', icon: 'book', requiredAny: read('accounting.journal_entry:read') },
      { path: '/finanzas/tesoreria', label: 'Tesorería', icon: 'bank', requiredAny: read('treasury.account:read') },
      { path: '/finanzas/conciliacion', label: 'Conciliación bancaria', icon: 'shuffle', requiredAny: read('treasury.bank_reconciliation:read') },
      { path: '/finanzas/cierres-caja', label: 'Cierres de caja', icon: 'receipt', requiredAny: read('treasury.cash_closing:read') },
      { path: '/finanzas/restricciones-fondos', label: 'Restricciones de fondos', icon: 'shield', requiredAny: read('treasury.fund_restriction:read') },
      { path: '/finanzas/comprobantes', label: 'Comprobantes', icon: 'receipt', requiredAny: read('treasury.voucher:read') },
      { path: '/finanzas/cuentas-por-pagar', label: 'Cuentas por pagar', icon: 'card', requiredAny: read('ap.supplier_invoice:read') },
      { path: '/finanzas/cuentas-por-cobrar', label: 'Cuentas por cobrar', icon: 'receipt', requiredAny: read('ar.customer_invoice:read') },
      { path: '/finanzas/activos', label: 'Activos', icon: 'tag', requiredAny: read('asset.fixed_asset:read') },
    ],
  },
  {
    key: 'proyectos',
    label: 'Proyectos',
    items: [
      { path: '/proyectos', label: 'Proyectos', icon: 'project', requiredAny: read('project:read') },
      { path: '/proyectos/wbs', label: 'WBS', icon: 'grid', requiredAny: read('project.wbs:read') },
      { path: '/proyectos/presupuestos', label: 'Presupuestos', icon: 'ruler', requiredAny: read('project.budget:read') },
      { path: '/proyectos/avances', label: 'Avances', icon: 'chart', requiredAny: read('project.progress:read') },
      { path: '/proyectos/ordenes-de-cambio', label: 'Órdenes de cambio', icon: 'shuffle', requiredAny: read('project.change_order:read') },
      { path: '/proyectos/diario-de-obra', label: 'Diario de obra', icon: 'notebook', requiredAny: read('site.daily_report:read') },
      { path: '/proyectos/calidad', label: 'Calidad', icon: 'shield', requiredAny: read('quality.inspection:read', 'quality.non_conformance:read') },
      { path: '/proyectos/seguridad', label: 'Seguridad', icon: 'shield', requiredAny: read('safety.observation:read', 'safety.incident:read') },
      { path: '/proyectos/rfi-submittals', label: 'RFI / Submittals', icon: 'file', requiredAny: read('construction.rfi:read', 'construction.submittal:read') },
    ],
  },
  {
    key: 'abastecimiento',
    label: 'Abastecimiento',
    items: [
      { path: '/abastecimiento/solicitudes', label: 'Solicitudes', icon: 'receipt', requiredAny: read('procurement.requisition:read') },
      { path: '/abastecimiento/comparativos', label: 'Comparativos', icon: 'scale', requiredAny: read('procurement.quotation:read') },
      { path: '/abastecimiento/ordenes-de-compra', label: 'Órdenes de compra', icon: 'package', requiredAny: read('procurement.purchase_order:read') },
      { path: '/abastecimiento/recepciones', label: 'Recepciones', icon: 'truck', requiredAny: read('procurement.goods_receipt:read') },
      { path: '/abastecimiento/inventario', label: 'Inventario', icon: 'grid', requiredAny: read('inventory.stock:read', 'inventory.item:read') },
      { path: '/abastecimiento/almacenes', label: 'Almacenes', icon: 'warehouse', requiredAny: read('inventory.warehouse:read') },
      { path: '/abastecimiento/proveedores', label: 'Proveedores', icon: 'users', requiredAny: read('procurement.supplier:read') },
      { path: '/abastecimiento/contratos', label: 'Contratos', icon: 'file', requiredAny: read('procurement.contract:read') },
    ],
  },
  {
    key: 'comercial',
    label: 'Comercial',
    items: [
      { path: '/comercial/leads', label: 'Leads', icon: 'target', requiredAny: read('crm.lead:read') },
      { path: '/comercial/oportunidades', label: 'Oportunidades', icon: 'briefcase', requiredAny: read('crm.opportunity:read') },
      { path: '/comercial/clientes', label: 'Clientes', icon: 'users', requiredAny: read('crm.customer:read') },
      { path: '/comercial/cotizaciones', label: 'Cotizaciones', icon: 'file', requiredAny: read('crm.quotation:read') },
      { path: '/comercial/contratos', label: 'Contratos', icon: 'file', requiredAny: read('crm.sales_contract:read') },
      { path: '/comercial/facturacion', label: 'Facturación', icon: 'receipt', requiredAny: read('ar.customer_invoice:read') },
      { path: '/comercial/cobros', label: 'Cobros', icon: 'bank', requiredAny: read('ar.customer_receipt:read') },
    ],
  },
  {
    key: 'recursos',
    label: 'Recursos',
    items: [
      { path: '/recursos/personal', label: 'Personal', icon: 'users', requiredAny: read('workforce.worker:read') },
      { path: '/recursos/cuadrillas', label: 'Cuadrillas', icon: 'users', requiredAny: read('workforce.crew:read') },
      { path: '/recursos/tiempo', label: 'Tiempo', icon: 'clock', requiredAny: read('workforce.time_entry:read') },
      { path: '/recursos/equipos', label: 'Equipos', icon: 'equipment', requiredAny: read('equipment.equipment:read') },
      { path: '/recursos/combustible', label: 'Combustible', icon: 'fuel', requiredAny: read('equipment.fuel_log:read') },
      { path: '/recursos/mantenimiento', label: 'Mantenimiento', icon: 'tool', requiredAny: read('equipment.maintenance_order:read') },
    ],
  },
  {
    key: 'control',
    label: 'Control',
    items: [
      { path: '/control/documentos', label: 'Documentos', icon: 'folder', requiredAny: read('document.document:read') },
      { path: '/control/evidencias', label: 'Evidencias', icon: 'camera', requiredAny: read('document.evidence:read') },
      { path: '/control/reportes', label: 'Reportes', icon: 'file', requiredAny: read('reports.general_ledger:read', 'reports.balance_sheet:read', 'reports.income_statement:read', 'reports.cash_flow:read', 'reports.trial_balance:read', 'reports.budget_vs_actual:read') },
      { path: '/control/auditoria', label: 'Auditoría', icon: 'search', requiredAny: read('audit.log:read') },
      { path: '/control/configuracion', label: 'Configuración', icon: 'settings', requiredAny: read('core.company:read', 'core.user:read') },
    ],
  },
]

export function filterNavGroups(permissions: string[] | undefined): NavGroup[] {
  const grants = new Set(permissions ?? [])
  return navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => !item.requiredAny || item.requiredAny.some((permission) => grants.has(permission)),
      ),
    }))
    .filter((group) => group.items.length > 0)
}

export const navItems: NavItem[] = navGroups.flatMap((group) => group.items)
