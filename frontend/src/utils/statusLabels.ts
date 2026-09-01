const STATUS_LABELS: Record<string, string> = {
  PLANNING: 'Planificación',
  PLANNED: 'Planificado',
  ACTIVE: 'Activo / En ejecución',
  ON_HOLD: 'Pausado',
  COMPLETED: 'Completado',
  CLOSED: 'Cerrado',
  CANCELLED: 'Cancelado',
  DRAFT: 'Borrador',
  SUBMITTED: 'Enviado',
  REVIEW: 'En revisión',
  APPROVED: 'Aprobado',
  REJECTED: 'Rechazado',
  IMPLEMENTED: 'Implementado',
  POSTED: 'Contabilizado',
  REVERSED: 'Revertido',
  OPEN: 'Abierto',
  SOFT_CLOSED: 'Cierre preliminar',
  PARTIALLY_PAID: 'Pagado parcialmente',
  PAID: 'Pagado',
  PARTIALLY_COLLECTED: 'Cobrado parcialmente',
  COLLECTED: 'Cobrado',
  SENT: 'Enviado',
  ACCEPTED: 'Aceptado',
  BILLED: 'Facturado',
}

export function statusLabel(status: string | null | undefined): string {
  if (!status) return '—'
  return STATUS_LABELS[status] ?? status.replaceAll('_', ' ')
}

// Mapeos por dominio (CORRECTIVA §25) — sin mezclar Project / Supplier /
// SupplierContract. El usuario nunca ve el enum crudo.

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  PLANNING: 'Planificación',
  ACTIVE: 'Activo',
  ON_HOLD: 'Pausado',
  COMPLETED: 'Completado',
  CLOSED: 'Cerrado',
  CANCELLED: 'Cancelado',
  ARCHIVED: 'Archivado',
}

export const SUPPLIER_STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Activo',
  INACTIVE: 'Inactivo',
  BLOCKED: 'Bloqueado',
  ARCHIVED: 'Archivado',
}

export const SUPPLIER_PARTY_ROLE_LABELS: Record<string, string> = {
  SUPPLIER: 'Proveedor',
  CONTRACTOR: 'Contratista',
  BOTH: 'Proveedor y contratista',
}

export const SUPPLIER_CONTRACT_STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Borrador',
  ACTIVE: 'Activo',
  COMPLETED: 'Completado',
  TERMINATED: 'Terminado anticipadamente',
}

const _labeler = (map: Record<string, string>) => (v: string | null | undefined) =>
  !v ? '—' : map[v] ?? v.replaceAll('_', ' ')

export const projectStatusLabel = _labeler(PROJECT_STATUS_LABELS)
export const supplierStatusLabel = _labeler(SUPPLIER_STATUS_LABELS)
export const supplierPartyRoleLabel = _labeler(SUPPLIER_PARTY_ROLE_LABELS)
export const supplierContractStatusLabel = _labeler(SUPPLIER_CONTRACT_STATUS_LABELS)
