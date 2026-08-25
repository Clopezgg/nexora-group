export interface FixedAsset {
  id: string
  companyId: string
  category: string
  name: string
  acquisitionDate: string
  cost: string
  currencyCode: string
  usefulLifeMonths: number
  salvageValue: string
  location: string | null
  responsible: string | null
  status: 'ACTIVE' | 'UNDER_MAINTENANCE' | 'DISPOSED' | 'RETIRED'
  scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
  projectId: string | null
  costCenterId: string | null
  depreciationExpenseAccountId: string
  accumulatedDepreciationAccountId: string
}

export interface DepreciationEntry {
  id: string
  assetId: string
  periodStart: string
  periodEnd: string
  amount: string
  accountingDocumentId: string | null
}
