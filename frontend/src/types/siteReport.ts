export interface DailySiteReportPhoto {
  id: string
  dailySiteReportId: string
  evidenceId: string
  createdAt: string
}

export interface DailySiteReport {
  id: string
  projectId: string
  reportDate: string
  weather: string | null
  workforceSummary: string | null
  activitiesPerformed: string
  equipmentUsed: string | null
  materialsUsed: string | null
  incidents: string | null
  observations: string | null
  authorId: string
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED'
  approvedById: string | null
  approvedAt: string | null
  photos: DailySiteReportPhoto[]
}
