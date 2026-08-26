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
  /**
   * Optional cross-entity search (NXR-REQ-0092, `GET /api/search`). Called
   * (debounced) whenever the query is >= 2 chars; its results are merged
   * additively into the local nav-filter matches, never replacing them, so
   * the palette is never blank while a remote lookup is in flight or fails.
   */
  searchRemote?: (query: string) => Promise<CommandItem[]>
}

/**
 * Global Cmd/Ctrl+K launcher. Always searches the app's own navigation
 * (real, live data — every route that exists) as a client-side filter; when
 * `searchRemote` is provided, cross-entity results (documents, journals,
 * suppliers, POs, …) are merged in as the user types.
 */
export function CommandPalette({ items, searchRemote }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  // Remote results are tagged with the query they answer -- `filtered` only
  // consumes them when that query still matches the current one, so an
  // in-flight/stale response from a shorter or earlier query never gets
  // merged in. This avoids resetting state synchronously inside the effect
  // below (react-hooks/set-state-in-effect): the effect only ever calls
  // setRemoteState from its async callbacks, never from its own body.
  const [remoteState, setRemoteState] = useState<{ query: string; results: CommandItem[] }>({
    query: '',
    results: [],
  })
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

  useEffect(() => {
    const q = query.trim()
    if (!searchRemote || q.length < 2) return
    let cancelled = false
    const timer = setTimeout(() => {
      searchRemote(q)
        .then((results) => {
          if (!cancelled) setRemoteState({ query: q, results })
        })
        .catch(() => {
          if (!cancelled) setRemoteState({ query: q, results: [] })
        })
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query, searchRemote])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items.slice(0, 8)
    const localMatches = items.filter((item) => item.label.toLowerCase().includes(q))
    const merged = [...localMatches]
    const seen = new Set(merged.map((item) => item.id))
    if (remoteState.query === query.trim()) {
      for (const result of remoteState.results) {
        if (!seen.has(result.id)) {
          merged.push(result)
          seen.add(result.id)
        }
      }
    }
    return merged.slice(0, 20)
  }, [items, query, remoteState])

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
