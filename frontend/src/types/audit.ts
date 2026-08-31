export interface AuditLogEntry {
  id: string
  actorUserId: string | null
  actorFullName: string | null
  actorEmail: string | null
  action: string
  entityType: string
  entityId: string
  companyId: string
  projectId: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  correlationId: string
  createdAt: string
}
