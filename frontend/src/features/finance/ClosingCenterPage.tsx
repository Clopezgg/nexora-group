import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { closingService, type ClosingCheck } from '../../services/closingService'
import { fiscalService } from '../../services/fiscalService'

export function ClosingCenterPage() {
  const handleMutationError = useMutationError()
  const queryClient = useQueryClient()
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()
  const [periodId, setPeriodId] = useState('')
  const [reason, setReason] = useState('')

  const periodsQuery = useQuery({
    queryKey: ['fiscal', 'periods', activeCompanyId],
    queryFn: () => fiscalService.listPeriods(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const checklistQuery = useQuery({
    queryKey: ['closing', 'checklist', activeCompanyId, periodId],
    queryFn: () => closingService.checklist(activeCompanyId as string, periodId),
    enabled: Boolean(activeCompanyId && periodId),
  })

  const hardClose = useMutation({
    mutationFn: (force: boolean) =>
      closingService.hardClose(activeCompanyId as string, periodId, {
        force,
        reason: reason.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal', 'periods', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['closing', 'checklist', activeCompanyId, periodId] })
      setReason('')
    },
    onError: (error) => handleMutationError(error, 'Cierre duro del período'),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="shield"
        title="Configura una compañía primero"
        description="El Centro de Cierre necesita una compañía y períodos fiscales."
      />
    )
  }

  const periods = (periodsQuery.data ?? []).filter((period) => period.status !== 'CLOSED')
  const checklist = checklistQuery.data
  const columns: TableColumn<ClosingCheck>[] = [
    { key: 'label', header: 'Verificación', render: (row) => row.label },
    {
      key: 'kind',
      header: 'Tipo',
      render: (row) => (
        <Badge tone={row.blocking ? 'info' : 'neutral'}>
          {row.blocking ? 'Bloqueante' : 'Advertencia'}
        </Badge>
      ),
    },
    {
      key: 'passed',
      header: 'Resultado',
      render: (row) => (
        <Badge tone={row.passed ? 'success' : row.blocking ? 'danger' : 'warning'}>
          {row.passed ? 'OK' : row.blocking ? 'BLOQUEA EL CIERRE' : 'Revisar'}
        </Badge>
      ),
    },
    { key: 'detail', header: 'Detalle', render: (row) => row.detail },
  ]

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Finanzas</p>
          <h1 className="nx-dashboard__title">Centro de Cierre contable</h1>
          <p className="nx-field__hint">
            El cierre duro (<code>CLOSED</code>) de un período es irreversible. Antes de permitirlo se
            corre el checklist de pre-cierre. Un manifiesto registra el resultado.
          </p>
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={(value) => {
            setActiveCompanyId(value)
            setPeriodId('')
          }}
        />
      </header>

      <Card title="Período">
        {periodsQuery.isLoading ? (
          <LoadingState label="Cargando períodos…" />
        ) : (
          <Select label="Período fiscal a cerrar" value={periodId} onChange={(event) => setPeriodId(event.target.value)}>
            <option value="">Selecciona un período abierto o en cierre preliminar…</option>
            {periods.map((period) => (
              <option key={period.id} value={period.id}>
                P{String(period.periodNumber).padStart(2, '0')} · {period.startDate} → {period.endDate} · {period.status}
              </option>
            ))}
          </Select>
        )}
      </Card>

      {periodId ? (
        <Card title="Checklist de pre-cierre">
          {checklistQuery.isLoading ? (
            <LoadingState label="Corriendo verificaciones de pre-cierre…" />
          ) : checklistQuery.isError ? (
            <ErrorState description="No se pudo calcular el checklist." onRetry={() => checklistQuery.refetch()} />
          ) : checklist ? (
            <>
              <Badge tone={checklist.canHardClose ? 'success' : 'danger'}>
                {checklist.canHardClose
                  ? 'Listo para cierre duro'
                  : 'Cierre duro bloqueado — resolver verificaciones bloqueantes'}
              </Badge>
              <Table
                columns={columns}
                rows={checklist.checks}
                getRowKey={(row) => row.key}
                emptyMessage="Sin verificaciones."
              />

              <div className="nx-treasury__form">
                <Input
                  label="Motivo (obligatorio para forzar)"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Requerido solo si fuerzas el cierre con verificaciones bloqueantes pendientes"
                />
                <div className="nx-treasury__actions">
                  <Button
                    loading={hardClose.isPending}
                    disabled={!checklist.canHardClose}
                    onClick={() => {
                      if (window.confirm('El cierre duro es irreversible. ¿Continuar?')) {
                        hardClose.mutate(false)
                      }
                    }}
                  >
                    Ejecutar cierre duro
                  </Button>
                  <Button
                    variant="secondary"
                    loading={hardClose.isPending}
                    disabled={checklist.canHardClose || !reason.trim()}
                    onClick={() => {
                      if (
                        window.confirm(
                          'Forzar el cierre con verificaciones bloqueantes pendientes queda registrado en auditoría. ¿Continuar?',
                        )
                      ) {
                        hardClose.mutate(true)
                      }
                    }}
                  >
                    Forzar cierre (con motivo)
                  </Button>
                </div>
              </div>

              {hardClose.isSuccess ? (
                <p className="nx-field__hint" role="status">
                  Período cerrado. Manifiesto generado el{' '}
                  {new Date(hardClose.data.closedAt).toLocaleString('es-HN')}
                  {hardClose.data.forced ? ` · forzado: ${hardClose.data.forceReason}` : ''}.
                </p>
              ) : null}
            </>
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}
