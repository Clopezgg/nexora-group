export interface Worker {
  id: string
  companyId: string
  fullName: string
  roleTitle: string | null
  standardHourlyRate: string
  active: boolean
}

export interface Crew {
  id: string
  companyId: string
  projectId: string | null
  name: string
  status: string
}

export interface CrewWithMembers extends Crew {
  members: Worker[]
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
