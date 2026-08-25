import { apiFetch } from './httpClient'
import type {
  Customer,
  Lead,
  LeadConversionResult,
  Opportunity,
  Quotation,
  SalesContract,
} from '../types/crm'

export const crmService = {
  listCustomers: (companyId: string) =>
    apiFetch<Customer[]>(`/crm/customers?companyId=${encodeURIComponent(companyId)}`),
  createCustomer: (payload: {
    companyId: string
    legalName: string
    tradeName?: string
    taxId?: string
    contactName?: string
    email?: string
    phone?: string
    address?: string
  }) => apiFetch<Customer>('/crm/customers', { method: 'POST', body: JSON.stringify(payload) }),

  listLeads: (companyId: string) =>
    apiFetch<Lead[]>(`/crm/leads?companyId=${encodeURIComponent(companyId)}`),
  createLead: (payload: {
    companyId: string
    name: string
    contactName?: string
    email?: string
    phone?: string
    source?: string
  }) => apiFetch<Lead>('/crm/leads', { method: 'POST', body: JSON.stringify(payload) }),
  convertLead: (leadId: string) =>
    apiFetch<LeadConversionResult>(`/crm/leads/${leadId}/convert`, { method: 'POST' }),

  listOpportunities: (companyId: string) =>
    apiFetch<Opportunity[]>(`/crm/opportunities?companyId=${encodeURIComponent(companyId)}`),

  listQuotations: (companyId: string) =>
    apiFetch<Quotation[]>(`/crm/quotations?companyId=${encodeURIComponent(companyId)}`),
  createQuotation: (payload: {
    companyId: string
    opportunityId: string
    customerId: string
    projectId?: string
    quotationNumber: string
    amount: string
    currencyCode: string
    validUntil?: string
    description?: string
  }) => apiFetch<Quotation>('/crm/quotations', { method: 'POST', body: JSON.stringify(payload) }),
  acceptQuotation: (quotationId: string) =>
    apiFetch<Quotation>(`/crm/quotations/${quotationId}/accept`, { method: 'POST' }),
  convertQuotation: (quotationId: string, payload: { contractNumber: string; startDate: string }) =>
    apiFetch<SalesContract>(`/crm/quotations/${quotationId}/convert`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listSalesContracts: (companyId: string) =>
    apiFetch<SalesContract[]>(`/crm/sales-contracts?companyId=${encodeURIComponent(companyId)}`),
  billSalesContract: (
    contractId: string,
    payload: {
      invoiceNumber: string
      invoiceDate: string
      dueDate: string
      revenueAccountId: string
      receivableAccountId: string
      description?: string
    },
  ) =>
    apiFetch<SalesContract>(`/crm/sales-contracts/${contractId}/bill`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
