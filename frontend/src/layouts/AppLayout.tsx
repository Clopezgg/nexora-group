import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import './AppLayout.css'

export function AppLayout() {
  return (
    <div className="nx-app-shell">
      <Sidebar />
      <div className="nx-app-shell__main">
        <Topbar />
        <main className="nx-app-shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
