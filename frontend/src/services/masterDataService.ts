import { apiFetch } from './httpClient'
import type { Company } from '../types/company'

export const masterDataService = {
  listCompanies: () => apiFetch<Company[]>('/master-data/companies'),
}
