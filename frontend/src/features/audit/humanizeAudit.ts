/**
 * Turns a stored technical audit action (`<module>.<entity>.<verb>`, e.g.
 * `ap.supplier_invoice.approve`) into human Spanish for the primary audit
 * view. The stored code is never changed — this is presentation only.
 */

const MODULE_LABELS: Record<string, string> = {
  core: 'Configuración',
  accounting: 'Contabilidad',
  treasury: 'Tesorería',
  ap: 'Cuentas por pagar',
  ar: 'Cuentas por cobrar',
  asset: 'Activos',
  project: 'Proyectos',
  procurement: 'Abastecimiento',
  inventory: 'Inventario',
  crm: 'Comercial',
  construction: 'Construcción',
  equipment: 'Equipos',
  workforce: 'Personal',
  document: 'Documentos',
  workflow: 'Aprobaciones',
  site: 'Obra',
  safety: 'Seguridad',
  quality: 'Calidad',
  tax: 'Impuestos',
  search: 'Búsqueda',
  reports: 'Reportes',
  test: 'Pruebas',
}

const ENTITY_LABELS: Record<string, string> = {
  company: 'Compañía',
  user: 'Usuario',
  account: 'Cuenta contable',
  journal_entry: 'Asiento contable',
  resource_posting_config: 'Configuración de imputación',
  supplier_invoice: 'Factura de proveedor',
  supplier_payment: 'Pago a proveedor',
  customer_invoice: 'Factura de cliente',
  customer_receipt: 'Cobro de cliente',
  fixed_asset: 'Activo fijo',
  depreciation: 'Depreciación',
  project: 'Proyecto',
  budget: 'Presupuesto',
  wbs: 'WBS',
  change_order: 'Orden de cambio',
  purchase_order: 'Orden de compra',
  requisition: 'Requisición',
  goods_receipt: 'Recepción de mercadería',
  quotation: 'Cotización',
  rfq: 'Solicitud de cotización',
  contract: 'Contrato',
  three_way_match: 'Conciliación tres vías',
  service_entry: 'Entrada de servicio',
  item: 'Artículo',
  warehouse: 'Almacén',
  stock: 'Existencias',
  physical_count: 'Conteo físico',
  lead: 'Prospecto',
  opportunity: 'Oportunidad',
  customer: 'Cliente',
  sales_contract: 'Contrato de venta',
  rfi: 'RFI',
  submittal: 'Submittal',
  daily_report: 'Reporte diario de obra',
  inspection: 'Inspección de calidad',
  non_conformance: 'No conformidad',
  corrective_action: 'Acción correctiva',
  observation: 'Observación de seguridad',
  incident: 'Incidente de seguridad',
  equipment: 'Equipo',
  fuel_log: 'Registro de combustible',
  maintenance_order: 'Orden de mantenimiento',
  maintenance_plan: 'Plan de mantenimiento',
  time_entry: 'Registro de tiempo',
  worker: 'Trabajador',
  crew: 'Cuadrilla',
  document: 'Documento',
  evidence: 'Evidencia',
  approval: 'Solicitud de aprobación',
  cash_closing: 'Cierre de caja',
  bank_reconciliation: 'Conciliación bancaria',
  transfer: 'Transferencia',
  remittance: 'Remesa',
  general_expense: 'Gasto general',
  fund_restriction: 'Restricción de fondos',
  voucher: 'Comprobante',
  tax_code: 'Código de impuesto',
  page: 'Registro',
  project_reset: 'Restablecimiento de proyecto',
  company_access: 'Acceso a compañía',
  reset: 'Restablecimiento de proyecto',
  project_access: 'Acceso a proyecto',
  role: 'Rol',
  profile: 'Perfil',
}

const VERB_LABELS: Record<string, string> = {
  create: 'Creación',
  update: 'Actualización',
  delete: 'Eliminación',
  approve: 'Aprobación',
  reject: 'Rechazo',
  cancel: 'Cancelación',
  reverse: 'Reversión',
  submit: 'Envío',
  post: 'Contabilización',
  capitalize: 'Capitalización',
  status_change: 'Cambio de estado',
  upload: 'Carga',
  version_add: 'Nueva versión',
  grant: 'Otorgamiento',
  revoke: 'Revocación',
  decide: 'Decisión',
  respond: 'Respuesta',
  response: 'Respuesta',
  close: 'Cierre',
  bill: 'Facturación',
  convert: 'Conversión',
  accept: 'Aceptación',
  upsert: 'Configuración',
  match: 'Conciliación',
  authorized: 'Autorización',
  reset: 'Restablecimiento',
}

export interface HumanAudit {
  /** e.g. "Factura de proveedor · Aprobación" */
  event: string
  /** e.g. "Cuentas por pagar" */
  module: string
  /** e.g. "Factura de proveedor" */
  record: string
  /** original stored code, unchanged */
  code: string
}

function titleize(token: string): string {
  const text = token.replace(/[._]/g, ' ').trim()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Actions whose `module.entity.verb` decomposition reads poorly. */
const SPECIAL_ACTIONS: Record<string, { event: string; module: string; record: string }> = {
  'project.reset.authorized': {
    event: 'Restablecimiento autorizado de proyecto',
    module: 'Proyectos',
    record: 'Proyecto',
  },
}

export function humanizeAuditAction(action: string): HumanAudit {
  const special = SPECIAL_ACTIONS[action]
  if (special) return { ...special, code: action }

  const parts = action.split('.')
  const moduleKey = parts[0] ?? ''
  const verbKey = parts.length > 1 ? parts[parts.length - 1] : ''
  const entityKey = parts.length >= 3 ? parts[parts.length - 2] : parts[1] ?? ''

  const module = MODULE_LABELS[moduleKey] ?? titleize(moduleKey)
  const record = ENTITY_LABELS[entityKey] ?? titleize(entityKey)
  const verb = VERB_LABELS[verbKey] ?? titleize(verbKey)

  const event = record && verb ? `${record} · ${verb}` : record || verb || titleize(action)
  return { event, module, record: record || '—', code: action }
}

const SENSITIVE_KEY = /(password|passwd|secret|token|cookie|authorization|api[_-]?key|database_url|salt|digest|credential|private[_-]?key)/i

/** Never render secrets in the audit detail drawer, even if a bad `before`/`after`
 *  payload ever carried one. */
export function redactSensitive(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactSensitive)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        k,
        SENSITIVE_KEY.test(k) ? '[oculto]' : redactSensitive(v),
      ]),
    )
  }
  return value
}

export function auditActorLabel(entry: {
  actorFullName: string | null
  actorEmail: string | null
}): string {
  return entry.actorFullName || entry.actorEmail || 'Sistema'
}
