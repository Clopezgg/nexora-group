/**
 * Enterprise Theme Engine — presets (orden maestra FINAL, Phase 8).
 *
 * REGLA §68: un tema es PURAMENTE presentación. Nunca toca moneda, cálculos,
 * permisos, contabilidad, workflow ni estado de negocio. Todo lo que hay aquí
 * son variables CSS (color, tipografía, radio). La densidad se maneja aparte.
 *
 * Sin CSS ni logos propietarios de SAP. Las tipografías son del sistema u
 * open-source (Inter). Los presets están "inspirados en" direcciones de
 * diseño empresarial (Horizon, Quartz/Fiori 3) — implementación 100% NEXORA.
 */

export type Density = 'comfortable' | 'compact'

export interface ThemePreset {
  id: string
  name: string
  description: string
  isDark: boolean
  /** Variables CSS que se inyectan en :root al activar el tema. */
  vars: Record<string, string>
}

const INTER = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
const SYSTEM = "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"

export const THEME_PRESETS: ThemePreset[] = [
  {
    id: 'nexora-horizon-light',
    name: 'NEXORA Horizon Light',
    description:
      'El tema por defecto de NEXORA: superficies blancas, fondo gris azulado, azul eléctrico como accent. Limpio y denso, dirección enterprise light clean.',
    isDark: false,
    vars: {
      '--nx-theme-page-bg': '#eef3f9',
      '--nx-theme-surface-2': '#f4f7fb',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#ffffff',
      '--nx-theme-text': '#102844',
      '--nx-theme-text-muted': '#4f6176',
      '--nx-theme-border': '#dce5ef',
      '--nx-theme-accent': '#1769d2',
      '--nx-theme-sidebar-bg': '#0b274a',
      '--nx-theme-sidebar-text': '#c7d7ea',
      '--nx-theme-radius': '9px',
      '--nx-theme-font': INTER,
    },
  },
  {
    id: 'nexora-classic',
    name: 'NEXORA Classic',
    description: 'El azul ejecutivo clásico de NEXORA (repinta por variables).',
    isDark: false,
    vars: {
      '--nx-theme-page-bg': '#eef3f9',
      '--nx-theme-surface-2': '#eef3f9',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#ffffff',
      '--nx-theme-text': '#102844',
      '--nx-theme-text-muted': '#4f6176',
      '--nx-theme-border': '#dce5ef',
      '--nx-theme-accent': '#1769d2',
      '--nx-theme-sidebar-bg': '#0b274a',
      '--nx-theme-sidebar-text': '#c7d7ea',
      '--nx-theme-radius': '9px',
      '--nx-theme-font': INTER,
    },
  },
  {
    id: 'nexora-dark',
    name: 'NEXORA Dark',
    description: 'Modo oscuro de NEXORA para salas de control.',
    isDark: true,
    vars: {
      '--nx-theme-page-bg': '#0b1220',
      '--nx-theme-surface-2': '#1b2740',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#141d2e',
      '--nx-theme-text': '#e7edf6',
      '--nx-theme-text-muted': '#9fb0c6',
      '--nx-theme-border': '#26324a',
      '--nx-theme-accent': '#55a3ff',
      '--nx-theme-sidebar-bg': '#0a0f1a',
      '--nx-theme-sidebar-text': '#c7d7ea',
      '--nx-theme-radius': '9px',
      '--nx-theme-font': INTER,
    },
  },
  {
    id: 'horizon-light',
    name: 'Horizon (claro)',
    description: 'Superficies planas y bordes suaves, inspirado en Horizon.',
    isDark: false,
    vars: {
      '--nx-theme-page-bg': '#f5f6f7',
      '--nx-theme-surface-2': '#eef1f4',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#ffffff',
      '--nx-theme-text': '#1d2d3e',
      '--nx-theme-text-muted': '#556b82',
      '--nx-theme-border': '#e5e9ee',
      '--nx-theme-accent': '#0a6ed1',
      '--nx-theme-sidebar-bg': '#1d2d3e',
      '--nx-theme-sidebar-text': '#cfd8e3',
      '--nx-theme-radius': '8px',
      '--nx-theme-font': SYSTEM,
    },
  },
  {
    id: 'horizon-dark',
    name: 'Horizon (oscuro)',
    description: 'Horizon en modo oscuro.',
    isDark: true,
    vars: {
      '--nx-theme-page-bg': '#12171c',
      '--nx-theme-surface-2': '#242c33',
      '--nx-theme-accent-contrast': '#0b0f12',
      '--nx-theme-surface': '#1c2329',
      '--nx-theme-text': '#eaeef2',
      '--nx-theme-text-muted': '#a7b4c0',
      '--nx-theme-border': '#2c353d',
      '--nx-theme-accent': '#4db1ff',
      '--nx-theme-sidebar-bg': '#0c1013',
      '--nx-theme-sidebar-text': '#cfd8e3',
      '--nx-theme-radius': '8px',
      '--nx-theme-font': SYSTEM,
    },
  },
  {
    id: 'quartz-light',
    name: 'Quartz (claro)',
    description: 'Aire y contraste alto, inspirado en Fiori 3 / Quartz.',
    isDark: false,
    vars: {
      '--nx-theme-page-bg': '#fafafa',
      '--nx-theme-surface-2': '#f2f2f2',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#ffffff',
      '--nx-theme-text': '#32363a',
      '--nx-theme-text-muted': '#6a6d70',
      '--nx-theme-border': '#e0e0e0',
      '--nx-theme-accent': '#0854a0',
      '--nx-theme-sidebar-bg': '#354a5f',
      '--nx-theme-sidebar-text': '#d9e0e7',
      '--nx-theme-radius': '6px',
      '--nx-theme-font': SYSTEM,
    },
  },
  {
    id: 'quartz-dark',
    name: 'Quartz (oscuro)',
    description: 'Quartz en modo oscuro.',
    isDark: true,
    vars: {
      '--nx-theme-page-bg': '#1c1c1c',
      '--nx-theme-surface-2': '#35383b',
      '--nx-theme-accent-contrast': '#0b0f14',
      '--nx-theme-surface': '#2a2c2e',
      '--nx-theme-text': '#eaecee',
      '--nx-theme-text-muted': '#a9adb0',
      '--nx-theme-border': '#3a3d40',
      '--nx-theme-accent': '#5fb0ff',
      '--nx-theme-sidebar-bg': '#121314',
      '--nx-theme-sidebar-text': '#d9e0e7',
      '--nx-theme-radius': '6px',
      '--nx-theme-font': SYSTEM,
    },
  },
  {
    id: 'high-contrast',
    name: 'Alto contraste — Negro',
    description: 'Fondo negro, texto blanco. Máxima legibilidad para accesibilidad.',
    isDark: true,
    vars: {
      '--nx-theme-page-bg': '#000000',
      '--nx-theme-surface-2': '#0a0a0a',
      '--nx-theme-accent-contrast': '#000000',
      '--nx-theme-surface': '#000000',
      '--nx-theme-text': '#ffffff',
      '--nx-theme-text-muted': '#e0e0e0',
      '--nx-theme-border': '#ffffff',
      '--nx-theme-accent': '#ffd500',
      '--nx-theme-sidebar-bg': '#000000',
      '--nx-theme-sidebar-text': '#ffffff',
      '--nx-theme-radius': '0px',
      '--nx-theme-font': SYSTEM,
    },
  },
  {
    id: 'high-contrast-white',
    name: 'Alto contraste — Blanco',
    description: 'Fondo blanco, texto negro y bordes definidos. Accesibilidad, no depende solo del color.',
    isDark: false,
    vars: {
      '--nx-theme-page-bg': '#ffffff',
      '--nx-theme-surface-2': '#f0f0f0',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#ffffff',
      '--nx-theme-text': '#000000',
      '--nx-theme-text-muted': '#1a1a1a',
      '--nx-theme-border': '#000000',
      '--nx-theme-accent': '#0000cc',
      '--nx-theme-sidebar-bg': '#ffffff',
      '--nx-theme-sidebar-text': '#000000',
      '--nx-theme-radius': '0px',
      '--nx-theme-font': SYSTEM,
    },
  },
  {
    id: 'nexora-executive',
    name: 'NEXORA Executive',
    description: 'Serio, denso en tipografía, para el comité financiero.',
    isDark: false,
    vars: {
      '--nx-theme-page-bg': '#f2f0ec',
      '--nx-theme-surface-2': '#eae7df',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#ffffff',
      '--nx-theme-text': '#1b1a17',
      '--nx-theme-text-muted': '#5a564d',
      '--nx-theme-border': '#ddd8ce',
      '--nx-theme-accent': '#7a5c1e',
      '--nx-theme-sidebar-bg': '#26241f',
      '--nx-theme-sidebar-text': '#d9d3c5',
      '--nx-theme-radius': '4px',
      '--nx-theme-font': "'Inter', Georgia, 'Times New Roman', serif",
    },
  },
  {
    id: 'nexora-compact-finance',
    name: 'NEXORA Compact Finance',
    description: 'NEXORA Classic con densidad compacta para pantallas con muchas cifras.',
    isDark: false,
    vars: {
      '--nx-theme-page-bg': '#eef2f7',
      '--nx-theme-surface-2': '#e7edf4',
      '--nx-theme-accent-contrast': '#ffffff',
      '--nx-theme-surface': '#ffffff',
      '--nx-theme-text': '#0f2033',
      '--nx-theme-text-muted': '#4a5a6c',
      '--nx-theme-border': '#d7e0ea',
      '--nx-theme-accent': '#125aab',
      '--nx-theme-sidebar-bg': '#0b274a',
      '--nx-theme-sidebar-text': '#c7d7ea',
      '--nx-theme-radius': '5px',
      '--nx-theme-font': INTER,
    },
  },
]

export const DEFAULT_THEME_ID = 'nexora-horizon-light'
export const DEFAULT_DENSITY: Density = 'comfortable'

export function getThemePreset(id: string | null | undefined): ThemePreset {
  return THEME_PRESETS.find((preset) => preset.id === id) ?? THEME_PRESETS[0]
}
