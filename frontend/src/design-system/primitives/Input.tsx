import { forwardRef, useId, type InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, id, className, ...rest }, ref) => {
    const generatedId = useId()
    const inputId = id ?? rest.name ?? generatedId
    return (
      <div className="nx-field">
        {label ? (
          <label className="nx-field__label" htmlFor={inputId}>
            {label}
          </label>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          className={['nx-input', error ? 'nx-input--error' : '', className]
            .filter(Boolean)
            .join(' ')}
          aria-invalid={Boolean(error)}
          {...rest}
        />
        {error ? <span className="nx-field__error">{error}</span> : null}
      </div>
    )
  },
)
Input.displayName = 'Input'
