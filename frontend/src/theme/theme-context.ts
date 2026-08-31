import { createContext, useContext } from 'react'
import type { Density, ThemePreset } from './themes'

export interface ThemeContextValue {
  activeThemeId: string
  activeDensity: Density
  userThemeId: string | null
  userDensity: Density | null
  presets: ThemePreset[]
  preview: (themeId: string | null, density: Density | null) => void
  clearPreview: () => void
  save: (themeId: string | null, density: Density | null) => Promise<unknown>
  isSaving: boolean
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
