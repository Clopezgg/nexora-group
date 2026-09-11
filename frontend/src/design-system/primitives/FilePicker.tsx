import { useId, useRef } from 'react'
import { Button } from './Button'
import { Icon } from './Icon'

export function FilePicker({
  label,
  hint,
  accept,
  disabled,
  value,
  onChange,
}: {
  label: string
  hint?: string
  accept?: string
  disabled?: boolean
  value: File | null
  onChange: (file: File | null) => void
}) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  function select(file: File | undefined) {
    onChange(file ?? null)
  }

  return (
    <div className="nx-file-picker">
      <span className="nx-field__label" id={`${inputId}-label`}>{label}</span>
      {hint ? <p className="nx-field__hint" id={`${inputId}-hint`}>{hint}</p> : null}
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        hidden
        accept={accept}
        disabled={disabled}
        aria-labelledby={`${inputId}-label`}
        aria-describedby={hint ? `${inputId}-hint` : undefined}
        onChange={(event) => select(event.target.files?.[0])}
      />
      <div className="nx-evidence__actions">
        <Button type="button" variant="secondary" disabled={disabled} onClick={() => inputRef.current?.click()}>
          <Icon name="file" size={16} /> {value ? 'Cambiar archivo' : 'Seleccionar archivo'}
        </Button>
        {value ? (
          <Button type="button" variant="ghost" disabled={disabled} onClick={() => {
            if (inputRef.current) inputRef.current.value = ''
            select(undefined)
          }}>
            Quitar
          </Button>
        ) : null}
      </div>
      <p className="nx-field__hint" role="status">{value ? value.name : 'Ningún archivo seleccionado'}</p>
    </div>
  )
}
