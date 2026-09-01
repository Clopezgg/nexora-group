import { createContext, useContext } from 'react'
import type { Density, ThemeFamily, ThemePreset, UiScale } from './themes'

export interface ThemeContextValue {
  activeThemeId: string
  activeDensity: Density
  activeFamily: ThemeFamily
  /** Escala de UI (90 / 100 / 110) — per-dispositivo, no se persiste server-side. */
  uiScale: UiScale
  userThemeId: string | null
  userDensity: Density | null
  presets: ThemePreset[]
  preview: (themeId: string | null, density: Density | null) => void
  clearPreview: () => void
  save: (themeId: string | null, density: Density | null) => Promise<unknown>
  setUiScale: (scale: UiScale) => void
  isSaving: boolean
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
