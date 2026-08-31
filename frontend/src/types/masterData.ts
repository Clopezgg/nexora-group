export interface Company {
  id: string
  name: string
  code: string | null
  legalName: string | null
  functionalCurrencyCode: string | null
  country: string | null
  fiscalId: string | null
  voucherPayerName: string | null
  defaultThemeId: string | null
  defaultDensity: string | null
  voucherApproverName: string | null
}

export interface Account {
  id: string
  code: string
  name: string
  accountType: string
  parentId: string | null
  isPostable: boolean
  cashFlowActivity?: string | null
}

export interface CompanyUser {
  id: string
  email: string
  fullName: string
  roles: string[]
}

export interface ControllingDimension {
  id: string
  companyId: string
  code: string
  name: string
}

export type ResourcePostingSource = 'FUEL' | 'MAINTENANCE' | 'LABOR'

export interface ResourcePostingConfig {
  id: string
  companyId: string
  sourceType: ResourcePostingSource
  expenseAccountId: string
  offsetAccountId: string
  active: boolean
}
