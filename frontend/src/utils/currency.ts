export const DEFAULT_CURRENCY = 'HNL'

const formatterCache = new Map<string, Intl.NumberFormat>()

export function formatMoney(value: number | string, currency = DEFAULT_CURRENCY): string {
  const normalizedCurrency = currency || DEFAULT_CURRENCY
  let formatter = formatterCache.get(normalizedCurrency)
  if (!formatter) {
    formatter = new Intl.NumberFormat('es-HN', {
      style: 'currency',
      currency: normalizedCurrency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
    formatterCache.set(normalizedCurrency, formatter)
  }
  return formatter.format(Number(value))
}

const symbolCache = new Map<string, string>()

function currencySymbol(currency: string): string {
  const key = currency || DEFAULT_CURRENCY
  let symbol = symbolCache.get(key)
  if (!symbol) {
    try {
      const parts = new Intl.NumberFormat('es-HN', {
        style: 'currency',
        currency: key,
        currencyDisplay: 'narrowSymbol',
      }).formatToParts(1)
      symbol = parts.find((part) => part.type === 'currency')?.value ?? key
    } catch {
      symbol = key
    }
    symbolCache.set(key, symbol)
  }
  return symbol
}

/** Abbreviated money for dense contexts — chart axes, sparklines, mobile KPIs.
 * "L 1.2M", "L 250K", "L 980". El valor exacto sigue disponible en tooltips y
 * en las tarjetas (§20/§26). */
export function formatMoneyCompact(value: number | string, currency = DEFAULT_CURRENCY): string {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return formatMoney(0, currency)
  const symbol = currencySymbol(currency)
  const sign = amount < 0 ? '-' : ''
  const abs = Math.abs(amount)
  if (abs >= 1_000_000) return `${sign}${symbol} ${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`
  if (abs >= 1_000) return `${sign}${symbol} ${(abs / 1_000).toFixed(abs >= 100_000 ? 0 : 1)}K`
  return `${sign}${symbol} ${abs.toFixed(0)}`
}
