import { apiFetch } from './httpClient'

export interface SupplierInvoice {
  id: string
  supplierId: string
  invoiceNumber: string
  scope: string
  projectId: string | null
  currencyCode: string
  amount: number
  taxAmount: number
  amountPaid: number
  dueDate: string
  status: string
  supplierContractId: string | null
}

export interface SupplierPayment {
  id: string
  supplierInvoiceId: string
  treasuryAccountId: string
  amount: number
  paymentDate: string
  accountingDocumentId: string
  reversalAccountingDocumentId: string | null
  reversedAt: string | null
  reversedByUserId: string | null
  reversalReason: string | null
}

export interface PaymentPlanItem {
  id: string
  supplierInvoiceId: string
  sequence: number
  dueDate: string
  amount: number
  note: string | null
}

export interface PaymentPlanItemInput {
  dueDate: string
  amount: string
  note?: string
}

export interface PaymentProposalItem {
  invoiceId: string
  invoiceNumber: string
  supplierName: string | null
  dueDate: string
  remaining: string
  overdue: boolean
}

export interface PaymentProposal {
  horizonDays: number
  asOf: string
  total: string
  items: PaymentProposalItem[]
}

export interface CustomerInvoice {
  id: string
  customerId: string
  invoiceNumber: string
  scope: string
  projectId: string | null
  currencyCode: string
  amount: number
  amountCollected: number
  dueDate: string
  status: string
}

export interface CustomerReceipt {
  id: string
  customerInvoiceId: string
  treasuryAccountId: string
  amount: number
  receiptDate: string
  accountingDocumentId: string
  reversalAccountingDocumentId: string | null
  reversedAt: string | null
  reversedByUserId: string | null
  reversalReason: string | null
}

export interface BusinessReversalResponse {
  originalId: string
  invoiceId: string
  originalAccountingDocumentId: string
  reversalAccountingDocumentId: string
  invoiceStatus: string
  appliedAmountAfterReversal: number
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
  submitForApproval: async (id: string, assignedTo: string) =>
    normalizeSupplierInvoice(
      await apiFetch<SupplierInvoice>(`/ap/supplier-invoices/${id}/submit-for-approval`, {
        method: 'POST',
        body: JSON.stringify({ assignedTo }),
      }),
    ),
  pay: (id: string, payload: Record<string, unknown>, idempotencyKey: string) =>
    apiFetch<SupplierPayment>(`/ap/supplier-invoices/${id}/payments`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload),
    }),
  listPayments: (invoiceId: string) =>
    apiFetch<SupplierPayment[]>(`/ap/supplier-invoices/${invoiceId}/payments`),
  getPaymentPlan: (invoiceId: string) =>
    apiFetch<PaymentPlanItem[]>(`/ap/supplier-invoices/${invoiceId}/payment-plan`),
  paymentProposal: (companyId: string, horizonDays = 14) =>
    apiFetch<PaymentProposal>(
      `/ap/payment-proposal?companyId=${encodeURIComponent(companyId)}&horizonDays=${horizonDays}`,
    ),
  setPaymentPlan: (invoiceId: string, installments: PaymentPlanItemInput[]) =>
    apiFetch<PaymentPlanItem[]>(`/ap/supplier-invoices/${invoiceId}/payment-plan`, {
      method: 'PUT',
      body: JSON.stringify({ installments }),
    }),
  reversePayment: (paymentId: string, reason: string) =>
    apiFetch<BusinessReversalResponse>(`/ap/supplier-payments/${paymentId}/reverse`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
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
  collect: (id: string, payload: Record<string, unknown>, idempotencyKey: string) =>
    apiFetch<CustomerReceipt>(`/ar/customer-invoices/${id}/receipts`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload),
    }),
  listReceipts: (invoiceId: string) =>
    apiFetch<CustomerReceipt[]>(`/ar/customer-invoices/${invoiceId}/receipts`),
  reverseReceipt: (receiptId: string, reason: string) =>
    apiFetch<BusinessReversalResponse>(`/ar/customer-receipts/${receiptId}/reverse`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
}
