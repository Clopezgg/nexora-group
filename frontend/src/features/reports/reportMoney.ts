import { useActiveCompany } from '../../hooks/useActiveCompany'
import { formatMoney } from '../../utils/currency'

/** Formateo de dinero para los reportes financieros, siempre en la moneda
 * funcional de la compañía activa (§26/§27). Nunca renderizar el número
 * crudo del backend. */
export function useReportCurrency() {
  const { activeCompany } = useActiveCompany()
  const currency = activeCompany?.functionalCurrencyCode ?? 'HNL'
  const fmt = (value: string | number | null | undefined): string =>
    value === null || value === undefined || value === '' ? '—' : formatMoney(Number(value), currency)
  return { currency, fmt }
}
