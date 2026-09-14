/**
 * NEXORA SAP GUI Classic — Input Primitive
 * 
 * Campo de entrada compacto estilo SAP GUI Classic.
 * - Altura 28px (desktop)
 * - Border 1px, sin radius
 * - Fondo blanco, texto azul petróleo
 * - Read-only con fondo diferenciado
 * - Value Help (F4) integrado opcional
 */

import { forwardRef, type InputHTMLAttributes, type RefObject, useId } from 'react';
import './SapInput.css';

export interface SapInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  readOnly?: boolean;
  valueHelp?: boolean;
  onValueHelp?: () => void;
  inputRef?: RefObject<HTMLInputElement>;
}

export const SapInput = forwardRef<HTMLInputElement, SapInputProps>(
  ({ 
    label, 
    readOnly, 
    valueHelp, 
    onValueHelp, 
    className = '', 
    disabled, 
    id, 
    ...props 
  }, ref) => {
    const generatedId = useId();
    const inputId = id || `sap-input-${generatedId}`;
    
    return (
      <div className={`nx-sap-input-wrapper ${readOnly ? 'nx-readonly' : ''} ${disabled ? 'nx-disabled' : ''} ${valueHelp ? 'nx-with-valuehelp' : ''} ${className}`}>
        {label && <label htmlFor={inputId} className="nx-sap-input__label">{label}</label>}
        <div className="nx-sap-input__field-wrapper">
          <input
            ref={ref}
            id={inputId}
            className="nx-sap-input"
            readOnly={readOnly}
            disabled={disabled}
            {...props}
          />
          {valueHelp && (
            <button
              type="button"
              className="nx-sap-input__valuehelp"
              aria-label="Ayuda de valores (F4)"
              onClick={onValueHelp}
              disabled={disabled || readOnly}
              tabIndex={-1}
            >
              ▼
            </button>
          )}
        </div>
      </div>
    );
  }
);

SapInput.displayName = 'SapInput';

/**
 * Campo de solo lectura — solo muestra el valor, estilo read-only
 */
export interface SapDisplayFieldProps {
  label?: string;
  value: string | number | null | undefined;
  className?: string;
  unit?: string;
}

export const SapDisplayField = ({ label, value, className = '', unit }: SapDisplayFieldProps) => {
  return (
    <div className={`nx-sap-display-field ${className}`}>
      {label && <label className="nx-sap-display-field__label">{label}</label>}
      <div className="nx-sap-display-field__value">
        <span className="nx-sap-display-field__text">{value ?? ''}</span>
        {unit && <span className="nx-sap-display-field__unit">{unit}</span>}
      </div>
    </div>
  );
}

/**
 * ComboBox / Select estilo SAP GUI
 */
export interface SapSelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string;
  options: Array<{ value: string; label: string }>;
  placeholder?: string;
  valueHelp?: boolean;
  onValueHelp?: () => void;
}

export const SapSelect = forwardRef<HTMLSelectElement, SapSelectProps>(
  ({ label, options, placeholder, valueHelp, onValueHelp, className = '', disabled, id, ...props }, ref) => {
    const generatedId = useId();
    const selectId = id || `sap-select-${generatedId}`;
    
    return (
      <div className={`nx-sap-select-wrapper ${disabled ? 'nx-disabled' : ''} ${valueHelp ? 'nx-with-valuehelp' : ''} ${className}`}>
        {label && <label htmlFor={selectId} className="nx-sap-select__label">{label}</label>}
        <div className="nx-sap-select__field-wrapper">
          <select
            ref={ref}
            id={selectId}
            className="nx-sap-select"
            disabled={disabled}
            {...props}
          >
            {placeholder && <option value="" disabled>{placeholder}</option>}
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {valueHelp && (
            <button
              type="button"
              className="nx-sap-select__valuehelp"
              aria-label="Ayuda de valores (F4)"
              onClick={onValueHelp}
              disabled={disabled}
              tabIndex={-1}
            >
              ▼
            </button>
          )}
        </div>
      </div>
    );
  }
);

SapSelect.displayName = 'SapSelect';