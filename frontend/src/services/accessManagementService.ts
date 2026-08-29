import { apiFetch } from './httpClient'

export interface RoleAccess {
  id: string
  name: string
  assigned: boolean
}

export interface CompanyAccess {
  id: string
  name: string
  assigned: boolean
}

export interface ProjectAccess {
  id: string
  companyId: string
  code: string | null
  name: string
  assigned: boolean
}

export interface UserAccessSummary {
  userId: string
  roles: RoleAccess[]
  companies: CompanyAccess[]
  projects: ProjectAccess[]
}

export const accessManagementService = {
  getUserAccess: (userId: string, companyId?: string) =>
    apiFetch<UserAccessSummary>(
      `/access-management/users/${userId}${companyId ? `?companyId=${encodeURIComponent(companyId)}` : ''}`,
    ),
  grantRole: (userId: string, roleId: string) =>
    apiFetch<UserAccessSummary>(`/access-management/users/${userId}/roles/${roleId}`, {
      method: 'PUT',
    }),
  revokeRole: (userId: string, roleId: string) =>
    apiFetch<UserAccessSummary>(`/access-management/users/${userId}/roles/${roleId}`, {
      method: 'DELETE',
    }),
  grantCompany: (userId: string, companyId: string) =>
    apiFetch<UserAccessSummary>(`/access-management/users/${userId}/companies/${companyId}`, {
      method: 'PUT',
    }),
  revokeCompany: (userId: string, companyId: string) =>
    apiFetch<UserAccessSummary>(`/access-management/users/${userId}/companies/${companyId}`, {
      method: 'DELETE',
    }),
  grantProject: (userId: string, projectId: string) =>
    apiFetch<UserAccessSummary>(`/access-management/users/${userId}/projects/${projectId}`, {
      method: 'PUT',
    }),
  revokeProject: (userId: string, projectId: string) =>
    apiFetch<UserAccessSummary>(`/access-management/users/${userId}/projects/${projectId}`, {
      method: 'DELETE',
    }),
}