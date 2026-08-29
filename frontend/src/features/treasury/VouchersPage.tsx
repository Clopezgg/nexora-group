import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Select,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { voucherService } from '../../services/voucherService'
import { statusLabel } from '../../utils/statusLabels'
import './TreasuryPage.css'

export function VouchersPage() {
  const handleMutationError = useMutationError()
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const [documentId, setDocumentId] = useState('')
  const [beneficiary, setBeneficiary] = useState('')
  const [payer, setPayer] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('TRANSFER')
  const [approvedBy, setApprovedBy] = useState('')

  const documentsQuery = useQuery({
    queryKey: ['accounting', 'journal-documents', activeCompanyId],
    queryFn: () => voucherService.listDocuments(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const download = useMutation({
    mutationFn: () => voucherService.download(documentId, {
      beneficiary: beneficiary.trim(),
      payer: payer.trim(),
      paymentMethod,
      approvedBy: approvedBy.trim() || undefined,
    }),
    onSuccess: (blob) => {
      const document = (documentsQuery.data ?? []).find((row) => row.id === documentId)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `NEXORA-${document?.documentNumber ?? 'comprobante'}.pdf`
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    },
    onError: (error) => handleMutationError(error, 'Generar comprobante'),
  })

  if (isLoading) return <LoadingState label="Cargando comprobantes…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="receipt" title="No hay compañía configurada" description="Configura una compañía antes de generar comprobantes." />
  }

  const documents = documentsQuery.data ?? []
  const selected = documents.find((row) => row.id === documentId)

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <div>
          <p className="nx-page__eyebrow">Tesorería</p>
          <h1 className="nx-dashboard__title">Comprobantes / Vouchers</h1>
          <p className="nx-field__hint">Genera el PDF oficial desde un documento contable real. El identificador se resuelve por selector; no se capturan UUID manualmente.</p>
        </div>
        <Select value={activeCompanyId ?? ''} onChange={(event) => { setActiveCompanyId(event.target.value); setDocumentId('') }} aria-label="Compañía">
          {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
        </Select>
      </header>

      <Card title="Documento contable">
        {documentsQuery.isLoading ? <LoadingState label="Cargando documentos…" /> : documentsQuery.isError ? (
          <ErrorState description="No se pudieron cargar los documentos contables." onRetry={() => documentsQuery.refetch()} />
        ) : (
          <div className="nx-treasury__form">
            <Select label="Asiento / documento" value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
              <option value="">Selecciona un documento…</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.documentNumber} — {document.description ?? document.scope} — {statusLabel(document.status)}
                </option>
              ))}
            </Select>
            {selected ? (
              <div className="nx-treasury__actions">
                <Badge>{statusLabel(selected.status)}</Badge>
                <span>{selected.documentNumber}</span>
                <span>{selected.currencyCode}</span>
              </div>
            ) : null}
          </div>
        )}
      </Card>

      <Card title="Datos impresos en el comprobante">
        <div className="nx-treasury__form">
          <Input label="Beneficiario" value={beneficiary} onChange={(event) => setBeneficiary(event.target.value)} required />
          <Input label="Pagador / emisor" value={payer} onChange={(event) => setPayer(event.target.value)} required />
          <Select label="Método de pago" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}>
            <option value="TRANSFER">Transferencia</option>
            <option value="CHECK">Cheque</option>
            <option value="CASH">Efectivo</option>
            <option value="REMITTANCE">Remesa</option>
            <option value="OTHER">Otro</option>
          </Select>
          <Input label="Aprobado por (opcional)" value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} />
          <Button
            loading={download.isPending}
            disabled={!documentId || !beneficiary.trim() || !payer.trim() || !paymentMethod}
            onClick={() => download.mutate()}
          >
            Generar PDF
          </Button>
        </div>
      </Card>
    </div>
  )
}