export type SafetySeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface SafetyObservation {
  id: string
  projectId: string
  observationDate: string
  category: string
  description: string
  severity: SafetySeverity
  responsibleUserId: string | null
  correctiveAction: string | null
  status: 'OPEN' | 'CLOSED'
  closedAt: string | null
  evidenceId: string | null
}

export interface SafetyIncident {
  id: string
  projectId: string
  incidentDate: string
  description: string
  severity: SafetySeverity
  responsibleUserId: string | null
  correctiveAction: string | null
  status: 'OPEN' | 'CLOSED'
  closedAt: string | null
  evidenceId: string | null
}
