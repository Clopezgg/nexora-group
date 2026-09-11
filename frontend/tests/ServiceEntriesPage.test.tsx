import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ServiceEntriesPage } from '../src/features/procurement/ServiceEntriesPage'

vi.mock('../src/hooks/useActiveCompany', () => ({
  useActiveCompany: () => ({
    activeCompanyId: 'c1',
    activeCompany: { id: 'c1', name: 'Nexora', functionalCurrencyCode: 'HNL' },
    isLoading: false,
  }),
}))

describe('ServiceEntriesPage', () => {
  it('lista avances reales y registra una aceptación operativa', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      let body: unknown = []
      if (url.includes('/procurement/purchase-orders?')) {
        body = [{
          id: 'po1', companyId: 'c1', poNumber: 'PO-001', supplierId: 's1', projectId: null,
          currencyCode: 'HNL', status: 'SENT', lines: [],
        }]
      } else if (url.includes('/procurement/service-entries?')) {
        body = [{
          id: 'sen0', entryNumber: 'SEN-000', purchaseOrderId: 'po1',
          periodStart: '2026-07-01', periodEnd: '2026-07-31',
          progressPercentage: '20.00', acceptedValue: '200.00', approvedById: 'u1', evidenceId: null,
        }]
      } else if (url.endsWith('/procurement/service-entries') && init?.method === 'POST') {
        body = { id: 'sen1', entryNumber: 'SEN-001' }
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
    })
    vi.stubGlobal('fetch', fetchMock)
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <ServiceEntriesPage />
      </QueryClientProvider>,
    )

    expect(await screen.findByText('SEN-000')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Orden de compra'), { target: { value: 'po1' } })
    fireEvent.change(screen.getByLabelText('Inicio del período'), { target: { value: '2026-08-01' } })
    fireEvent.change(screen.getByLabelText('Fin del período'), { target: { value: '2026-08-31' } })
    fireEvent.change(screen.getByLabelText('Avance aceptado (%)'), { target: { value: '35.00' } })
    fireEvent.change(screen.getByLabelText('Valor aceptado'), { target: { value: '350.00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar entrada' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/procurement/service-entries'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          purchaseOrderId: 'po1',
          periodStart: '2026-08-01',
          periodEnd: '2026-08-31',
          progressPercentage: '35.00',
          acceptedValue: '350.00',
        }),
      }),
    ))
  })
})
