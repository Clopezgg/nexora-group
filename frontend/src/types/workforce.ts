export interface Worker {
  id: string
  companyId: string
  fullName: string
  roleTitle: string | null
  standardHourlyRate: string
  active: boolean
}

export type TimeEntryStatus = 'SUBMITTED' | 'APPROVED' | 'REJECTED'

export interface TimeEntry {
  id: string
  companyId: string
  workerId: string
  scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
  projectId: string | null
  workDate: string
  hoursWorked: string
  hourlyRate: string
  status: TimeEntryStatus
  approvedHours: string | null
  laborCost: string | null
  approvedById: string | null
  approvedAt: string | null
}
