export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED'
export type ApprovalPriority = 'LOW' | 'NORMAL' | 'HIGH'

export interface ApprovalRequestEntry {
  id: string
  policyId: string | null
  entityType: string
  entityId: string
  companyId: string
  projectId: string | null
  module: string
  requestedBy: string
  assignedTo: string | null
  assignedRole: string | null
  status: ApprovalStatus
  priority: ApprovalPriority
  amount: string | null
  comment: string | null
  decidedBy: string | null
  decidedAt: string | null
  createdAt: string
}
