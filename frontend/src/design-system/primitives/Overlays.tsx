import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  const [visible, setVisible] = useState(false)
  const id = useId()
  return (
    <span
      className="nx-tooltip"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      <span aria-describedby={visible ? id : undefined}>{children}</span>
      {visible ? (
        <span role="tooltip" id={id} className="nx-tooltip__bubble">
          {label}
        </span>
      ) : null}
    </span>
  )
}

interface PopoverProps {
  trigger: ReactNode
  children: ReactNode
  align?: 'start' | 'end'
}

export function Popover({ trigger, children, align = 'start' }: PopoverProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    document.addEventListener('keydown', onEscape)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      document.removeEventListener('keydown', onEscape)
    }
  }, [])

  return (
    <div className="nx-popover" ref={rootRef}>
      <button
        type="button"
        className="nx-popover__trigger"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {trigger}
      </button>
      {open ? (
        <div className={`nx-popover__panel nx-popover__panel--${align}`} role="dialog">
          {children}
        </div>
      ) : null}
    </div>
  )
}

interface DrawerProps {
  open: boolean
  title: string
  onClose: () => void
  side?: 'left' | 'right'
  children: ReactNode
}

/** Side-anchored panel — used for the mobile navigation drawer and detail-record side panels. */
export function Drawer({ open, title, onClose, side = 'right', children }: DrawerProps) {
  if (!open) return null
  return (
    <div className="nx-drawer__overlay" role="presentation" onClick={onClose}>
      <div
        className={`nx-drawer nx-drawer--${side}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="nx-drawer__header">
          <h2 className="nx-drawer__title">{title}</h2>
          <button className="nx-modal__close" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>
        <div className="nx-drawer__body">{children}</div>
      </div>
    </div>
  )
}

interface SheetProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

/** Bottom sheet — the mobile-first equivalent of Drawer, anchored to the viewport bottom. */
export function Sheet({ open, title, onClose, children }: SheetProps) {
  if (!open) return null
  return (
    <div className="nx-drawer__overlay" role="presentation" onClick={onClose}>
      <div
        className="nx-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <span className="nx-sheet__handle" aria-hidden="true" />
        <div className="nx-drawer__header">
          <h2 className="nx-drawer__title">{title}</h2>
          <button className="nx-modal__close" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>
        <div className="nx-drawer__body">{children}</div>
      </div>
    </div>
  )
}
