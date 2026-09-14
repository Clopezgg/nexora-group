/**
 * NEXORA SAP GUI Classic — Button Primitive
 * 
 * Botón compacto estilo SAP GUI Classic (JPL Signature / Tradeshow).
 * - Altura fija 28px (desktop)
 * - Bevel clásico (gradiente JPL) para botones estándar
 * - Gradiente azul para botones primarios
 * - Un solo tab stop, navegación por teclado
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import '../../sap-gui/tokens/sap-gui-tokens.css';

export interface SapButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'standard' | 'primary' | 'danger' | 'toolbar';
  size?: 'standard' | 'compact';
  iconOnly?: boolean;
  children: ReactNode;
}

export const SapButton = forwardRef<HTMLButtonElement, SapButtonProps>(
  ({ variant = 'standard', size = 'standard', iconOnly, children, className = '', disabled, ...props }, ref) => {
    const baseClass = 'nx-sap-btn';
    const variantClass = `nx-sap-btn--${variant}`;
    const sizeClass = `nx-sap-btn--${size}`;
    const iconClass = iconOnly ? 'nx-sap-btn--icon-only' : '';
    const disabledClass = disabled ? 'nx-disabled' : '';
    
    return (
      <button
        ref={ref}
        className={`${baseClass} ${variantClass} ${sizeClass} ${iconClass} ${disabledClass} ${className}`.trim()}
        disabled={disabled}
        {...props}
      >
        <span className="nx-sap-btn__content">{children}</span>
      </button>
    );
  }
);

SapButton.displayName = 'SapButton';

/**
 * Botón de toolbar (icono solo, 28x28px)
 */
export interface SapToolbarButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  label: string;
  pressed?: boolean;
}

export const SapToolbarButton = forwardRef<HTMLButtonElement, SapToolbarButtonProps>(
  ({ icon, label, pressed, className = '', disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`nx-sap-toolbar-btn ${pressed ? 'nx-pressed' : ''} ${className}`.trim()}
        disabled={disabled}
        aria-label={label}
        aria-pressed={pressed}
        title={label}
        {...props}
      >
        <span className="nx-sap-toolbar-btn__icon">{icon}</span>
      </button>
    );
  }
);

SapToolbarButton.displayName = 'SapToolbarButton';

/**
 * Botón de comando (para command field) — compacto con checkmark
 */
export interface SapCommandButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  checked?: boolean;
}

export const SapCommandButton = forwardRef<HTMLButtonElement, SapCommandButtonProps>(
  ({ children, checked, className = '', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`nx-sap-cmd-btn ${checked ? 'nx-checked' : ''} ${className}`.trim()}
        aria-checked={checked}
        {...props}
      >
        {children}
      </button>
    );
  }
);

SapCommandButton.displayName = 'SapCommandButton';