import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, Select } from '../../design-system'
import { useAuth } from '../../features/auth/auth-context'
import { masterDataService } from '../../services/masterDataService'
import { useTheme } from '../../theme/theme-context'
import {
  compileTheme,
  DENSITIES,
  DENSITY_LABEL,
  getThemePreset,
  UI_SCALES,
  type Density,
  type ThemeFamily,
  type UiScale,
} from '../../theme/themes'
import { CompanyBrandingCard } from './CompanyBrandingCard'
import './ThemeSettingsCard.css'

const FAMILY_LABEL: Record<ThemeFamily, string> = {
  nexora: 'NEXORA', horizon: 'Horizon', quartz: 'Quartz', belize: 'Belize',
}

/** Vista previa exclusivamente estructural. Nunca muestra importes ficticios:
 * prueba shell/sidebar/header/KPI/table/filter/form/dialog/chart anatomy without
 * pretending those values are company data. */
function ThemePreviewApp({ themeId, density, scale }: { themeId: string; density: Density; scale: UiScale }) {
  const preset = getThemePreset(themeId)
  const style = compileTheme(preset, density, scale) as React.CSSProperties
  return (
    <div className="nx-theme-preview" style={style} aria-label={`Vista previa estructural de ${preset.name}`}>
      <div className="nx-theme-preview__shell">
        <div className="nx-theme-preview__sidebar">
          <span className="nx-theme-preview__brand">NEXORA</span>
          <span className="nx-theme-preview__nav nx-theme-preview__nav--active">Finanzas</span>
          <span className="nx-theme-preview__nav">Proyectos</span>
          <span className="nx-theme-preview__nav">Tesorería</span>
        </div>
        <div className="nx-theme-preview__main">
          <div className="nx-theme-preview__topbar">
            <strong>Centro operativo</strong>
            <span className="nx-theme-preview__chip">Vista previa</span>
          </div>
          <div className="nx-theme-preview__kpis">
            {['Posición financiera', 'Obligaciones', 'Aprobaciones'].map((label) => (
              <div key={label} className="nx-theme-preview__kpi">{label}</div>
            ))}
          </div>
          <table className="nx-theme-preview__table">
            <thead><tr><th>Proceso</th><th>Estado</th><th>Acción</th></tr></thead>
            <tbody>
              <tr><td>Contrato de ejecución</td><td>Activo</td><td>Ver obligaciones</td></tr>
              <tr><td>Pago contractual</td><td>Pendiente</td><td>Revisar</td></tr>
            </tbody>
          </table>
          <div className="nx-theme-preview__filterbar">
            <span className="nx-theme-preview__field-label">Categoría</span>
            <span className="nx-theme-preview__input">Todas</span>
          </div>
          <div className="nx-theme-preview__form">
            <span className="nx-theme-preview__field-label">Beneficiario</span>
            <span className="nx-theme-preview__input">Buscar…</span>
            <button className="nx-theme-preview__btn" type="button" tabIndex={-1}>Continuar</button>
            <span className="nx-theme-preview__status nx-theme-preview__status--ok">Conciliado</span>
            <span className="nx-theme-preview__status nx-theme-preview__status--warn">Pendiente</span>
          </div>
          <div className="nx-theme-preview__chart" aria-hidden="true">
            {[40, 70, 55, 90, 65, 80].map((height, index) => <span key={index} style={{ height: `${height}%` }} />)}
          </div>
          <div className="nx-theme-preview__dialog" aria-hidden="true">
            <div className="nx-theme-preview__dialog-header">Confirmar operación</div>
            <div className="nx-theme-preview__dialog-body">Revisa contexto, estado y trazabilidad antes de continuar.</div>
          </div>
        </div>
      </div>
    </div>
  )
}

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
  const {
    presets,
    activeThemeId,
    activeDensity,
    uiScale,
    userThemeId,
    userDensity,
    preview,
    clearPreview,
    save,
    setUiScale,
    isSaving,
  } = useTheme()

  const [draftTheme, setDraftTheme] = useState<string>(userThemeId ?? activeThemeId)
  const [draftDensity, setDraftDensity] = useState<Density>(userDensity ?? activeDensity)

  const families = useMemo(() => {
    const order: ThemeFamily[] = ['nexora', 'horizon', 'quartz', 'belize']
    return order.filter((family) => presets.some((preset) => preset.family === family))
  }, [presets])
  const draftFamily = getThemePreset(draftTheme).family
  const familyPresets = presets.filter((preset) => preset.family === draftFamily)

  const applyPreview = (themeId: string, density: Density) => {
    setDraftTheme(themeId)
    setDraftDensity(density)
    preview(themeId, density)
  }

  const setCompanyDefault = useMutation({
    mutationFn: () => masterDataService.updateCompany(companyId as string, {
      defaultThemeId: activeThemeId,
      defaultDensity: activeDensity,
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['master-data', 'companies'] }),
  })

  return (
    <>
      <Card title="Apariencia (Theme Engine)">
        <p className="nx-field__hint">
          El tema es solo presentación: nunca cambia cifras, permisos ni contabilidad. Cada familia cambia anatomía visual — radio, densidad, elevación, tablas, inputs, diálogos, filter bars y object headers — además de la paleta. La mini-aplicación es una muestra estructural sin datos financieros ficticios.
        </p>

        <div className="nx-theme-settings">
          <div className="nx-theme-settings__controls">
            <Select
              label="Familia"
              value={draftFamily}
              onChange={(event) => {
                const family = event.target.value as ThemeFamily
                const first = presets.find((preset) => preset.family === family)
                if (first) applyPreview(first.id, draftDensity)
              }}
            >
              {families.map((family) => <option key={family} value={family}>{FAMILY_LABEL[family]}</option>)}
            </Select>

            <Select label="Variante" value={draftTheme} onChange={(event) => applyPreview(event.target.value, draftDensity)}>
              {familyPresets.map((preset) => <option key={preset.id} value={preset.id}>{preset.name}</option>)}
            </Select>

            <Select label="Densidad" value={draftDensity} onChange={(event) => applyPreview(draftTheme, event.target.value as Density)}>
              {DENSITIES.map((density) => <option key={density} value={density}>{DENSITY_LABEL[density]}</option>)}
            </Select>

            <Select label="Escala de la interfaz" value={String(uiScale)} onChange={(event) => setUiScale(Number(event.target.value) as UiScale)}>
              {UI_SCALES.map((scale) => <option key={scale} value={scale}>{scale}%</option>)}
            </Select>

            <p className="nx-field__hint">
              {getThemePreset(draftTheme).description}
              {getThemePreset(draftTheme).contrast === 'high' ? ' · Alto contraste.' : ''}
            </p>
            {companyDefaultThemeId === draftTheme ? <Badge tone="neutral">Predeterminado de la compañía</Badge> : null}
            {companyDefaultDensity ? <p className="nx-field__hint">Densidad predeterminada de la compañía: {companyDefaultDensity}</p> : null}
          </div>

          <div className="nx-theme-settings__preview">
            <span className="nx-theme-settings__preview-label">Vista previa estructural</span>
            <ThemePreviewApp themeId={draftTheme} density={draftDensity} scale={uiScale} />
          </div>
        </div>

        <div className="nx-treasury__actions">
          <Button loading={isSaving} onClick={() => save(draftTheme, draftDensity)}>Guardar como mi preferencia</Button>
          <Button variant="secondary" onClick={() => { void save(null, null) }}>Volver a heredar</Button>
          <Button variant="secondary" onClick={clearPreview}>Cancelar vista previa</Button>
          {isAdmin && companyId ? (
            <Button variant="secondary" loading={setCompanyDefault.isPending} onClick={() => setCompanyDefault.mutate()}>
              Fijar el tema actual como predeterminado de la compañía
            </Button>
          ) : null}
        </div>
        {setCompanyDefault.isSuccess ? <p className="nx-field__hint" role="status">Predeterminado de la compañía actualizado.</p> : null}
      </Card>
      {isAdmin && companyId ? <CompanyBrandingCard companyId={companyId} /> : null}
    </>
  )
}
