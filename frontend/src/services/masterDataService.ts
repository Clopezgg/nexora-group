import { apiFetch } from './httpClient'
import type { Account, Company, CompanyUser } from '../types/masterData'

export interface CompanyProfileInput {
  name?: string
  code?: string
  legalName?: string
  functionalCurrencyCode?: string
  country?: string
  fiscalId?: string
}

export const masterDataService = {
  listCompanies: () => apiFetch<Company[]>('/master-data/companies'),
  listUsers: (companyId: string) =>
    apiFetch<CompanyUser[]>(`/master-data/users?companyId=${companyId}`),
  createUser: (payload: {
    companyId: string
    email: string
    fullName: string
    password: string
    roleName: string
  }) => apiFetch<CompanyUser>('/master-data/users', { method: 'POST', body: JSON.stringify(payload) }),
  createCompany: (payload: {
    name: string
    code?: string
    legalName?: string
    functionalCurrencyCode: string
    country?: string
    fiscalId?: string
  }) => apiFetch<Company>('/master-data/companies', { method: 'POST', body: JSON.stringify(payload) }),
  updateCompany: (companyId: string, payload: CompanyProfileInput) =>
    apiFetch<Company>(`/master-data/companies/${companyId}/profile`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listAccounts: async (
    companyId: string,
    options?: { includeNonPostable?: boolean },
  ) => {
    const accounts = await apiFetch<Account[]>(`/master-data/accounts?companyId=${companyId}`)
    return options?.includeNonPostable
      ? accounts
      : accounts.filter((account) => account.isPostable !== false)
  },
  createAccount: (payload: {
    companyId: string
    code: string
    name: string
    accountType: string
    parentId?: string
    isPostable?: boolean
  }) =>
    apiFetch<Account>('/master-data/accounts', { method: 'POST', body: JSON.stringify(payload) }),
}
