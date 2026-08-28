export interface Company {
  id: string
  name: string
  code: string | null
  legalName: string | null
  functionalCurrencyCode: string | null
  country: string | null
  fiscalId: string | null
}

export interface Account {
  id: string
  code: string
  name: string
  accountType: string
  parentId: string | null
  isPostable: boolean
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
