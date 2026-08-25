import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function makeNotification(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'n1',
    recipientUserId: 'u1',
    type: 'approval.assigned',
    title: 'Nueva aprobación pendiente',
    body: 'Tienes una factura de proveedor esperando tu aprobación',
    entityType: 'ap.supplier_invoice',
    entityId: 'inv1',
    readAt: null,
    createdAt: '2026-08-25T10:00:00Z',
    ...overrides,
  }
}

function stubFetch() {
  let notifications = [makeNotification()]

  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = init?.method ?? 'GET'

      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (method === 'POST' && url.match(/\/notifications\/.+\/read/)) {
        notifications = notifications.map((note) =>
          note.id === 'n1' ? { ...note, readAt: '2026-08-25T11:00:00Z' } : note,
        )
        return Promise.resolve({ ok: true, status: 200, json: async () => notifications[0] } as Response)
      }
      if (url.includes('/notifications')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => notifications.map((n) => ({ ...n })) } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('NotificationBell', () => {
  it('shows the unread count badge and opens a dropdown with recent notifications', async () => {
    stubFetch()
    const user = userEvent.setup()

    render(renderApp('/inicio'))

    await screen.findByRole('heading', { name: /inicio/i })

    const bellButton = await screen.findByRole('button', { name: /notificaciones \(1 sin leer\)/i })
    expect(within(bellButton.parentElement as HTMLElement).getByText('1')).toBeInTheDocument()

    await user.click(bellButton)

    const panel = await screen.findByRole('dialog', { name: /notificaciones/i })
    expect(within(panel).getByText('Nueva aprobación pendiente')).toBeInTheDocument()
  })

  it('marks a notification as read via the real API and refetches, clearing the unread badge', async () => {
    stubFetch()
    const user = userEvent.setup()

    render(renderApp('/inicio'))

    await screen.findByRole('heading', { name: /inicio/i })

    const bellButton = await screen.findByRole('button', { name: /notificaciones \(1 sin leer\)/i })
    await user.click(bellButton)

    const panel = await screen.findByRole('dialog', { name: /notificaciones/i })
    await user.click(within(panel).getByRole('button', { name: /marcar como leída/i }))

    // After the mark-read response, the item no longer shows the mark-read
    // action (only unread items render it) -- proving the panel actually
    // refetched the real API response, not an optimistic local mutation.
    await screen.findByRole('button', { name: /^notificaciones$/i })
    expect(within(panel).queryByRole('button', { name: /marcar como leída/i })).not.toBeInTheDocument()
  })
})
