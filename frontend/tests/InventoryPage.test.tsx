import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { InventoryPage } from '../src/features/inventory/InventoryPage'

vi.mock('../src/hooks/useActiveCompany', () => ({
  useActiveCompany: () => ({
    activeCompanyId: 'c1',
    activeCompany: { id: 'c1', name: 'Nexora', functionalCurrencyCode: 'USD' },
    isLoading: false,
  }),
}))

function renderPage(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={queryClient}><InventoryPage /></QueryClientProvider>)
}

describe('InventoryPage', () => {
  it('expone todas las operaciones de inventario sin llamadas manuales a API', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      const body = url.includes('/inventory/items')
        ? [{ id: 'i1', companyId: 'c1', sku: 'MAT-1', name: 'Material', itemType: 'MATERIAL', uom: 'UND', active: true }]
        : url.includes('/inventory/warehouses')
          ? [{ id: 'w1', companyId: 'c1', projectId: null, code: 'CENTRAL', name: 'Central', status: 'ACTIVE' }]
          : url.includes('/projects?')
            ? [{ id: 'p1', companyId: 'c1', code: 'P-1', name: 'Proyecto Uno', status: 'ACTIVE', currencyCode: 'USD' }]
            : url.includes('/master-data/accounts')
              ? [
                  { id: 'a1', companyId: 'c1', code: '1400', name: 'Inventario', accountType: 'ASSET', isPostable: true },
                  { id: 'a2', companyId: 'c1', code: '6100', name: 'Costo', accountType: 'EXPENSE', isPostable: true },
                ]
              : url.includes('/procurement/suppliers')
                ? [{ id: 's1', companyId: 'c1', legalName: 'Proveedor Uno', status: 'ACTIVE' }]
                : []
      return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
    })
    renderPage(fetchMock)

    expect(await screen.findByRole('tab', { name: 'Recibir' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Emitir a proyecto' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Transferir' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Devolver a proveedor' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Conteo físico' })).toBeInTheDocument()
    expect(screen.getByText(/configuración contable/i)).toBeInTheDocument()
  })

  it('envía la fecha económica y las cuentas reales al emitir a proyecto', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      let body: unknown = []
      if (url.includes('/inventory/items')) body = [{ id: 'i1', companyId: 'c1', sku: 'MAT-1', name: 'Material', itemType: 'MATERIAL', uom: 'UND', active: true }]
      else if (url.includes('/inventory/warehouses')) body = [{ id: 'w1', companyId: 'c1', projectId: null, code: 'CENTRAL', name: 'Central', status: 'ACTIVE' }]
      else if (url.includes('/projects?')) body = [{ id: 'p1', companyId: 'c1', code: 'P-1', name: 'Proyecto Uno', status: 'ACTIVE', currencyCode: 'USD' }]
      else if (url.includes('/master-data/accounts')) body = [
        { id: 'a1', companyId: 'c1', code: '1400', name: 'Inventario', accountType: 'ASSET', isPostable: true },
        { id: 'a2', companyId: 'c1', code: '6100', name: 'Costo', accountType: 'EXPENSE', isPostable: true },
      ]
      else if (url.includes('/procurement/suppliers')) body = []
      else if (url.endsWith('/inventory/stock/issue-to-project') && init?.method === 'POST') body = { id: 'entry-1' }
      return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
    })
    renderPage(fetchMock)
    fireEvent.click(await screen.findByRole('tab', { name: 'Emitir a proyecto' }))
    fireEvent.change(screen.getByLabelText('Ítem'), { target: { value: 'i1' } })
    fireEvent.change(screen.getByLabelText('Almacén'), { target: { value: 'w1' } })
    fireEvent.change(screen.getByLabelText('Proyecto'), { target: { value: 'p1' } })
    fireEvent.change(screen.getByLabelText('Cantidad'), { target: { value: '2.5' } })
    fireEvent.change(screen.getByLabelText('Fecha efectiva'), { target: { value: '2026-09-10' } })
    fireEvent.change(screen.getByLabelText('Cuenta de costo'), { target: { value: 'a2' } })
    fireEvent.change(screen.getByLabelText('Cuenta de inventario'), { target: { value: 'a1' } })
    const submit = screen.getByRole('button', { name: 'Emitir material' })
    await waitFor(() => expect(submit).toBeEnabled())
    fireEvent.submit(submit.closest('form') as HTMLFormElement)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/inventory/stock/issue-to-project'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          companyId: 'c1', itemId: 'i1', warehouseId: 'w1', projectId: 'p1', quantity: '2.5',
          effectiveDate: '2026-09-10', costOfGoodsAccountId: 'a2', inventoryAccountId: 'a1',
        }),
      }),
    ))
  })
})
