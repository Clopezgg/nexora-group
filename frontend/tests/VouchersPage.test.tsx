import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

describe('VouchersPage', () => {
  beforeEach(() => {
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:runtime-voucher'),
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/auth/me')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({
              id: 'user-runtime',
              email: 'admin@nexora.group',
              fullName: 'Admin',
              roles: ['Administrator'],
              permissions: ['treasury.voucher:read'],
            }),
          } as Response)
        }
        if (url.includes('/master-data/companies')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [
              {
                id: 'company-runtime',
                name: 'Constructora Nexora',
                code: 'NX',
                functionalCurrencyCode: 'HNL',
                voucherPayerName: 'KAREN VANNESSA LOPEZ GONZALEZ',
                voucherApproverName: 'CARLOS HUMBERTO LOPEZ',
              },
            ],
          } as Response)
        }
        if (url.includes('/accounting/journal-entries')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [
              {
                id: 'document-runtime',
                documentNumber: 'REM-2026-0001',
                companyId: 'company-runtime',
                scope: 'CENTRAL',
                projectId: null,
                currencyCode: 'HNL',
                status: 'POSTED',
                description: 'Remesa recibida',
              },
            ],
          } as Response)
        }
        if (url.includes('/treasury/vouchers/document-runtime')) {
          expect(init?.credentials).toBe('include')
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers({
              'content-type': 'application/pdf',
              'content-disposition': 'attachment; filename="comprobante.pdf"',
            }),
            blob: async () => new Blob(['pdf-runtime'], { type: 'application/pdf' }),
          } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }),
    )
  })

  it('uses a real document selector and downloads an authenticated professional PDF', async () => {
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))

    const documentSelect = await screen.findByLabelText('Asiento / documento')
    expect(screen.queryByLabelText(/uuid/i)).not.toBeInTheDocument()
    await user.selectOptions(documentSelect, 'document-runtime')
    expect(screen.getByText('REM-2026-0001', { selector: 'span' })).toBeInTheDocument()
    expect(screen.getByText('HNL')).toBeInTheDocument()

    expect(screen.getByRole('option', { name: 'Transferencia' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Cheque' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Efectivo' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Remesa' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Otro' })).toBeInTheDocument()

    await user.type(screen.getByLabelText('Beneficiario'), 'Proveedor real')
    // El pagador es fijo desde Company Settings: se muestra read-only, no se captura.
    const payerField = screen.getByLabelText('Pagador') as HTMLInputElement
    expect(payerField).toBeDisabled()
    expect(payerField.value).toBe('KAREN VANNESSA LOPEZ GONZALEZ')
    await user.click(screen.getByRole('button', { name: 'Generar PDF' }))

    await waitFor(() => {
      expect(URL.createObjectURL).toHaveBeenCalled()
    })
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled()

    const voucherCall = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.find(([u]) =>
      String(u).includes('/treasury/vouchers/document-runtime'),
    )
    expect(voucherCall).toBeDefined()
    expect(String(voucherCall?.[0])).not.toContain('payer=')
  })
})
