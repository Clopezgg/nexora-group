import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PurchaseOrdersPage } from '../src/features/procurement/PurchaseOrdersPage'

vi.mock('../src/hooks/useActiveCompany', () => ({
  useActiveCompany: () => ({
    activeCompanyId: 'c1',
    activeCompany: { id: 'c1', name: 'Nexora', functionalCurrencyCode: 'HNL' },
    isLoading: false,
  }),
}))

describe('PurchaseOrdersPage three-way match', () => {
  it('ejecuta el match con una factura real vinculada a la PO', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      let body: unknown = []
      if (url.includes('/procurement/purchase-orders?')) {
        body = [{
          id: 'po1', companyId: 'c1', poNumber: 'PO-001', supplierId: 's1', projectId: null,
          currencyCode: 'HNL', status: 'RECEIVED', lines: [{
            id: 'line1', itemId: 'item1', description: 'Material', quantity: '10.0000',
            unitPrice: '100.0000', taxAmount: '150.00', quantityReceived: '10.0000',
          }],
        }]
      } else if (url.includes('/procurement/suppliers?')) {
        body = [{ id: 's1', companyId: 'c1', legalName: 'Proveedor Uno' }]
      } else if (url.includes('/ap/supplier-invoices?')) {
        body = [{
          id: 'inv1', supplierId: 's1', invoiceNumber: 'FAC-001', scope: 'GENERAL', projectId: null,
          currencyCode: 'HNL', amount: '1000.00', taxAmount: '150.00', amountPaid: '0.00',
          dueDate: '2026-09-30', status: 'DRAFT', supplierContractId: null,
          contractInstallmentId: null, purchaseOrderId: 'po1',
        }]
      } else if (url.includes('/procurement/three-way-match?')) {
        body = []
      } else if (url.endsWith('/procurement/three-way-match') && init?.method === 'POST') {
        body = {
          id: 'twm1', purchaseOrderId: 'po1', supplierInvoiceId: 'inv1',
          supplierInvoiceAmount: '1150.00', supplierInvoiceQuantity: '10.0000', matchKind: 'FINANCIAL',
          status: 'MATCHED', orderedAmount: '1150.00', receivedQuantity: '10.0000', exceptions: [],
        }
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
    })
    vi.stubGlobal('fetch', fetchMock)
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <PurchaseOrdersPage />
      </QueryClientProvider>,
    )

    fireEvent.click(await screen.findByRole('button', { name: 'Conciliar factura de PO-001' }))
    fireEvent.change(screen.getByLabelText('Factura de proveedor'), { target: { value: 'inv1' } })
    fireEvent.change(screen.getByLabelText('Cantidad facturada'), { target: { value: '10.0000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ejecutar conciliación' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/procurement/three-way-match'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            purchaseOrderId: 'po1',
            supplierInvoiceId: 'inv1',
            supplierInvoiceQuantity: '10.0000',
          }),
        }),
      )
    })
  })
})
