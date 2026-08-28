export interface FiscalYear {
  id: string
  companyId: string
  code: string
  startDate: string
  endDate: string
}

export type FiscalPeriodStatus = 'OPEN' | 'SOFT_CLOSED' | 'CLOSED'

export interface FiscalPeriod {
  id: string
  fiscalYearId: string
  companyId: string
  periodNumber: number
  startDate: string
  endDate: string
  status: FiscalPeriodStatus
}

export interface CurrentFiscalPeriod {
  fiscalYear: FiscalYear | null
  period: FiscalPeriod | null
}
