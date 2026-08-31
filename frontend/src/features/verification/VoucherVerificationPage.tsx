import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { apiFetch } from '../../services/httpClient'
import { formatMoney } from '../../utils/currency'
import './VoucherVerificationPage.css'

interface VerificationResult {
  verified: boolean
  documentNumber: string
  company: string
  beneficiary: string
  issuedOn: string
  amount: string
  currency: string
  status: string
  verificationCode: string
}

const STATUS_LABEL: Record<string, string> = {
  posted: 'Contabilizado',
  draft: 'Borrador',
  reversed: 'Reversado',
}

/** Página pública de verificación de comprobantes (§42). NEXORA Horizon Light.
 * Sin datos bancarios, evidencia ni identificadores técnicos. */
export function VoucherVerificationPage() {
  const { token } = useParams<{ token: string }>()

  const query = useQuery({
    queryKey: ['voucher-verification', token],
    queryFn: () =>
      apiFetch<VerificationResult>(`/verificar/comprobante/${encodeURIComponent(token ?? '')}`),
    enabled: Boolean(token),
    retry: false,
  })

  return (
    <div className="nx-verify">
      <main className="nx-verify__card">
        <div className="nx-verify__brand">NEXORA GROUP</div>

        {query.isLoading ? (
          <p className="nx-verify__muted">Verificando comprobante…</p>
        ) : query.isError || !query.data?.verified ? (
          <>
            <h1 className="nx-verify__title nx-verify__title--bad">Comprobante no verificado</h1>
            <p className="nx-verify__muted">
              No encontramos un comprobante con ese código de verificación. Solicita el documento
              original a NEXORA GROUP.
            </p>
          </>
        ) : (
          <>
            <h1 className="nx-verify__title nx-verify__title--ok">✓ Comprobante válido</h1>
            <dl className="nx-verify__grid">
              <div>
                <dt>Empresa</dt>
                <dd>{query.data.company}</dd>
              </div>
              <div>
                <dt>Número</dt>
                <dd>{query.data.documentNumber}</dd>
              </div>
              <div>
                <dt>Beneficiario</dt>
                <dd>{query.data.beneficiary}</dd>
              </div>
              <div>
                <dt>Fecha de emisión</dt>
                <dd>{query.data.issuedOn}</dd>
              </div>
              <div>
                <dt>Monto</dt>
                <dd>{formatMoney(query.data.amount, query.data.currency)}</dd>
              </div>
              <div>
                <dt>Estado</dt>
                <dd>{STATUS_LABEL[query.data.status.toLowerCase()] ?? query.data.status}</dd>
              </div>
              <div>
                <dt>Código de verificación</dt>
                <dd>{query.data.verificationCode}</dd>
              </div>
            </dl>
          </>
        )}
        <p className="nx-verify__foot">Verificación pública emitida por NEXORA GROUP.</p>
      </main>
    </div>
  )
}
