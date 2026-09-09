import { useEffect, useEffectEvent, useId, useRef, type ReactNode } from 'react'

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** `wide` da más ancho para tablas financieras (§44). */
  size?: 'default' | 'wide'
}

export function Modal({ open, title, onClose, children, size = 'default' }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeDialog = useEffectEvent(onClose)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    if (!open) return
    const previouslyFocused = document.activeElement as HTMLElement | null
    const dialog = dialogRef.current
    const focusableSelector = 'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
    const focusable = () => Array.from(dialog?.querySelectorAll<HTMLElement>(focusableSelector) ?? [])
    focusable()[0]?.focus()

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeDialog()
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      if (items.length === 0) {
        event.preventDefault()
        dialog?.focus()
        return
      }
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      previouslyFocused?.focus()
    }
  }, [open])

  if (!open) return null
  return (
    <div
      className="nx-modal__overlay"
      role="presentation"
      onClick={onClose}
      style={{ padding: '16px', overflowY: 'auto', boxSizing: 'border-box' }}
    >
      <div
        ref={dialogRef}
        className="nx-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
        style={{
          maxHeight: 'calc(100dvh - 32px)',
          overflowY: 'auto',
          boxSizing: 'border-box',
          ...(size === 'wide' ? { width: 'min(1040px, 100%)', maxWidth: 'min(1040px, 100%)' } : {}),
        }}
      >
        <div className="nx-modal__header">
          <h2 className="nx-modal__title" id={titleId}>{title}</h2>
          <button className="nx-modal__close" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>
        <div className="nx-modal__body" id={descriptionId}>{children}</div>
      </div>
    </div>
  )
}
