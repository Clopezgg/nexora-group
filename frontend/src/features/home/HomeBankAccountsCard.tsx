import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Card, EmptyState, Icon, LoadingState } from '../../design-system'
import { treasuryService } from '../../services/treasuryService'
import { formatMoney } from '../../utils/currency'

function mask(reference: string | null): string {
  if (!reference) return 'sin número'
  const trimmed = reference.trim()
  return trimmed.length <= 4 ? `••••${trimmed}` : `••••${trimmed.slice(-4)}`
}

/** Cuentas bancarias — saldos en libros (§16). Usa `TreasuryAccount` real;
 * nunca imprime el número completo ni datos falsos. */
export function HomeBankAccountsCard({ companyId }: { companyId: string }) {
  const query = useQuery({
    queryKey: ['treasury', 'accounts', companyId],
    queryFn: () => treasuryService.listAccounts(companyId),
    enabled: Boolean(companyId),
  })

  const accounts = (Array.isArray(query.data) ? query.data : []).filter(
    (account) => account.kind === 'BANK',
  )

  return (
    <Card title="Cuentas bancarias · saldos en libros">
      {query.isLoading ? (
        <LoadingState label="Cargando cuentas…" />
      ) : accounts.length === 0 ? (
        <EmptyState icon="bank" title="Sin cuentas bancarias registradas" />
      ) : (
        <ul className="nx-home__banks">
          {accounts.map((account) => (
            <li key={account.id}>
              <Link to="/finanzas/tesoreria" className="nx-home__bank">
                <span className="nx-home__bank-icon" aria-hidden="true">
                  <Icon name="bank" />
                </span>
                <span className="nx-home__bank-id">
                  <span className="nx-home__bank-name">{account.institution ?? account.name}</span>
                  <span className="nx-home__bank-ref">
                    {mask(account.accountReference)} · {account.currencyCode}
                  </span>
                </span>
                <span className="nx-home__bank-balance">
                  {formatMoney(account.balance, account.currencyCode)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
