import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { preferencesService } from '../services/preferencesService'
import { masterDataService } from '../services/masterDataService'
import { useAuth } from '../features/auth/auth-context'
import { ThemeContext, type ThemeContextValue } from './theme-context'
import {
  compileTheme,
  DEFAULT_DENSITY,
  DEFAULT_THEME_ID,
  DEFAULT_UI_SCALE,
  THEME_PRESETS,
  UI_SCALES,
  getThemePreset,
  type Density,
  type UiScale,
} from './themes'
import './themes.css'

const UI_SCALE_KEY = 'nx.ui-scale'

function readUiScale(): UiScale {
  try {
    const raw = Number(window.localStorage.getItem(UI_SCALE_KEY))
    return (UI_SCALES as number[]).includes(raw) ? (raw as UiScale) : DEFAULT_UI_SCALE
  } catch {
    return DEFAULT_UI_SCALE
  }
}

function applyToDom(themeId: string, density: Density, scale: UiScale) {
  const preset = getThemePreset(themeId)
  const root = document.documentElement
  root.dataset.nxTheme = preset.id
  root.dataset.nxFamily = preset.family
  root.dataset.nxDensity = density
  root.dataset.nxContrast = preset.contrast
  // El Theme Engine gobierna SIEMPRE la presentación: NEXORA Horizon
  // (default) también re-pinta por variables. No hay un modo "sin tema".
  root.dataset.nxThemed = 'on'
  root.style.colorScheme = preset.isDark ? 'dark' : 'light'
  for (const [key, value] of Object.entries(compileTheme(preset, density, scale))) {
    root.style.setProperty(key, value)
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const prefsQuery = useQuery({
    queryKey: ['me', 'preferences'],
    queryFn: preferencesService.get,
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(user),
  })
  const companiesQuery = useQuery({
    queryKey: ['master-data', 'companies'],
    queryFn: masterDataService.listCompanies,
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(user),
  })

  const [preview, setPreviewState] = useState<{ themeId: string | null; density: Density | null } | null>(null)
  const [uiScale, setUiScaleState] = useState<UiScale>(() => readUiScale())

  const userThemeId = prefsQuery.data?.themeId ?? null
  const userDensity = (prefsQuery.data?.density as Density | null) ?? null
  const companyThemeId = companiesQuery.data?.[0]?.defaultThemeId ?? null
  const companyDensity = (companiesQuery.data?.[0]?.defaultDensity as Density | null) ?? null

  const activeThemeId = preview?.themeId ?? userThemeId ?? companyThemeId ?? DEFAULT_THEME_ID
  const activeDensity: Density =
    preview?.density ?? userDensity ?? companyDensity ?? getThemePreset(activeThemeId).densityDefault ?? DEFAULT_DENSITY
  const activeFamily = getThemePreset(activeThemeId).family

  useEffect(() => {
    applyToDom(activeThemeId, activeDensity, uiScale)
  }, [activeThemeId, activeDensity, uiScale])

  const setUiScale = useCallback((scale: UiScale) => {
    setUiScaleState(scale)
    try {
      window.localStorage.setItem(UI_SCALE_KEY, String(scale))
    } catch {
      /* almacenamiento no disponible — el cambio vive solo esta sesión */
    }
  }, [])

  const saveMutation = useMutation({
    mutationFn: (body: { themeId: string | null; density: Density | null }) =>
      preferencesService.update(body),
    onSuccess: () => {
      setPreviewState(null)
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })

  const value = useMemo<ThemeContextValue>(
    () => ({
      activeThemeId,
      activeDensity,
      activeFamily,
      uiScale,
      userThemeId,
      userDensity,
      presets: THEME_PRESETS,
      preview: (themeId, density) => setPreviewState({ themeId, density }),
      clearPreview: () => setPreviewState(null),
      save: (themeId, density) => saveMutation.mutateAsync({ themeId, density }),
      setUiScale,
      isSaving: saveMutation.isPending,
    }),
    [activeThemeId, activeDensity, activeFamily, uiScale, userThemeId, userDensity, saveMutation, setUiScale],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
