import { apiFetch } from './httpClient'
import type { Account, Company } from '../types/masterData'

export const masterDataService = {
  listCompanies: () => apiFetch<Company[]>('/master-data/companies'),
  createCompany: (payload: { name: string; functionalCurrencyCode: string }) =>
    apiFetch<Company>('/master-data/companies', { method: 'POST', body: JSON.stringify(payload) }),
  listAccounts: (companyId: string) =>
    apiFetch<Account[]>(`/master-data/accounts?companyId=${companyId}`),
  createAccount: (payload: {
    companyId: string
    code: string
    name: string
    accountType: string
  }) =>
    apiFetch<Account>('/master-data/accounts', { method: 'POST', body: JSON.stringify(payload) }),
}
