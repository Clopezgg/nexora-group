import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], documents: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => companies } as Response)
      }
      if (url.includes('/documents?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => documents } as Response)
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
})
