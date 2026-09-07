export const DEFAULT_CURRENCY = 'HNL'

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

/**
 * Formatea dinero sin convertir strings Decimal del backend a IEEE-754.
 * La representación financiera autoritativa viaja como string; aquí se
 * normaliza a centavos con BigInt y redondeo decimal exacto. Los `number`
 * siguen aceptándose para inputs/UI no autoritativos por compatibilidad.
 */
export function formatMoney(value: number | string, currency = DEFAULT_CURRENCY): string {
  const raw = typeof value === 'number'
    ? (Number.isFinite(value) ? value.toFixed(2) : '0')
    : String(value).trim()
  const match = raw.match(/^([+-]?)(\d+)(?:\.(\d+))?$/)
  if (!match) return `${currencySymbol(currency)} 0.00`

  const negative = match[1] === '-'
  const integer = BigInt(match[2])
  const fraction = (match[3] ?? '').padEnd(3, '0')
  let cents = integer * 100n + BigInt(fraction.slice(0, 2) || '0')
  if (Number(fraction[2] ?? '0') >= 5) cents += 1n

  const whole = cents / 100n
  const decimal = String(cents % 100n).padStart(2, '0')
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const sign = negative && cents !== 0n ? '-' : ''
  return `${sign}${currencySymbol(currency || DEFAULT_CURRENCY)} ${grouped}.${decimal}`
}

/** Abbreviated money is deliberately presentational (axes/sparklines), never
 * used as an accounting value or request payload. */
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
