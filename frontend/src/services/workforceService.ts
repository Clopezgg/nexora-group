import { apiFetch } from './httpClient'
import type { Crew, CrewWithMembers, TimeEntry, Worker } from '../types/workforce'

export const workforceService = {
  listWorkers: (companyId: string) => apiFetch<Worker[]>(`/workforce/workers?companyId=${companyId}`),
  createWorker: (payload: {
    companyId: string
    fullName: string
    roleTitle?: string
    standardHourlyRate: string
  }) => apiFetch<Worker>('/workforce/workers', { method: 'POST', body: JSON.stringify(payload) }),

  listCrews: (companyId: string) => apiFetch<Crew[]>(`/workforce/crews?companyId=${companyId}`),
  createCrew: (payload: { companyId: string; name: string; projectId?: string }) =>
    apiFetch<Crew>('/workforce/crews', { method: 'POST', body: JSON.stringify(payload) }),
  getCrew: (crewId: string) => apiFetch<CrewWithMembers>(`/workforce/crews/${crewId}`),
  addCrewMember: (crewId: string, workerId: string) =>
    apiFetch(`/workforce/crews/${crewId}/members`, {
      method: 'POST',
      body: JSON.stringify({ workerId }),
    }),
  removeCrewMember: (crewId: string, workerId: string) =>
    apiFetch(`/workforce/crews/${crewId}/members/${workerId}`, { method: 'DELETE' }),

  listTimeEntries: (companyId: string) =>
    apiFetch<TimeEntry[]>(`/workforce/time-entries?companyId=${companyId}`),
  createTimeEntry: (payload: {
    companyId: string
    workerId: string
    scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
    projectId?: string
    workDate: string
    hoursWorked: string
    hourlyRate: string
  }) => apiFetch<TimeEntry>('/workforce/time-entries', { method: 'POST', body: JSON.stringify(payload) }),

  approveTimeEntry: (timeEntryId: string, approvedHours?: string) =>
    apiFetch<TimeEntry>(`/workforce/time-entries/${timeEntryId}/approve`, {
      method: 'POST',
      body: JSON.stringify(approvedHours !== undefined ? { approvedHours } : {}),
    }),
  rejectTimeEntry: (timeEntryId: string) =>
    apiFetch<TimeEntry>(`/workforce/time-entries/${timeEntryId}/reject`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
}
