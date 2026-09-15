import { useState } from 'react'
import { Icon } from '../../design-system/primitives/Icon'
import { useNavigate } from 'react-router-dom'

/**
 * Toolbar SAP: acciones reales de navegación de la sesión (atrás/adelante/
 * inicio/búsqueda/navegación). La compañía, proyecto, período fiscal,
 * Protected Edit, notificaciones y usuario viven en la Topbar canónica que
 * sigue montada debajo con tratamiento SAP — esta tira no duplica estado.
 */
export function SapToolbar({ onOpenNav }: { onOpenNav: () => void }) {
  const navigate = useNavigate()
  const [focusedIndex, setFocusedIndex] = useState(0)
  const openSearch = () => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
  }
  return (
    <div
      className="nx-sap-toolbar"
      role="toolbar"
      aria-label="Barra de herramientas SAP GUI"
      onKeyDown={(event) => {
        const buttons = Array.from(
          event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'),
        )
        const currentIndex = buttons.indexOf(event.target as HTMLButtonElement)
        if (currentIndex < 0) return
        let nextIndex: number
        switch (event.key) {
          case 'ArrowLeft':
            nextIndex = (currentIndex - 1 + buttons.length) % buttons.length
            break
          case 'ArrowRight':
            nextIndex = (currentIndex + 1) % buttons.length
            break
          case 'Home':
            nextIndex = 0
            break
          case 'End':
            nextIndex = buttons.length - 1
            break
          default:
            return
        }
        event.preventDefault()
        buttons[nextIndex]?.focus()
      }}
    >
      <button
        type="button"
        tabIndex={focusedIndex === 0 ? 0 : -1}
        onFocus={() => setFocusedIndex(0)}
        aria-label="Atrás"
        title="Atrás"
        onClick={() => window.history.back()}
      >
        ←
      </button>
      <button
        type="button"
        tabIndex={focusedIndex === 1 ? 0 : -1}
        onFocus={() => setFocusedIndex(1)}
        aria-label="Adelante"
        title="Adelante"
        onClick={() => window.history.forward()}
      >
        →
      </button>
      <button
        type="button"
        tabIndex={focusedIndex === 2 ? 0 : -1}
        onFocus={() => setFocusedIndex(2)}
        aria-label="Inicio"
        title="Inicio"
        onClick={() => navigate('/inicio')}
      >
        <Icon name="home" size={16} />
      </button>
      <span className="nx-sap-toolbar__separator" aria-hidden="true" />
      <button
        type="button"
        tabIndex={focusedIndex === 3 ? 0 : -1}
        onFocus={() => setFocusedIndex(3)}
        aria-label="Búsqueda global"
        title="Búsqueda global (Cmd/Ctrl + K)"
        onClick={openSearch}
      >
        <Icon name="search" size={16} />
      </button>
      <button
        type="button"
        tabIndex={focusedIndex === 4 ? 0 : -1}
        onFocus={() => setFocusedIndex(4)}
        aria-label="Abrir navegación"
        title="Abrir navegación"
        onClick={onOpenNav}
      >
        <Icon name="menu" size={16} />
      </button>
    </div>
  )
}
