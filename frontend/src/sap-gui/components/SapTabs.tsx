/**
 * NEXORA SAP GUI Classic — Tab Primitive
 * 
 * Pestañas estilo carpeta SAP GUI Classic (folder tabs).
 * - Esquinas rectas, sin redondeo
 * - Hombro diagonal (clip-path)
 * - Solo un tab stop
 * - Navegación por flechas, Home, End
 * - Estados: activo, inactivo, deshabilitado
 */

import { forwardRef, type ReactNode, useId, useRef, useState, useEffect } from 'react';
import './SapTabs.css';

export interface SapTabItem {
  key: string;
  label: string;
  content: ReactNode;
  disabled?: boolean;
}

export interface SapTabsProps {
  items: SapTabItem[];
  defaultKey?: string;
  activeKey?: string;
  onChange?: (key: string) => void;
  variant?: 'folder' | 'raised-folder' | 'modern-folder';
  className?: string;
}

export const SapTabs = forwardRef<HTMLDivElement, SapTabsProps>(
  ({ 
    items, 
    defaultKey, 
    activeKey, 
    onChange, 
    variant = 'folder',
    className = '' 
  }, ref) => {
  const instanceId = useId();
  const tabRefs = useRef(new Map<string, HTMLButtonElement>());
  const enabledItems = items.filter((item) => !item.disabled);
  const [internalActive, setInternalActive] = useState(defaultKey ?? enabledItems[0]?.key);
  const requestedActive = activeKey ?? internalActive;
  const active = enabledItems.some((item) => item.key === requestedActive)
    ? requestedActive
    : enabledItems[0]?.key;
  const activeItem = items.find((item) => item.key === active);

  const tabId = (key: string) => `${instanceId}-tab-${key}`;
  const panelId = `${instanceId}-panel`;

  const setActive = (key: string) => {
    if (activeKey === undefined) setInternalActive(key);
    onChange?.(key);
  };

  // Keyboard navigation
  useEffect(() => {
    const activeTab = tabRefs.current.get(active);
    if (activeTab) {
      activeTab.focus();
    }
  }, [active]);

  return (
    <div
      ref={ref}
      className={`nx-sap-tabs nx-sap-tabs--${variant} ${className}`}
      data-nx-tabs={variant}
    >
      <div className="nx-sap-tabs__list" role="tablist" aria-label="Pestañas">
        {items.map((item) => {
          const isActive = active === item.key;
          const index = items.findIndex((i) => i.key === item.key);
          return (
            <button
              key={item.key}
              ref={(node) => {
                if (node) tabRefs.current.set(item.key, node);
                else tabRefs.current.delete(item.key);
              }}
              role="tab"
              id={tabId(item.key)}
              aria-controls={panelId}
              aria-selected={isActive}
              tabIndex={isActive ? 0 : -1}
              disabled={item.disabled}
              type="button"
              className={[
                'nx-sap-tabs__tab',
                isActive ? 'nx-sap-tabs__tab--active' : '',
                item.disabled ? 'nx-disabled' : '',
              ].filter(Boolean).join(' ')}
              onClick={() => {
                if (!item.disabled) setActive(item.key);
              }}
              onKeyDown={(event) => {
                const enabledIndices = items
                  .map((i, idx) => (i.disabled ? -1 : idx))
                  .filter((idx) => idx !== -1);
                const currentEnabledIndex = enabledIndices.indexOf(index);
                let nextEnabledIndex: number;

                switch (event.key) {
                  case 'ArrowRight':
                    event.preventDefault();
                    nextEnabledIndex = (currentEnabledIndex + 1) % enabledIndices.length;
                    break;
                  case 'ArrowLeft':
                    event.preventDefault();
                    nextEnabledIndex = (currentEnabledIndex - 1 + enabledIndices.length) % enabledIndices.length;
                    break;
                  case 'Home':
                    event.preventDefault();
                    nextEnabledIndex = 0;
                    break;
                  case 'End':
                    event.preventDefault();
                    nextEnabledIndex = enabledIndices.length - 1;
                    break;
                  default:
                    return;
                }
                const nextItem = items[enabledIndices[nextEnabledIndex]];
                if (nextItem) {
                  event.preventDefault();
                  setActive(nextItem.key);
                  tabRefs.current.get(nextItem.key)?.focus();
                }
              }}
            >
              {item.label}
            </button>
          )
        })}
      </div>
      <div
        className="nx-sap-tabs__panel"
        role="tabpanel"
        id={panelId}
        aria-labelledby={active ? tabId(active) : undefined}
        tabIndex={0}
      >
        {activeItem?.content}
      </div>
    </div>
  );
});

SapTabs.displayName = 'SapTabs';