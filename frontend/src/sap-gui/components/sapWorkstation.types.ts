/**
 * NEXORA SAP GUI Classic — Workstation Types
 * 
 * Tipos compartidos para el sistema SAP Workstation.
 */

import type { NavGroup } from '../../app/navigation';

export interface SapWorkstationProps {
  children?: React.ReactNode;
}

export interface SapMenuBarProps {
  groups: NavGroup[];
  onOpenSearch: () => void;
  onOpenNav: () => void;
}

export interface SapCommandBarProps {
  items: CommandItem[];
  searchRemote: ((query: string) => Promise<CommandItem[]>) | undefined;
}

export interface SapToolbarProps {
  onOpenNav: () => void;
}

// Use type aliases for marker interfaces to avoid empty interface lint errors
export type SapScreenFrameProps = Record<string, never>;
export type SapStatusBarProps = Record<string, never>;
export type SapTitleBarProps = Record<string, never>;

export interface SapTreeProps {
  groups: NavGroup[];
  onNavigate?: () => void;
  variant?: 'sidebar' | 'drawer';
}

export interface CommandItem {
  id: string;
  label: string;
  group: string;
  path: string;
}