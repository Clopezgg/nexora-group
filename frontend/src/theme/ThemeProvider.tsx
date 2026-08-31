import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { preferencesService } from '../services/preferencesService'
import { masterDataService } from '../services/masterDataService'
import { useAuth } from '../features/auth/auth-context'
import { ThemeContext, type ThemeContextValue } from './theme-context'
import { DEFAULT_DENSITY, DEFAULT_THEME_ID, THEME_PRESETS, getThemePreset, type Density } from './themes'
import './themes.css'

function applyToDom(themeId: string, density: Density) {
  const preset = getThemePreset(themeId)
  const root = document.documentElement
  root.dataset.nxTheme = preset.id
  root.dataset.nxDensity = density
  // El Theme Engine gobierna SIEMPRE la presentación: NEXORA Horizon Light
  // (default) también re-pinta por variables. No hay un modo "sin tema".
  root.dataset.nxThemed = 'on'
  root.style.colorScheme = preset.isDark ? 'dark' : 'light'
  for (const [key, value] of Object.entries(preset.vars)) {
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

  const userThemeId = prefsQuery.data?.themeId ?? null
  const userDensity = (prefsQuery.data?.density as Density | null) ?? null
  const companyThemeId = companiesQuery.data?.[0]?.defaultThemeId ?? null
  const companyDensity = (companiesQuery.data?.[0]?.defaultDensity as Density | null) ?? null

  const activeThemeId = preview?.themeId ?? userThemeId ?? companyThemeId ?? DEFAULT_THEME_ID
  const activeDensity: Density = preview?.density ?? userDensity ?? companyDensity ?? DEFAULT_DENSITY

  useEffect(() => {
    applyToDom(activeThemeId, activeDensity)
  }, [activeThemeId, activeDensity])

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
      userThemeId,
      userDensity,
      presets: THEME_PRESETS,
      preview: (themeId, density) => setPreviewState({ themeId, density }),
      clearPreview: () => setPreviewState(null),
      save: (themeId, density) => saveMutation.mutateAsync({ themeId, density }),
      isSaving: saveMutation.isPending,
    }),
    [activeThemeId, activeDensity, userThemeId, userDensity, saveMutation],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
