import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, Select } from '../../design-system'
import { useAuth } from '../../features/auth/auth-context'
import { masterDataService } from '../../services/masterDataService'
import { useTheme } from '../../theme/theme-context'
import type { Density } from '../../theme/themes'
import './ThemeSettingsCard.css'

export function ThemeSettingsCard({
  companyId,
  companyDefaultThemeId,
  companyDefaultDensity,
}: {
  companyId: string | null
  companyDefaultThemeId: string | null
  companyDefaultDensity: string | null
}) {
  const { user } = useAuth()
  const isAdmin = (user?.roles ?? []).includes('Administrator')
  const queryClient = useQueryClient()
  const { presets, activeThemeId, activeDensity, userThemeId, userDensity, preview, clearPreview, save, isSaving } =
    useTheme()

  const [draftTheme, setDraftTheme] = useState<string | null>(userThemeId)
  const [draftDensity, setDraftDensity] = useState<Density | null>(userDensity)

  const applyPreview = (themeId: string | null, density: Density | null) => {
    setDraftTheme(themeId)
    setDraftDensity(density)
    preview(themeId, density)
  }

  const setCompanyDefault = useMutation({
    mutationFn: () =>
      masterDataService.updateCompany(companyId as string, {
        defaultThemeId: activeThemeId,
        defaultDensity: activeDensity,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['master-data', 'companies'] }),
  })

  return (
    <Card title="Apariencia (Theme Engine)">
      <p className="nx-field__hint">
        El tema es solo presentación: nunca cambia cifras, permisos ni contabilidad. Cascada de
        resolución: tu preferencia → predeterminado de la compañía → NEXORA Classic.
      </p>

      <div className="nx-theme-grid">
        {presets.map((preset) => {
          const selected = (draftTheme ?? activeThemeId) === preset.id
          return (
            <button
              key={preset.id}
              type="button"
              className={`nx-theme-swatch${selected ? ' nx-theme-swatch--selected' : ''}`}
              style={{
                background: preset.vars['--nx-theme-page-bg'],
                color: preset.vars['--nx-theme-text'],
                borderColor: selected ? preset.vars['--nx-theme-accent'] : preset.vars['--nx-theme-border'],
              }}
              onMouseEnter={() => preview(preset.id, draftDensity)}
              onMouseLeave={() => preview(draftTheme, draftDensity)}
              onFocus={() => preview(preset.id, draftDensity)}
              onClick={() => applyPreview(preset.id, draftDensity)}
            >
              <span className="nx-theme-swatch__dot" style={{ background: preset.vars['--nx-theme-accent'] }} />
              <span className="nx-theme-swatch__name">{preset.name}</span>
              <span className="nx-theme-swatch__desc">{preset.description}</span>
              {preset.id === companyDefaultThemeId ? (
                <Badge tone="neutral">Predeterminado de la compañía</Badge>
              ) : null}
              {preset.isDark ? <Badge tone="info">Oscuro</Badge> : null}
            </button>
          )
        })}
      </div>

      <Select
        label="Densidad"
        value={draftDensity ?? activeDensity}
        onChange={(event) => applyPreview(draftTheme, event.target.value as Density)}
      >
        <option value="comfortable">Cómoda</option>
        <option value="compact">Compacta (pantallas con muchas cifras)</option>
      </Select>
      {companyDefaultDensity ? (
        <p className="nx-field__hint">Densidad predeterminada de la compañía: {companyDefaultDensity}</p>
      ) : null}

      <div className="nx-treasury__actions">
        <Button
          loading={isSaving}
          onClick={() => save(draftTheme, draftDensity)}
        >
          Guardar como mi preferencia
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            setDraftTheme(null)
            setDraftDensity(null)
            void save(null, null)
          }}
        >
          Volver a heredar
        </Button>
        <Button variant="secondary" onClick={clearPreview}>
          Cancelar vista previa
        </Button>
        {isAdmin && companyId ? (
          <Button
            variant="secondary"
            loading={setCompanyDefault.isPending}
            onClick={() => setCompanyDefault.mutate()}
          >
            Fijar el tema actual como predeterminado de la compañía
          </Button>
        ) : null}
      </div>
      {setCompanyDefault.isSuccess ? (
        <p className="nx-field__hint" role="status">Predeterminado de la compañía actualizado.</p>
      ) : null}
    </Card>
  )
}
