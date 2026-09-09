import { useNavigate } from 'react-router-dom'

/**
 * Toolbar SAP: acciones reales de navegación de la sesión (atrás/adelante/
 * inicio/búsqueda/navegación). La compañía, proyecto, período fiscal,
 * Protected Edit, notificaciones y usuario viven en la Topbar canónica que
 * sigue montada debajo con tratamiento SAP — esta tira no duplica estado.
 */
export function SapToolbar({ onOpenNav }: { onOpenNav: () => void }) {
  const navigate = useNavigate()
  const openSearch = () => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
  }
  return (
    <div className="nx-sap-toolbar" role="toolbar" aria-label="Barra de herramientas SAP GUI">
      <button type="button" aria-label="Atrás" title="Atrás" onClick={() => window.history.back()}>←</button>
      <button type="button" aria-label="Adelante" title="Adelante" onClick={() => window.history.forward()}>→</button>
      <button type="button" aria-label="Inicio" title="Inicio" onClick={() => navigate('/inicio')}>⌂</button>
      <span className="nx-sap-toolbar__separator" aria-hidden="true" />
      <button type="button" aria-label="Búsqueda global" title="Búsqueda global (Cmd/Ctrl + K)" onClick={openSearch}>⌕</button>
      <button type="button" aria-label="Abrir navegación" title="Abrir navegación" onClick={onOpenNav}>☰</button>
    </div>
  )
}
