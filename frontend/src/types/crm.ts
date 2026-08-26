export interface Customer {
  id: string
  companyId: string
  legalName: string
  tradeName: string | null
  taxId: string | null
  contactName: string | null
  email: string | null
  phone: string | null
  address: string | null
  status: string
}

export interface Lead {
  id: string
  companyId: string
  name: string
  contactName: string | null
  email: string | null
  phone: string | null
  source: string | null
  status: string
  convertedCustomerId: string | null
}

export interface Opportunity {
  id: string
  companyId: string
  leadId: string | null
  customerId: string
  name: string
  stage: string
  estimatedAmount: string | null
  currencyCode: string | null
}

export interface LeadConversionResult {
  lead: Lead
  customer: Customer
  opportunity: Opportunity
}

export interface Quotation {
  id: string
  companyId: string
  opportunityId: string
  customerId: string
  projectId: string | null
  quotationNumber: string
  amount: string
  currencyCode: string
  status: string
  validUntil: string | null
  description: string | null
}

export interface SalesContract {
  id: string
  companyId: string
  quotationId: string
  customerId: string
  projectId: string | null
  contractNumber: string
  scope: string
  amount: string
  currencyCode: string
  startDate: string
  status: string
  customerInvoiceId: string | null
}
