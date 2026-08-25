export interface QualityInspection {
  id: string
  projectId: string
  wbsNodeId: string | null
  inspectionType: string
  inspectionDate: string
  inspectorId: string
  result: 'PENDING' | 'PASS' | 'FAIL'
  notes: string | null
  evidenceId: string | null
}

export interface NonConformance {
  id: string
  projectId: string
  qualityInspectionId: string | null
  description: string
  responsibleUserId: string
  dueDate: string | null
  status: 'OPEN' | 'CLOSED'
  closedAt: string | null
  evidenceId: string | null
}

export interface CorrectiveAction {
  id: string
  nonConformanceId: string
  description: string
  responsibleUserId: string
  dueDate: string
  status: 'OPEN' | 'COMPLETED'
  completedAt: string | null
  evidenceId: string | null
}
