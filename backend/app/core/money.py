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


def format_money(value: Decimal | int | float | str, currency_code: str = "HNL") -> str:
    """`format_money("150000", "HNL")` -> `"L 150,000.00"`.

    Negativos con signo menos delante del símbolo: `"-L 1,250.00"`.
    """
    amount = _quantize(value)
    negative = amount < 0
    digits = f"{abs(amount):,.2f}"
    symbol = _CURRENCY_SYMBOL.get(currency_code.upper(), currency_code.upper())
    prefix = "-" if negative else ""
    return f"{prefix}{symbol} {digits}"
