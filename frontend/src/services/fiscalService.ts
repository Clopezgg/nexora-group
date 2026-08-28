import { apiFetch } from './httpClient'
import type { CurrentFiscalPeriod, FiscalPeriod, FiscalPeriodStatus, FiscalYear } from '../types/fiscal'

export const fiscalService = {
  listYears: (companyId: string) => apiFetch<FiscalYear[]>(`/fiscal/years?companyId=${companyId}`),
  createYear: (payload: { companyId: string; code: string; startDate: string; endDate: string }) =>
    apiFetch<FiscalYear>('/fiscal/years', { method: 'POST', body: JSON.stringify(payload) }),
  generateMonthlyPeriods: (fiscalYearId: string) =>
    apiFetch<FiscalPeriod[]>(`/fiscal/years/${fiscalYearId}/generate-monthly-periods`, { method: 'POST' }),
  listPeriods: (companyId: string) => apiFetch<FiscalPeriod[]>(`/fiscal/periods?companyId=${companyId}`),
  getCurrent: (companyId: string) => apiFetch<CurrentFiscalPeriod>(`/fiscal/periods/current?companyId=${companyId}`),
  setPeriodStatus: (periodId: string, status: FiscalPeriodStatus, reason?: string) =>
    apiFetch<FiscalPeriod>(`/fiscal/periods/${periodId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status, reason }),
    }),
}
