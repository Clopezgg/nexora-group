import { apiFetch } from './httpClient'

export interface SupplierInvoice {
  id: string
  supplierName: string
  invoiceNumber: string
  scope: string
  currencyCode: string
  amount: number
  taxAmount: number
  amountPaid: number
  dueDate: string
  status: string
}

export interface CustomerInvoice {
  id: string
  customerName: string
  invoiceNumber: string
  scope: string
  currencyCode: string
  amount: number
  amountCollected: number
  dueDate: string
  status: string
}

function normalizeSupplierInvoice(invoice: SupplierInvoice): SupplierInvoice {
  return {
    ...invoice,
    amount: Number(invoice.amount),
    taxAmount: Number(invoice.taxAmount),
    amountPaid: Number(invoice.amountPaid),
  }
}

function normalizeCustomerInvoice(invoice: CustomerInvoice): CustomerInvoice {
  return {
    ...invoice,
    amount: Number(invoice.amount),
    amountCollected: Number(invoice.amountCollected),
  }
}

export const apService = {
  listInvoices: async (companyId: string) =>
    (
      await apiFetch<SupplierInvoice[]>(
        `/ap/supplier-invoices?companyId=${encodeURIComponent(companyId)}`,
      )
    ).map(normalizeSupplierInvoice),
  createInvoice: async (payload: Record<string, unknown>) =>
    normalizeSupplierInvoice(
      await apiFetch<SupplierInvoice>('/ap/supplier-invoices', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    ),
  getInvoice: async (id: string) =>
    normalizeSupplierInvoice(await apiFetch<SupplierInvoice>(`/ap/supplier-invoices/${id}`)),
  approveInvoice: async (id: string) =>
    normalizeSupplierInvoice(
      await apiFetch<SupplierInvoice>(`/ap/supplier-invoices/${id}/approve`, { method: 'POST' }),
    ),
  pay: (id: string, payload: Record<string, unknown>) =>
    apiFetch(`/ap/supplier-invoices/${id}/payments`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}

export const arService = {
  listInvoices: async (companyId: string) =>
    (
      await apiFetch<CustomerInvoice[]>(
        `/ar/customer-invoices?companyId=${encodeURIComponent(companyId)}`,
      )
    ).map(normalizeCustomerInvoice),
  createInvoice: async (payload: Record<string, unknown>) =>
    normalizeCustomerInvoice(
      await apiFetch<CustomerInvoice>('/ar/customer-invoices', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    ),
  getInvoice: async (id: string) =>
    normalizeCustomerInvoice(await apiFetch<CustomerInvoice>(`/ar/customer-invoices/${id}`)),
  approveInvoice: async (id: string) =>
    normalizeCustomerInvoice(
      await apiFetch<CustomerInvoice>(`/ar/customer-invoices/${id}/approve`, { method: 'POST' }),
    ),
  collect: (id: string, payload: Record<string, unknown>) =>
    apiFetch(`/ar/customer-invoices/${id}/receipts`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
