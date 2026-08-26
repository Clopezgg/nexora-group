import {
  forwardRef,
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from 'react'

interface FieldWrapProps {
  label?: string
  error?: string
  id: string
  hint?: string
  children: ReactNode
}

function FieldWrap({ label, error, id, hint, children }: FieldWrapProps) {
  return (
    <div className="nx-field">
      {label ? (
        <label className="nx-field__label" htmlFor={id}>
          {label}
        </label>
      ) : null}
      {children}
      {hint && !error ? <span className="nx-field__hint">{hint}</span> : null}
      {error ? <span className="nx-field__error">{error}</span> : null}
    </div>
  )
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  hint?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, hint, id, className, ...rest }, ref) => {
    const generatedId = useId()
    const fieldId = id ?? generatedId
    return (
      <FieldWrap label={label} error={error} hint={hint} id={fieldId}>
        <textarea
          ref={ref}
          id={fieldId}
          className={['nx-textarea', error ? 'nx-input--error' : '', className]
            .filter(Boolean)
            .join(' ')}
          aria-invalid={Boolean(error)}
          {...rest}
        />
      </FieldWrap>
    )
  },
)
Textarea.displayName = 'Textarea'

interface SearchInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ label, id, className, ...rest }, ref) => {
    const generatedId = useId()
    const inputId = id ?? generatedId
    return (
      <div className="nx-search-input">
        {label ? (
          <label className="nx-field__label nx-visually-hidden" htmlFor={inputId}>
            {label}
          </label>
        ) : null}
        <span className="nx-search-input__icon" aria-hidden="true">
          🔍
        </span>
        <input
          ref={ref}
          id={inputId}
          type="search"
          className={['nx-input', 'nx-search-input__field', className].filter(Boolean).join(' ')}
          {...rest}
        />
      </div>
    )
  },
)
SearchInput.displayName = 'SearchInput'

interface DatePickerProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
}

export const DatePicker = forwardRef<HTMLInputElement, DatePickerProps>(
  ({ label, error, id, className, ...rest }, ref) => {
    const generatedId = useId()
    const inputId = id ?? generatedId
    return (
      <FieldWrap label={label} error={error} id={inputId}>
        <input
          ref={ref}
          id={inputId}
          type="date"
          className={['nx-input', error ? 'nx-input--error' : '', className]
            .filter(Boolean)
            .join(' ')}
          aria-invalid={Boolean(error)}
          {...rest}
        />
      </FieldWrap>
    )
  },
)
DatePicker.displayName = 'DatePicker'

interface MoneyInputProps {
  label?: string
  error?: string
  hint?: string
  name?: string
  id?: string
  value: number | null
  onChange: (value: number | null) => void
  onBlur?: () => void
  precision?: number
  disabled?: boolean
  placeholder?: string
}

/** Numeric-only amount entry. Always resolves to a plain number (or null), never a float rounding surprise beyond `precision`. */
export const MoneyInput = forwardRef<HTMLInputElement, MoneyInputProps>(
  (
    { label, error, hint, id, name, value, onChange, onBlur, precision = 2, disabled, placeholder },
    ref,
  ) => {
    const generatedId = useId()
    const inputId = id ?? generatedId
    const [raw, setRaw] = useState(value === null ? '' : String(value))

    const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
      const next = event.target.value
      if (!/^-?\d*\.?\d*$/.test(next)) return
      setRaw(next)
      if (next === '' || next === '-') {
        onChange(null)
        return
      }
      const parsed = Number(next)
      if (!Number.isNaN(parsed)) onChange(Number(parsed.toFixed(precision)))
    }

    return (
      <FieldWrap label={label} error={error} hint={hint} id={inputId}>
        <input
          ref={ref}
          id={inputId}
          name={name}
          inputMode="decimal"
          className={['nx-input', 'nx-money-input', error ? 'nx-input--error' : '']
            .filter(Boolean)
            .join(' ')}
          value={raw}
          onChange={handleChange}
          onBlur={onBlur}
          disabled={disabled}
          placeholder={placeholder ?? '0.00'}
          aria-invalid={Boolean(error)}
        />
      </FieldWrap>
    )
  },
)
MoneyInput.displayName = 'MoneyInput'

interface CurrencyInputProps {
  label?: string
  amountError?: string
  amount: number | null
  currency: string
  currencies: string[]
  onAmountChange: (value: number | null) => void
  onCurrencyChange: (currency: string) => void
  disabled?: boolean
}

/** Compound amount + currency-code entry, used wherever a document carries an original currency distinct from the company's functional currency. */
export function CurrencyInput({
  label,
  amountError,
  amount,
  currency,
  currencies,
  onAmountChange,
  onCurrencyChange,
  disabled,
}: CurrencyInputProps) {
  const id = useId()
  return (
    <div className="nx-currency-input">
      {label ? <span className="nx-field__label">{label}</span> : null}
      <div className="nx-currency-input__row">
        <select
          aria-label="Moneda"
          className="nx-select nx-currency-input__currency"
          value={currency}
          disabled={disabled}
          onChange={(event) => onCurrencyChange(event.target.value)}
        >
          {currencies.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
        <input
          id={id}
          inputMode="decimal"
          className={['nx-input', amountError ? 'nx-input--error' : ''].filter(Boolean).join(' ')}
          value={amount === null ? '' : String(amount)}
          disabled={disabled}
          placeholder="0.00"
          onChange={(event) => {
            const next = event.target.value
            if (!/^-?\d*\.?\d*$/.test(next)) return
            onAmountChange(next === '' ? null : Number(next))
          }}
        />
      </div>
      {amountError ? <span className="nx-field__error">{amountError}</span> : null}
    </div>
  )
}

export interface ComboboxOption {
  value: string
  label: string
}

interface ComboboxProps {
  label?: string
  error?: string
  placeholder?: string
  options: ComboboxOption[]
  value: string | null
  onChange: (value: string | null) => void
  disabled?: boolean
  emptyMessage?: string
}

/** Type-to-filter select over a fixed, already-loaded option set. */
export function Combobox({
  label,
  error,
  placeholder = 'Buscar…',
  options,
  value,
  onChange,
  disabled,
  emptyMessage = 'Sin resultados.',
}: ComboboxProps) {
  const id = useId()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onPointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onEscape)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onEscape)
    }
  }, [open])

  const selected = options.find((option) => option.value === value) ?? null
  const filtered = options.filter((option) =>
    option.label.toLowerCase().includes(query.toLowerCase()),
  )

  return (
    <div className="nx-field nx-combobox" ref={rootRef}>
      {label ? (
        <label className="nx-field__label" htmlFor={id}>
          {label}
        </label>
      ) : null}
      <div className="nx-combobox__control">
        <input
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-listbox`}
          autoComplete="off"
          className={['nx-input', error ? 'nx-input--error' : ''].filter(Boolean).join(' ')}
          placeholder={selected?.label ?? placeholder}
          value={query}
          disabled={disabled}
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value)
            setOpen(true)
          }}
        />
        {open ? (
          <ul className="nx-combobox__listbox" id={`${id}-listbox`} role="listbox">
            {filtered.length === 0 ? (
              <li className="nx-combobox__empty">{emptyMessage}</li>
            ) : (
              filtered.map((option) => (
                <li key={option.value}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={option.value === value}
                    className="nx-combobox__option"
                    onClick={() => {
                      onChange(option.value)
                      setQuery('')
                      setOpen(false)
                    }}
                  >
                    {option.label}
                  </button>
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>
      {error ? <span className="nx-field__error">{error}</span> : null}
    </div>
  )
}
