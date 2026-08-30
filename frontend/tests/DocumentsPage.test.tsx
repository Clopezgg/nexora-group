import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], documents: unknown[], versions: unknown[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: 'u1',
            email: 'admin@nexora.group',
            fullName: 'Admin',
            roles: ['Administrator'],
            permissions: ['document.document:read'],
          }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => companies } as Response)
      }
      if (url.includes('/documents?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => documents } as Response)
      }
      if (url.includes('/documents/d1/versions')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => versions } as Response)
      }
      if (url.includes('/evidence/e1/download')) {
        return Promise.resolve(
          new Response(new Blob(['document bytes'], { type: 'application/pdf' }), {
            status: 200,
            headers: { 'Content-Disposition': "attachment; filename*=UTF-8''plano.pdf" },
          }),
        )
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('DocumentsPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch([], [])

    render(renderApp('/control/documentos'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('lists real documents with their current version, never fabricated rows', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 'd1',
          companyId: 'c1',
          scope: 'GENERAL',
          projectId: null,
          category: 'DRAWING',
          title: 'Plano estructural nivel 3',
          description: null,
          status: 'ACTIVE',
          currentVersion: {
            id: 'v1',
            documentId: 'd1',
            versionNumber: 1,
            evidenceId: 'e1',
            status: 'ACTIVE',
            notes: null,
            uploadedBy: 'u1',
            createdAt: '2026-03-01T00:00:00Z',
          },
        },
      ],
    )

    render(renderApp('/control/documentos'))

    expect(await screen.findByText('Plano estructural nivel 3')).toBeInTheDocument()
    expect(screen.getByText('v1')).toBeInTheDocument()
  })

  it('downloads a selected version through its private evidence endpoint', async () => {
    const user = userEvent.setup()
    const createObjectURL = vi.fn().mockReturnValue('blob:private-evidence')
    const revokeObjectURL = vi.fn()
    const NativeURL = URL
    class DownloadURL extends NativeURL {
      static createObjectURL = createObjectURL
      static revokeObjectURL = revokeObjectURL
    }
    vi.stubGlobal('URL', DownloadURL)
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)

    const version = {
      id: 'v1',
      documentId: 'd1',
      versionNumber: 1,
      evidenceId: 'e1',
      status: 'ACTIVE',
      notes: null,
      uploadedBy: 'u1',
      createdAt: '2026-03-01T00:00:00Z',
    }
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 'd1',
          companyId: 'c1',
          scope: 'GENERAL',
          projectId: null,
          category: 'DRAWING',
          title: 'Plano estructural',
          description: null,
          status: 'ACTIVE',
          currentVersion: version,
        },
      ],
      [version],
    )

    render(renderApp('/control/documentos'))
    await user.click(await screen.findByRole('button', { name: /ver versiones/i }))
    await user.click(await screen.findByRole('button', { name: /descargar/i }))

    await waitFor(() => expect(createObjectURL).toHaveBeenCalledOnce())
    expect(click).toHaveBeenCalledOnce()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:private-evidence')
    expect(fetch).toHaveBeenCalledWith('/api/evidence/e1/download', expect.objectContaining({ credentials: 'include' }))

    click.mockRestore()
    vi.unstubAllGlobals()
  })
})
