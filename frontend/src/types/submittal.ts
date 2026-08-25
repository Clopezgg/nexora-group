export const SUBMITTAL_STATUSES = ['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED'] as const
export type SubmittalStatus = (typeof SUBMITTAL_STATUSES)[number]

export interface Submittal {
  id: string
  companyId: string
  projectId: string
  wbsNodeId: string | null
  number: string
  revision: number
  title: string
  description: string | null
  supplierId: string | null
  contractId: string | null
  status: SubmittalStatus
  submittedBy: string
  submittedAt: string
  dueDate: string | null
  reviewerResponse: string | null
  reviewedBy: string | null
  responseRecordedAt: string | null
  decidedBy: string | null
  decidedAt: string | null
  evidenceId: string | null
  createdAt: string
}
