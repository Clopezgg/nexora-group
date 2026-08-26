import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

describe('LoginPage', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Not authenticated' }),
      } as Response),
    )
  })

  it('renders the login form when the user is not authenticated', async () => {
    render(renderApp('/login'))

    expect(await screen.findByRole('heading', { name: /iniciar sesión/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/correo electrónico/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
  })

  it('shows validation errors for empty submit', async () => {
    const user = userEvent.setup()
    render(renderApp('/login'))

    await screen.findByRole('heading', { name: /iniciar sesión/i })
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    expect(await screen.findByText(/ingresa tu correo electrónico/i)).toBeInTheDocument()
  })
})
