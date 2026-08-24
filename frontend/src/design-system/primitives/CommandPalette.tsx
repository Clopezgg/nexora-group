import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export interface CommandItem {
  id: string
  label: string
  group: string
  path: string
}

interface CommandPaletteProps {
  items: CommandItem[]
}

/**
 * Global Cmd/Ctrl+K launcher. Today it searches the app's own navigation
 * (real, live data — every route that exists), not a placeholder. Cross-entity
 * search (documents, journals, suppliers, POs, …) plugs in here once
 * `GET /api/v1/search` exists (NXR-REQ-0092, owned by Track G) — this
 * component's contract (items: id/label/group/path) is designed to accept
 * that feed without changing shape.
 */
export function CommandPalette({ items }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const isCombo = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k'
      if (isCombo) {
        event.preventDefault()
        setOpen((current) => !current)
      }
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items.slice(0, 8)
    return items.filter((item) => item.label.toLowerCase().includes(q)).slice(0, 20)
  }, [items, query])

  if (!open) return null

  return (
    <div
      className="nx-command-palette__overlay"
      role="presentation"
      onClick={() => setOpen(false)}
    >
      <div
        className="nx-command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Búsqueda global"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          autoFocus
          type="text"
          className="nx-command-palette__input"
          placeholder="Ir a… (Cmd/Ctrl + K)"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <ul className="nx-command-palette__list" role="listbox">
          {filtered.length === 0 ? (
            <li className="nx-command-palette__empty">Sin resultados.</li>
          ) : (
            filtered.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="nx-command-palette__item"
                  role="option"
                  onClick={() => {
                    navigate(item.path)
                    setOpen(false)
                    setQuery('')
                  }}
                >
                  <span className="nx-command-palette__group">{item.group}</span>
                  {item.label}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
