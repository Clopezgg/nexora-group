import { apiFetch } from './httpClient'

export interface ContractInstallment {
  installmentId: string
  sequence: number
  periodYear: number
  periodMonth: number
  periodLabel: string
  dueDate: string
  scheduledAmount: string
  retentionAmount: string
  netDue: string
  paid: string
  remaining: string
  status: string
}

export interface ContractSchedule {
  id: string
  companyId: string
  supplierContractId: string
  projectId: string | null
  currencyCode: string
  scheduleType: string
  totalScheduled: string
  status: string
  installments: ContractInstallment[]
}

export interface ContractPaymentSummary {
  contractValue: string
  totalScheduledToDate: string
  paidAccumulated: string
  contractBalance: string
  overdueBalance: string
  nextDuePeriod: string | null
  nextDueAmount: string | null
  currencyCode: string
}

export interface FifoPreviewItem {
  installmentId: string
  periodLabel: string
  amountApplied: string
}

export const contractPaymentService = {
  getByContract: (contractId: string) =>
    apiFetch<ContractSchedule>(`/contract-payments/by-contract/${encodeURIComponent(contractId)}`),

  createMonthlySchedule: (body: {
    supplierContractId: string
    startPeriod: string
    months: number
    monthlyAmount: string
  }) =>
    apiFetch<ContractSchedule>('/contract-payments/schedules', {
      method: 'POST',
      body: JSON.stringify({ scheduleType: 'MONTHLY', ...body }),
    }),

  summary: (scheduleId: string, asOf?: string) => {
    const qs = asOf ? `?asOf=${encodeURIComponent(asOf)}` : ''
    return apiFetch<ContractPaymentSummary>(
      `/contract-payments/schedules/${encodeURIComponent(scheduleId)}/summary${qs}`,
    )
  },

  fifoPreview: (scheduleId: string, amount: string, asOf?: string) =>
    apiFetch<FifoPreviewItem[]>(
      `/contract-payments/schedules/${encodeURIComponent(scheduleId)}/fifo-preview`,
      { method: 'POST', body: JSON.stringify({ amount, asOf }) },
    ),
}
