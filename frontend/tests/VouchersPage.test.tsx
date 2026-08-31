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
        if (url.includes('/treasury/beneficiaries')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [
              { beneficiaryType: 'SUPPLIER', id: 'sup-1', name: 'Ferretería El Clavo', reference: 'RTN-123' },
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
        if (url.includes('/evidence') && (!init || init.method === undefined || init.method === 'GET')) {
          // Con evidencia adjunta el método bancario queda habilitado.
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [{ id: 'ev-1', originalFilename: 'transferencia.pdf' }],
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

    // Beneficiario: selector buscable sobre entidades reales, no texto libre.
    const beneficiaryBox = screen.getByRole('combobox', { name: 'Beneficiario' })
    await user.type(beneficiaryBox, 'Ferre')
    await user.click(await screen.findByText(/Ferretería El Clavo/))

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
    const voucherUrl = String(voucherCall?.[0])
    expect(voucherUrl).not.toContain('payer=')
    expect(voucherUrl).toContain('beneficiaryType=SUPPLIER')
    expect(voucherUrl).toContain('beneficiaryId=sup-1')
  })

  it('blocks bank payment methods until payment evidence is attached', async () => {
    // Sin evidencia adjunta para el documento.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/auth/me')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({ id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'], permissions: ['treasury.voucher:read'] }),
          } as Response)
        }
        if (url.includes('/master-data/companies')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 'company-runtime', name: 'Constructora Nexora', functionalCurrencyCode: 'HNL', voucherPayerName: 'KAREN', voucherApproverName: 'CARLOS' }] } as Response)
        }
        if (url.includes('/treasury/beneficiaries')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => [{ beneficiaryType: 'SUPPLIER', id: 'sup-1', name: 'Ferretería El Clavo', reference: null }] } as Response)
        }
        if (url.includes('/accounting/journal-entries')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 'document-runtime', documentNumber: 'REM-2026-0001', companyId: 'company-runtime', scope: 'CENTRAL', projectId: null, currencyCode: 'HNL', status: 'POSTED', description: 'Remesa' }] } as Response)
        }
        if (url.includes('/evidence')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }),
    )
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))

    await user.selectOptions(await screen.findByLabelText('Asiento / documento'), 'document-runtime')
    await user.type(screen.getByRole('combobox', { name: 'Beneficiario' }), 'Ferre')
    await user.click(await screen.findByText(/Ferretería El Clavo/))

    // Método por defecto = Transferencia (bancario) -> evidencia obligatoria.
    expect(await screen.findByText(/exigen adjuntar el comprobante del pago/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generar PDF' })).toBeDisabled()

    // Cambiar a Efectivo libera el botón.
    await user.selectOptions(screen.getByLabelText('Método de pago'), 'CASH')
    expect(screen.getByRole('button', { name: 'Generar PDF' })).toBeEnabled()
  })
})
