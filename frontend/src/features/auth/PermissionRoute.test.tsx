import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { CurrentUser } from '../../types/auth'
import { AuthContext, type AuthContextValue } from './auth-context'
import { PermissionRoute } from './PermissionRoute'

function renderRoute(permissions: string[], roles: CurrentUser['roles'] = ['Viewer']) {
  const user = {
    id: 'user-1',
    email: 'user@nexora.group',
    fullName: 'User',
    roles,
    permissions,
  } satisfies CurrentUser
  const auth: AuthContextValue = {
    user,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    loginError: null,
    isLoggingIn: false,
    logout: vi.fn(),
  }
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={['/finanzas/contabilidad']}>
        <Routes>
          <Route
            element={<PermissionRoute requiredAny={['accounting.journal_entry:read']} />}
          >
            <Route path="/finanzas/contabilidad" element={<p>Contabilidad privada</p>} />
          </Route>
          <Route path="/inicio" element={<p>Inicio autorizado</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

describe('PermissionRoute', () => {
  it('renders a direct route when the user has one required permission', () => {
    renderRoute(['accounting.journal_entry:read'])

    expect(screen.getByText('Contabilidad privada')).toBeTruthy()
  })

  it('redirects a direct route when the user lacks every required permission', () => {
    renderRoute(['inventory.item:read'])

    expect(screen.queryByText('Contabilidad privada')).toBeNull()
    expect(screen.getByText('Inicio autorizado')).toBeTruthy()
  })

  it('keeps the canonical Administrator role accessible while grants refresh', () => {
    renderRoute([], ['Administrator'])

    expect(screen.getByText('Contabilidad privada')).toBeTruthy()
  })
})
