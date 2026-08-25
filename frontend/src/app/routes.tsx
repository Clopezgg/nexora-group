import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { LoginPage } from '../pages/LoginPage'
import { HomePage } from '../features/home/HomePage'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { TreasuryPage } from '../features/treasury/TreasuryPage'
import { AccountsPayablePage } from '../features/treasury/AccountsPayablePage'
import { AccountsReceivablePage } from '../features/treasury/AccountsReceivablePage'
import { navItems } from './navigation'

// Track A (Financial Core) ya construyó pantallas reales para estas rutas;
// el resto sigue en PlaceholderPage hasta que su track dueño las construya.
const trackARoutes: Record<string, RouteObject['element']> = {
  '/finanzas/tesoreria': <TreasuryPage />,
  '/finanzas/cuentas-por-pagar': <AccountsPayablePage />,
  '/finanzas/cuentas-por-cobrar': <AccountsReceivablePage />,
}

const placeholderRoutes: RouteObject[] = navItems
  .filter((item) => item.path !== '/inicio')
  .map((item) => ({
    path: item.path.replace(/^\//, ''),
    element: trackARoutes[item.path] ?? <PlaceholderPage title={item.label} />,
  }))

export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/inicio" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [{ path: 'inicio', element: <HomePage /> }, ...placeholderRoutes],
      },
    ],
  },
  { path: '*', element: <Navigate to="/inicio" replace /> },
]
