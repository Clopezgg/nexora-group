import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './auth-context'
import { LoadingState } from '../../design-system'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingState label="Verificando sesión…" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
