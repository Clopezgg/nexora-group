import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Button,
  Card,
  CompanySelector,
  EmptyState,
  Input,
  LoadingState,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { masterDataService } from '../../services/masterDataService'
import type { Company } from '../../types/masterData'

/**
 * NXR-REQ-0095: perfil editable de una compañía (Settings). code y
 * functional_currency_code son de solo lectura -- son inmutables
 * post-creación (CLAUDE.md, "no cambiar Company.functional_currency
 * post-creación"). Solo legal_name/fiscal_id se editan aquí.
 */
export function CompanySettingsPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading } = useActiveCompany()
  const queryClient = useQueryClient()

  const selectedCompany = companies.find((company) => company.id === activeCompanyId) ?? null

  const [form, setForm] = useState({ legalName: '', fiscalId: '' })
  // Ajuste de estado derivado durante el render (no un efecto) cuando
  // cambia la compañía seleccionada -- sincroniza el form con los datos
  // reales de esa compañía sin el patrón "setState dentro de useEffect".
  const [syncedCompanyId, setSyncedCompanyId] = useState<string | null>(null)
  if (selectedCompany && selectedCompany.id !== syncedCompanyId) {
    setSyncedCompanyId(selectedCompany.id)
    setForm({ legalName: selectedCompany.legalName ?? '', fiscalId: selectedCompany.fiscalId ?? '' })
  }

  const updateMutation = useMutation({
    mutationFn: () =>
      masterDataService.updateCompany(selectedCompany!.id, {
        legalName: form.legalName,
        fiscalId: form.fiscalId,
      }),
    onSuccess: (updatedCompany: Company) => {
      queryClient.invalidateQueries({ queryKey: ['master-data', 'companies'] })
      // Refleja el valor real devuelto por la API (puede ser
      // canonicalizado por el servidor), no lo que el usuario tecleó.
      setForm({ legalName: updatedCompany.legalName ?? '', fiscalId: updatedCompany.fiscalId ?? '' })
    },
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />

  if (companies.length === 0) {
    return (
      <EmptyState
        icon="tool"
        title="No hay compañías registradas"
        description="Crea una compañía antes de editar su perfil."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Configuración</h1>
      </header>

      <Card>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={setActiveCompanyId}
        />
      </Card>

      {selectedCompany ? (
        <Card title="Perfil de la compañía">
          <form
            onSubmit={(event) => {
              event.preventDefault()
              updateMutation.mutate()
            }}
          >
            <Input label="Código" value={selectedCompany.code ?? '—'} disabled readOnly />
            <Input
              label="Moneda funcional"
              value={selectedCompany.functionalCurrencyCode ?? '—'}
              disabled
              readOnly
            />
            <Input
              label="Razón social"
              name="legalName"
              value={form.legalName}
              onChange={(event) => setForm((prev) => ({ ...prev, legalName: event.target.value }))}
            />
            <Input
              label="Identificación fiscal"
              name="fiscalId"
              value={form.fiscalId}
              onChange={(event) => setForm((prev) => ({ ...prev, fiscalId: event.target.value }))}
            />

            <Button type="submit" loading={updateMutation.isPending}>
              Guardar cambios
            </Button>

            {updateMutation.isSuccess ? (
              <p className="nx-field__hint" role="status">
                Cambios guardados.
              </p>
            ) : null}
            {updateMutation.isError ? (
              <p className="nx-field__error" role="alert">
                {(updateMutation.error as Error).message}
              </p>
            ) : null}
          </form>
        </Card>
      ) : null}
    </div>
  )
}
