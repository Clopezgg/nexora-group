export const RFI_STATUSES = ['OPEN', 'ANSWERED', 'CLOSED'] as const
export type RfiStatus = (typeof RFI_STATUSES)[number]

export interface Rfi {
  id: string
  companyId: string
  projectId: string
  wbsNodeId: string | null
  number: string
  subject: string
  question: string
  response: string | null
  responsible: string | null
  requestedBy: string
  respondedBy: string | null
  dueDate: string | null
  respondedAt: string | null
  closedAt: string | null
  status: RfiStatus
  createdAt: string
}
