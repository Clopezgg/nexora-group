import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { SapCommandBarProps } from './sapWorkstation.types'

interface AliasedItem {
  id: string
  label: string
  group: string
  path: string
}

/**
 * Command field estilo workstation: [✓] [←] [→] [ campo ] [▾].
 * Solo comandos Nexora reales: módulos visibles por RBAC (filtro local) +
 * resultados remotos de globalSearch (documentos, asientos, proveedores…).
 * Sin códigos SAP ficticios (/nFB60, ME21N, F110). Keyboard-first.
 */
export function SapCommandBar({ items, searchRemote }: SapCommandBarProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  // Resultados remotos etiquetados con el query al que responden: solo se
  // fusionan cuando ese query sigue vigente, así una respuesta tardía jamás
  // contamina otra búsqueda (mismo patrón que CommandPalette).
  const [remoteState, setRemoteState] = useState<{ query: string; results: AliasedItem[] }>({
    query: '',
    results: [],
  })
  const inputRef = useRef<HTMLInputElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)

  const normalized = query.trim().toLowerCase()
  const local = useMemo(() => {
    if (!normalized) return items.slice(0, 8)
    return items.filter((item) => item.label.toLowerCase().includes(normalized)).slice(0, 12)
  }, [items, normalized])

  useEffect(() => {
    if (!searchRemote || normalized.length < 2) return
    const asked = query.trim()
    let cancelled = false
    const timer = window.setTimeout(() => {
      searchRemote(asked)
        .then((results) => {
          if (!cancelled) setRemoteState({ query: asked, results: results.slice(0, 8) })
        })
        .catch(() => {
          if (!cancelled) setRemoteState({ query: asked, results: [] })
        })
    }, 220)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [query, searchRemote, normalized.length])

  const merged: AliasedItem[] = useMemo(() => {
    const trimmed = query.trim()
    const remote = remoteState.query === trimmed ? remoteState.results : []
    const seen = new Set(local.map((item) => item.id))
    const out = [...local]
    for (const result of remote) {
      if (!seen.has(result.id)) {
        out.push(result)
        seen.add(result.id)
      }
    }
    return out.slice(0, 20)
  }, [local, remoteState, query])

  const safeHighlight = merged.length === 0 ? 0 : Math.min(highlight, merged.length - 1)

  useEffect(() => {
    if (!open) return
    const onPointer = (event: PointerEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    return () => document.removeEventListener('pointerdown', onPointer)
  }, [open ])

  const go = (path: string) => {
    setOpen(false)
    setQuery('')
    navigate(path)
  }

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
      setHighlight((current) => (merged.length === 0 ? 0 : (current + 1) % merged.length))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlight((current) => (merged.length === 0 ? 0 : (current - 1 + merged.length) % merged.length))
    } else if (event.key === 'Enter') {
      const target = merged[safeHighlight]
      if (open && target) {
        event.preventDefault()
        go(target.path)
      }
    } else if (event.key === 'Escape') {
      if (open) {
        event.preventDefault()
        setOpen(false)
      } else {
        setQuery('')
        inputRef.current?.blur()
      }
    }
  }

  return (
    <div ref={boxRef} className="nx-sap-commandbar" role="search" aria-label="Campo de comandos SAP GUI">
      <span className="nx-sap-commandbar__ok" aria-hidden="true">✓</span>
      <button
        type="button"
        className="nx-sap-commandbar__nav"
        aria-label="Atrás"
        onClick={() => window.history.back()}
      >
        ←
      </button>
      <button
        type="button"
        className="nx-sap-commandbar__nav"
        aria-label="Adelante"
        onClick={() => window.history.forward()}
      >
        →
      </button>
      <div className="nx-sap-commandbar__field">
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open && merged.length > 0}
          aria-controls="nx-sap-command-listbox"
          aria-autocomplete="list"
          aria-label="Comando: buscar módulo, documento o acción"
          placeholder="Buscar módulo, documento o acción…"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setHighlight(0)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
        {open && normalized.length > 0 ? (
          <ul id="nx-sap-command-listbox" role="listbox" aria-label="Resultados del comando" className="nx-sap-commandbar__results">
            {merged.length === 0 ? (
              <li role="option" aria-selected="false" className="nx-sap-commandbar__empty">
                Sin resultados para “{query.trim()}”.
              </li>
            ) : (
              merged.map((item, index) => (
                <li
                  key={item.id}
                  role="option"
                  aria-selected={index === safeHighlight}
                  className={index === safeHighlight ? 'nx-sap-commandbar__option--active' : undefined}
                >
                  <button
                    type="button"
                    tabIndex={-1}
                    onMouseEnter={() => setHighlight(index)}
                    onClick={() => go(item.path)}
                  >
                    <span className="nx-sap-commandbar__group">{item.group}</span>
                    {item.label}
                  </button>
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>
      <button
        type="button"
        className="nx-sap-commandbar__nav"
        aria-label="Abrir búsqueda global"
        aria-haspopup="dialog"
        onClick={() => {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
        }}
      >
        ▾
      </button>
    </div>
  )
}
