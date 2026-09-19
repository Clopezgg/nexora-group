/**
 * NEXORA SAP GUI Classic — Workstation Shell
 * 
 * Composición completa de la estación de trabajo:
 * - Title Bar
 * - Menu Bar
 * - Command Bar + Toolbar (command row)
 * - Sidebar (Easy Access Tree)
 * - Main Area (Screen Frame + Topbar)
 * - Status Bar
 * - Responsive
 */

import { forwardRef, type ReactNode, useEffect, useState, useMemo } from 'react';
import { filterNavGroups } from '../../app/navigation';
import { useAuth } from '../../features/auth/auth-context';
import { useActiveCompany } from '../../hooks/useActiveCompany';
import { globalSearch } from '../../services/searchService';
import { SapTitleBar } from './SapTitleBar';
import { SapMenuBar } from './SapMenuBar';
import { SapCommandBar } from './SapCommandBar';
import { SapToolbar } from './SapToolbar';
import { SapTree } from './SapTree';
import { SapScreenFrame } from './SapScreenFrame';
import { SapStatusBar } from './SapStatusBar';
import { CommandPalette } from '../../design-system/primitives/CommandPalette';
import type { CommandItem } from '../../design-system/primitives/CommandPalette';
import { Drawer } from '../../design-system/primitives/Overlays';
import { SapButton } from './SapButton';
import { Topbar } from '../../layouts/Topbar';
import '../../sap-gui/tokens/sap-gui-tokens.css';
import './SapWorkstation.css';

export interface SapWorkstationProps {
  children?: ReactNode;
}

/**
 * SapWorkstation: Composición de presentación completa.
 * Reutiliza Outlet (vía SapScreenFrame), compañía/proyecto activos,
 * Protected Edit, usuario, notifications, command palette,
 * globalSearch, route definitions, permission filtering, logout y drawer responsive.
 * No duplica Router, auth ni permisos.
 */
export const SapWorkstation = forwardRef<HTMLDivElement, SapWorkstationProps>(
  ({ children }, ref) => {
    const [mobileNavOpen, setMobileNavOpen] = useState(false);
    const { activeCompanyId } = useActiveCompany();
    const { user, logout } = useAuth();
    const visibleGroups = filterNavGroups(user?.permissions);

    const commandItems = useMemo<CommandItem[]>(
      () =>
        visibleGroups.flatMap((group) =>
          group.items.map((item) => ({
            id: item.path,
            label: item.label,
            group: group.label,
            path: item.path,
          })),
        ),
      [visibleGroups],
    );

    const searchRemote = useMemo(() => {
      if (!activeCompanyId) return undefined;
      const companyId = activeCompanyId;
      return async (query: string): Promise<CommandItem[]> => {
        const results = await globalSearch(companyId, query);
        return results.map((result) => ({
          id: result.id,
          label: result.label,
          group: result.group,
          path: result.path,
        }));
      };
    }, [activeCompanyId]);

    const openSearch = () => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }));
    };

    // Focus management for drawer
    useEffect(() => {
      if (mobileNavOpen) {
        document.body.style.overflow = 'hidden';
      }
      return () => {
        document.body.style.overflow = '';
      };
    }, [mobileNavOpen]);

    return (
      <div ref={ref} className="nx-sap-workstation" role="application">
        {/* Title Bar */}
        <SapTitleBar />
        
        {/* Menu Bar */}
        <SapMenuBar 
          groups={visibleGroups} 
          onOpenSearch={openSearch} 
          onOpenNav={() => setMobileNavOpen(true)} 
        />
        
        {/* Command Row: Command Bar + Toolbar */}
        <div className="nx-sap-commandrow">
          <SapCommandBar items={commandItems} searchRemote={searchRemote} />
          <SapToolbar onOpenNav={() => setMobileNavOpen(true)} />
        </div>

        {/* Sidebar + Main Area */}
        <div className="nx-sap-workarea">
          {/* Sidebar / Easy Access Tree */}
          <aside 
            className="nx-sap-sidebar" 
            aria-label="NEXORA Easy Access"
            role="complementary"
          >
            <div className="nx-sap-sidebar__brand" aria-label="NEXORA Easy Access">
              <span className="nx-sap-sidebar__brand-mark" aria-hidden="true">
                <svg viewBox="0 0 32 32" width="24" height="24" aria-hidden="true">
                  <rect x="4" y="4" width="24" height="24" rx="2" fill="currentColor"/>
                  <text x="16" y="22" textAnchor="middle" fontSize="14" fontWeight="bold" fill="white" fontFamily="Arial">NX</text>
                </svg>
              </span>
              <span className="nx-sap-sidebar__brand-copy">
                <span className="nx-sap-sidebar__brand-name">NEXORA Easy Access</span>
                <span className="nx-sap-sidebar__brand-tagline">Navegación empresarial</span>
              </span>
            </div>
            <SapTree groups={filterNavGroups(user?.permissions)} variant="sidebar" />
          </aside>

          {/* Main Area */}
          <div className="nx-sap-main">
            {/* Topbar (contexto empresa/proyecto, Protected Edit, usuario, notificaciones) */}
            <Topbar onOpenNav={() => setMobileNavOpen(true)} />
            
            {/* Screen Frame + Outlet */}
            <main className="nx-sap-content" role="main">
              <SapScreenFrame />
              {children}
            </main>
          </div>
        </div>

        {/* Status Bar */}
        <SapStatusBar />

        {/* Mobile Drawer */}
        <Drawer
          open={mobileNavOpen}
          title="Navegación"
          side="left"
          onClose={() => setMobileNavOpen(false)}
        >
          <SapTree groups={filterNavGroups(user?.permissions)} variant="drawer" onNavigate={() => setMobileNavOpen(false)} />
          <div className="nx-sap-drawer__footer">
            <div className="nx-sap-drawer__user">
              <span className="nx-sap-drawer__user-name">{user?.fullName ?? user?.email}</span>
              {user?.roles?.[0] ? (
                <span className="nx-sap-drawer__user-role">{user.roles[0]}</span>
              ) : null}
            </div>
            <SapButton
              variant="standard"
              onClick={() => {
                setMobileNavOpen(false);
                logout();
              }}
            >
              Cerrar sesión
            </SapButton>
          </div>
        </Drawer>

        {/* Command Palette (global) */}
        <CommandPalette items={commandItems} searchRemote={searchRemote} />
      </div>
    );
  }
);

SapWorkstation.displayName = 'SapWorkstation';