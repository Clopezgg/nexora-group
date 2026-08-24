import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { LoginPage } from '../pages/LoginPage'
import { DashboardPage } from '../pages/DashboardPage'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { navItems } from './navigation'

const placeholderRoutes: RouteObject[] = navItems
  .filter((item) => item.path !== '/dashboard')
  .map((item) => ({
    path: item.path.replace(/^\//, ''),
    element: <PlaceholderPage title={item.label} />,
  }))

export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/dashboard" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: 'dashboard', element: <DashboardPage /> },
          ...placeholderRoutes,
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
]
