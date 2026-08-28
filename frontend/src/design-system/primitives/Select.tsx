import { forwardRef, useId, type ReactNode, type SelectHTMLAttributes } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  children: ReactNode
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, id, className, children, ...rest }, ref) => {
    const generatedId = useId()
    const selectId = id ?? rest.name ?? generatedId
    return (
      <div className="nx-field">
        {label ? (
          <label className="nx-field__label" htmlFor={selectId}>
            {label}
          </label>
        ) : null}
        <select
          ref={ref}
          id={selectId}
          className={['nx-select', error ? 'nx-select--error' : '', className]
            .filter(Boolean)
            .join(' ')}
          aria-invalid={Boolean(error)}
          {...rest}
        >
          {children}
        </select>
        {error ? <span className="nx-field__error">{error}</span> : null}
      </div>
    )
  },
)
Select.displayName = 'Select'
