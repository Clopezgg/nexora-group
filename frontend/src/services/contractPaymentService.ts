import { apiFetch } from './httpClient'

export type ContractInstallmentKind = 'ADVANCE' | 'REGULAR' | 'RETENTION_RELEASE'

export interface ContractInstallment {
  installmentId: string
  sequence: number
  installmentKind: ContractInstallmentKind
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
  regularNumber: number | null
  regularCount: number | null
}

export interface ContractSchedule {
  id: string
  companyId: string
  supplierContractId: string
  projectId: string | null
  currencyCode: string
  scheduleType: string
  dueDay: number | null
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
  advanceScheduled: string
  regularScheduled: string
  totalContractualScheduled: string
  advancePaid: string
  advanceRemaining: string
  retentionOutstanding: string
}

export interface FifoPreviewItem {
  installmentId: string
  periodLabel: string
  amountApplied: string
}

export interface LedgerAllocation {
  paymentId: string
  paymentDate: string
  installmentSequence: number
  installmentPeriodLabel: string
  amountApplied: string
  bankTransactionReference: string | null
  reversed: boolean
}

export interface ContractLedgerEntry {
  scheduleId: string
  supplierContractId: string
  contractNumber: string
  supplierLegalName: string | null
  projectId: string | null
  currencyCode: string
  contractValue: string
  scheduledToDate: string
  paidAccumulated: string
  contractBalance: string
  overdueBalance: string
  installments: ContractInstallment[]
  allocations: LedgerAllocation[]
}

export interface ContractPaymentLedger {
  companyId: string
  asOf: string
  entries: ContractLedgerEntry[]
  totalContractValue: string
  totalPaidAccumulated: string
  totalContractBalance: string
}

export const contractPaymentService = {
  getByContract: (contractId: string) =>
    apiFetch<ContractSchedule>(`/contract-payments/by-contract/${encodeURIComponent(contractId)}`),

  // Modo canónico (§16-§20): el backend calcula el anticipo + N mensualidades.
  createContractPlan: (body: {
    supplierContractId: string
    regularMonths: number
    dueDay: number
    firstPeriod: string
    advanceAmount?: string
    advanceDueDate?: string
  }) =>
    apiFetch<ContractSchedule>('/contract-payments/schedules', {
      method: 'POST',
      body: JSON.stringify({ scheduleType: 'MONTHLY', ...body }),
    }),

  rebuildPlan: (
    scheduleId: string,
    body: {
      reason: string
      regularMonths: number
      dueDay: number
      firstPeriod: string
      advanceAmount?: string
      advanceDueDate?: string
      retentionPercentage?: string
    },
  ) =>
    apiFetch<ContractSchedule>(
      `/contract-payments/schedules/${encodeURIComponent(scheduleId)}/rebuild`,
      { method: 'POST', body: JSON.stringify(body) },
    ),

  prepareAdvanceInvoice: (
    scheduleId: string,
    body: { payableAccountId: string; costCenterId?: string; amount?: string },
  ) =>
    apiFetch<{ invoiceId: string; advanceInstallmentId: string; amount: string }>(
      `/contract-payments/schedules/${encodeURIComponent(scheduleId)}/advance-invoice`,
      { method: 'POST', body: JSON.stringify(body) },
    ),

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

  ledger: (companyId: string, asOf?: string) => {
    const params = new URLSearchParams({ companyId })
    if (asOf) params.set('asOf', asOf)
    return apiFetch<ContractPaymentLedger>(`/reports/contract-payment-ledger?${params.toString()}`)
  },
}
