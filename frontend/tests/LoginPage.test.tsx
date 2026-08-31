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
        headers: new Headers(),
        json: async () => ({ detail: 'Not authenticated' }),
      } as Response),
    )
  })

  it('renders the minimalist login card when the user is not authenticated', async () => {
    render(renderApp('/login'))

    expect(await screen.findByRole('heading', { name: /bienvenido a nexora/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/correo electrónico/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument()
  })

  it('does not surface a non-functional "forgot password" affordance', async () => {
    render(renderApp('/login'))
    await screen.findByRole('heading', { name: /bienvenido a nexora/i })
    expect(screen.queryByText(/olvidaste tu contraseña/i)).not.toBeInTheDocument()
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(renderApp('/login'))
    await screen.findByRole('heading', { name: /bienvenido a nexora/i })

    const password = screen.getByLabelText(/contraseña/i)
    expect(password).toHaveAttribute('type', 'password')
    await user.click(screen.getByRole('button', { name: /mostrar/i }))
    expect(password).toHaveAttribute('type', 'text')
  })

  it('shows validation errors for empty submit', async () => {
    const user = userEvent.setup()
    render(renderApp('/login'))

    await screen.findByRole('heading', { name: /bienvenido a nexora/i })
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    expect(await screen.findByText(/ingresa tu correo electrónico/i)).toBeInTheDocument()
  })

  it('shows a safe, human message on failed credentials (never a status code)', async () => {
    const user = userEvent.setup()
    render(renderApp('/login'))
    await screen.findByRole('heading', { name: /bienvenido a nexora/i })

    await user.type(screen.getByLabelText(/correo electrónico/i), 'admin@nexora.group')
    await user.type(screen.getByLabelText(/contraseña/i), 'wrong-pass')
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    expect(await screen.findByText(/correo o contraseña incorrectos/i)).toBeInTheDocument()
  })
})
