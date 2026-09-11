"""Formateo de dinero centralizado para artefactos que genera el backend
(PDF de comprobantes, manifiestos de cierre, exportes). El frontend tiene su
propio `formatMoney` en `frontend/src/utils/currency.ts`; ambos deben
producir la misma convención: símbolo/código + miles con coma + 2 decimales,
nunca un número desnudo como `150000`.
"""

from decimal import ROUND_HALF_UP, Decimal

# Símbolo preferido por moneda. Para monedas sin símbolo local establecido se
# usa el código ISO como prefijo (p. ej. "PAB 1,000.00").
_CURRENCY_SYMBOL = {
    "HNL": "L",
    "USD": "$",
    "EUR": "€",
}


def _quantize(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(value: Decimal | int | float | str, currency_code: str) -> str:
    """`format_money("150000", "HNL")` -> `"L 150,000.00"`.

    La moneda es obligatoria: los artefactos financieros del backend nunca
    deben inventar HNL (ni ninguna otra divisa) cuando el dominio no entregó
    una autoridad monetaria explícita.
    """
    currency = currency_code.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("Se requiere un código de moneda ISO explícito")

    amount = _quantize(value)
    negative = amount < 0
    digits = f"{abs(amount):,.2f}"
    symbol = _CURRENCY_SYMBOL.get(currency, currency)
    prefix = "-" if negative else ""
    return f"{prefix}{symbol} {digits}"
