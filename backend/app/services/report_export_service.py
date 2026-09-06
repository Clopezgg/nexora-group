from __future__ import annotations
"""Exportación XLSX real de reportes financieros (ORDEN MAESTRA DE CIERRE
FINAL DE PRODUCTO §19). Usa openpyxl -- nunca HTML/CSV renombrado. Cada hoja
lleva título, compañía, moneda, fecha de generación y totales; nunca UUID.
"""

import io
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_TITLE_FONT = Font(bold=True, size=14)
_SUBTITLE_FONT = Font(size=10, italic=True, color="555555")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = "1F3B57"
_TOTAL_FONT = Font(bold=True)
_MONEY_FORMAT = "#,##0.00"


def _header_block(sheet, *, title: str, company_name: str, currency_code: str, as_of: date) -> int:
    sheet["A1"] = title
    sheet["A1"].font = _TITLE_FONT
    sheet["A2"] = company_name
    sheet["A2"].font = Font(bold=True, size=11)
    sheet["A3"] = f"Moneda {currency_code} · Al {as_of.isoformat()}"
    sheet["A3"].font = _SUBTITLE_FONT
    sheet["A4"] = f"Generado {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
    sheet["A4"].font = _SUBTITLE_FONT
    return 6  # primera fila libre para encabezados de columna


def _write_columns(sheet, row: int, headers: list[str]) -> None:
    for col, header in enumerate(headers, start=1):
        cell = sheet.cell(row=row, column=col, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _fill(_HEADER_FILL)
        cell.alignment = Alignment(horizontal="center")


def _fill(hex_color: str):
    from openpyxl.styles import PatternFill

    return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")


def _autosize(sheet, n_cols: int) -> None:
    for col in range(1, n_cols + 1):
        letter = get_column_letter(col)
        max_len = max(
            (len(str(cell.value)) for cell in sheet[letter] if cell.value is not None),
            default=10,
        )
        sheet.column_dimensions[letter].width = min(max(max_len + 2, 12), 48)


def trial_balance_xlsx(
    *,
    company_name: str,
    currency_code: str,
    as_of: date,
    rows: list,
    total_debit: Decimal,
    total_credit: Decimal,
) -> bytes:
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Balance de Comprobación"

    header_row = _header_block(
        sheet, title="Balance de Comprobación", company_name=company_name,
        currency_code=currency_code, as_of=as_of,
    )
    _write_columns(sheet, header_row, ["Código", "Cuenta", "Debe", "Haber"])

    r = header_row + 1
    for row in rows:
        sheet.cell(row=r, column=1, value=row.account_code)
        sheet.cell(row=r, column=2, value=row.account_name)
        debit_cell = sheet.cell(row=r, column=3, value=float(row.debit_balance))
        debit_cell.number_format = _MONEY_FORMAT
        credit_cell = sheet.cell(row=r, column=4, value=float(row.credit_balance))
        credit_cell.number_format = _MONEY_FORMAT
        r += 1

    sheet.cell(row=r, column=2, value="TOTAL").font = _TOTAL_FONT
    total_debit_cell = sheet.cell(row=r, column=3, value=float(total_debit))
    total_debit_cell.font = _TOTAL_FONT
    total_debit_cell.number_format = _MONEY_FORMAT
    total_credit_cell = sheet.cell(row=r, column=4, value=float(total_credit))
    total_credit_cell.font = _TOTAL_FONT
    total_credit_cell.number_format = _MONEY_FORMAT

    _autosize(sheet, 4)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
