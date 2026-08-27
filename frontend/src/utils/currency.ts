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
