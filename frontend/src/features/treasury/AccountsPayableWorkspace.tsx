import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, EmptyState, LoadingState, Select } from '../../design-system'
import { masterDataService } from '../../services/masterDataService'
import { apService, type SupplierInvoice } from '../../services/apArService'
import { treasuryService } from '../../services/treasuryService'
import { formatMoney } from '../../utils/currency'
import { AccountsPayablePage } from './AccountsPayablePage'
import { PaymentPlanModal } from './PaymentPlanModal'
import { SupplierPaymentHistoryModal } from './SupplierPaymentHistoryModal'

export function AccountsPayableWorkspace() {
  const queryClient = useQueryClient()
  const [companyId, setCompanyId] = useState('')
  const [invoiceId, setInvoiceId] = useState('')
  const [historyInvoice, setHistoryInvoice] = useState<SupplierInvoice | null>(null)
  const [planInvoice, setPlanInvoice] = useState<SupplierInvoice | null>(null)

  const companiesQuery = useQuery({
    queryKey: ['master-data', 'companies'],
    queryFn: masterDataService.listCompanies,
  })
  const companies = companiesQuery.data ?? []
  const activeCompanyId = companyId || companies[0]?.id || ''

  const invoicesQuery = useQuery({
    queryKey: ['ap', 'supplier-invoices', activeCompanyId],
    queryFn: () => apService.listInvoices(activeCompanyId),
    enabled: Boolean(activeCompanyId),
  })
  const treasuryQuery = useQuery({
    queryKey: ['treasury', 'accounts', activeCompanyId],
    queryFn: () => treasuryService.listAccounts(activeCompanyId),
    enabled: Boolean(activeCompanyId),
  })
  const invoices = invoicesQuery.data ?? []
  const selectedInvoice = invoices.find((invoice) => invoice.id === invoiceId) ?? null

  if (companiesQuery.isLoading) return <LoadingState label="Cargando cuentas por pagar…" />

  return (
    <div className="nx-treasury">
      <AccountsPayablePage />

      <Card title="Historial formal de pagos y reversals">
        {companies.length === 0 ? (
          <EmptyState
            icon="card"
            title="No hay compañía configurada"
            description="Configura una compañía antes de consultar pagos."
          />
        ) : (
          <div className="nx-treasury__form">
            <p className="nx-field__hint">
              Los pagos contabilizados nunca se eliminan. Un reversal crea un asiento inverso y conserva motivo, usuario, fecha y documento origen.
            </p>
            <Select
              label="Compañía"
              value={activeCompanyId}
              onChange={(event) => {
                setCompanyId(event.target.value)
                setInvoiceId('')
              }}
            >
              {companies.map((company) => (
                <option key={company.id} value={company.id}>{company.name}</option>
              ))}
            </Select>
            <Select
              label="Factura de proveedor"
              value={invoiceId}
              onChange={(event) => setInvoiceId(event.target.value)}
              disabled={invoicesQuery.isLoading}
            >
              <option value="">Selecciona una factura…</option>
              {invoices.map((invoice) => (
                <option key={invoice.id} value={invoice.id}>
                  {invoice.invoiceNumber} — {formatMoney(invoice.amount, invoice.currencyCode)} — {invoice.status}
                </option>
              ))}
            </Select>
            <div className="nx-treasury__actions">
              <Button
                variant="secondary"
                disabled={!selectedInvoice}
                onClick={() => selectedInvoice && setHistoryInvoice(selectedInvoice)}
              >
                Ver pagos y reversals
              </Button>
              <Button
                variant="secondary"
                disabled={!selectedInvoice}
                onClick={() => selectedInvoice && setPlanInvoice(selectedInvoice)}
              >
                Plan de pago / cuotas
              </Button>
            </div>
          </div>
        )}
      </Card>

      {planInvoice ? (
        <PaymentPlanModal
          invoice={planInvoice}
          onClose={() => setPlanInvoice(null)}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices', activeCompanyId] })
            queryClient.invalidateQueries({ queryKey: ['ap', 'payment-plan', planInvoice.id] })
          }}
        />
      ) : null}

      {historyInvoice ? (
        <SupplierPaymentHistoryModal
          invoice={historyInvoice}
          treasuryAccounts={treasuryQuery.data ?? []}
          onClose={() => setHistoryInvoice(null)}
          onReversed={() => {
            queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices', activeCompanyId] })
            queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-payments', historyInvoice.id] })
            queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts', activeCompanyId] })
          }}
        />
      ) : null}
    </div>
  )
}
