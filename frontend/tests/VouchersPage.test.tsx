import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

interface FetchScenarioOptions {
  evidenceList?: Array<Record<string, unknown>>
  uploadResponse?: (call: number) => Promise<Response> | Response
}

function stubVoucherFetch(options: FetchScenarioOptions = {}) {
  const evidenceList = options.evidenceList ?? []
  let uploadCalls = 0

  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method ?? 'GET').toUpperCase()

      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: 'user-runtime',
            email: 'admin@nexora.group',
            fullName: 'Admin',
            roles: ['Administrator'],
            permissions: ['treasury.voucher:read', 'document.evidence:create', 'document.evidence:read'],
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
      if (url.includes('/treasury/accounts')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            { id: 'acc-1', name: 'Cuenta operativa', kind: 'BANK', institution: 'BAC', accountReference: '1234567890', currencyCode: 'HNL', balance: '0.00', glAccountId: 'gl-1', companyId: 'company-runtime', status: 'ACTIVE' },
          ],
        } as Response)
      }
      if (url.includes('/accounting/journal-entries')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            { id: 'document-runtime', documentNumber: 'REM-2026-0001', companyId: 'company-runtime', scope: 'CENTRAL', projectId: null, currencyCode: 'HNL', status: 'POSTED', description: 'Remesa recibida' },
            { id: 'document-other', documentNumber: 'REM-2026-0002', companyId: 'company-runtime', scope: 'CENTRAL', projectId: null, currencyCode: 'HNL', status: 'POSTED', description: 'Segundo documento' },
          ],
        } as Response)
      }
      if (url.includes('/evidence') && method === 'POST') {
        uploadCalls += 1
        if (options.uploadResponse) return Promise.resolve(options.uploadResponse(uploadCalls))
        const evidence = { id: `ev-${uploadCalls}`, originalFilename: 'transferencia.jpg', entityId: 'document-runtime' }
        evidenceList.push(evidence)
        return Promise.resolve({ ok: true, status: 201, json: async () => evidence } as Response)
      }
      if (url.includes('/evidence') && method === 'GET') {
        const entityId = new URL(url, 'http://x').searchParams.get('entityId')
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => evidenceList.filter((row) => !entityId || row.entityId === entityId),
        } as Response)
      }
      if (url.includes('/treasury/vouchers/document-runtime')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/pdf', 'content-disposition': 'attachment; filename="c.pdf"' }),
          blob: async () => new Blob(['pdf'], { type: 'application/pdf' }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }),
  )
}

async function selectDocumentAndBeneficiary(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(await screen.findByLabelText('Asiento / documento'), 'document-runtime')
  await user.type(screen.getByRole('combobox', { name: 'Beneficiario' }), 'Ferre')
  await user.click(await screen.findByText(/Ferretería El Clavo/))
}

function evidenceFileInput(): HTMLInputElement {
  return document.querySelector('#voucher-evidence-file') as HTMLInputElement
}

describe('VouchersPage', () => {
  beforeEach(() => {
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:runtime-voucher') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
  })

  it('downloads an authenticated professional PDF when evidence is attached', async () => {
    stubVoucherFetch({ evidenceList: [{ id: 'ev-1', originalFilename: 'transferencia.pdf', entityId: 'document-runtime' }] })
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))

    await selectDocumentAndBeneficiary(user)
    expect(screen.getByText('REM-2026-0001', { selector: 'span' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Cuenta de tesorería (banco)'), 'acc-1')
    await user.click(screen.getByRole('button', { name: 'Generar PDF' }))

    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled())
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled()
  })

  it('does not revoke the object URL synchronously (Safari/iOS)', async () => {
    stubVoucherFetch({ evidenceList: [{ id: 'ev-1', entityId: 'document-runtime' }] })
    const setTimeoutSpy = vi.spyOn(window, 'setTimeout')
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))
    await selectDocumentAndBeneficiary(user)
    await user.click(screen.getByRole('button', { name: 'Generar PDF' }))
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled())
    // The revoke + anchor removal must be deferred, not run inline.
    expect(URL.revokeObjectURL).not.toHaveBeenCalled()
    expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 60_000)
    setTimeoutSpy.mockRestore()
  })

  it('blocks bank payment methods with an explicit reason until evidence is attached', async () => {
    stubVoucherFetch({ evidenceList: [] })
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))

    await selectDocumentAndBeneficiary(user)
    expect(await screen.findByText(/Adjunta el comprobante de transferencia para continuar/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generar PDF' })).toBeDisabled()

    await user.selectOptions(screen.getByLabelText('Método de pago'), 'CASH')
    expect(screen.getByRole('button', { name: 'Generar PDF' })).toBeEnabled()
  })

  it('shows the selected filename and does not clear the input before the upload resolves', async () => {
    const evidenceList: Array<Record<string, unknown>> = []
    let resolveUpload: (r: Response) => void = () => {}
    stubVoucherFetch({
      evidenceList,
      uploadResponse: () =>
        new Promise<Response>((resolve) => {
          resolveUpload = resolve
        }),
    })
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))
    await selectDocumentAndBeneficiary(user)

    const input = evidenceFileInput()
    const file = new File(['x'], 'comprobante-transferencia.jpg', { type: 'image/jpeg' })
    fireEvent.change(input, { target: { files: [file] } })

    expect(await screen.findByText('comprobante-transferencia.jpg')).toBeInTheDocument()
    expect(screen.getByText(/Subiendo evidencia/i)).toBeInTheDocument()
    // The native input still holds the file while the mutation is pending.
    expect(input.files?.[0]?.name).toBe('comprobante-transferencia.jpg')

    evidenceList.push({ id: 'ev-1', entityId: 'document-runtime' })
    resolveUpload({ ok: true, status: 201, json: async () => ({ id: 'ev-1', entityId: 'document-runtime' }) } as Response)

    expect(await screen.findByText(/Evidencia cargada correctamente/i)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generar PDF' })).toBeEnabled())
  })

  it('surfaces a human error and a retry action when the upload fails', async () => {
    stubVoucherFetch({
      evidenceList: [],
      uploadResponse: () =>
        ({
          ok: false,
          status: 503,
          json: async () => ({ error: { code: 'NXR-EVIDENCE-STORAGE-AUTH', message: 'No fue posible almacenar la evidencia. Intenta nuevamente.', correlationId: 'abc' } }),
        }) as Response,
    })
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))
    await selectDocumentAndBeneficiary(user)

    const file = new File(['x'], 'foto.jpg', { type: 'image/jpeg' })
    fireEvent.change(evidenceFileInput(), { target: { files: [file] } })

    expect(await screen.findByRole('button', { name: /Reintentar/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generar PDF' })).toBeDisabled()
  })

  it('resets evidence state when the selected document changes', async () => {
    stubVoucherFetch({ evidenceList: [] })
    const user = userEvent.setup()
    render(renderApp('/finanzas/comprobantes'))
    await selectDocumentAndBeneficiary(user)

    const file = new File(['x'], 'doc-a-evidencia.jpg', { type: 'image/jpeg' })
    fireEvent.change(evidenceFileInput(), { target: { files: [file] } })
    expect(await screen.findByText(/Evidencia cargada correctamente/i)).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Asiento / documento'), 'document-other')

    await waitFor(() => expect(screen.queryByText('doc-a-evidencia.jpg')).not.toBeInTheDocument())
    const region = screen.getByText(/Evidencia del pago/i).closest('.nx-evidence') as HTMLElement
    expect(within(region).queryByText(/Evidencia cargada correctamente/i)).not.toBeInTheDocument()
  })
})
