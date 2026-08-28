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
