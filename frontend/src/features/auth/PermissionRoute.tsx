import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './auth-context'

export function PermissionRoute({ requiredAny }: { requiredAny: string[] }) {
  const { user } = useAuth()
  const permissions = new Set(user?.permissions ?? [])

  if (!requiredAny.some((permission) => permissions.has(permission))) {
    return <Navigate to="/inicio" replace />
  }

  return <Outlet />
}
