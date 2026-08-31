import io
import uuid
from decimal import Decimal

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.money import format_money
from app.models.accounting import AccountingDocument, JournalLine
from app.models.chart_of_accounts import Account
from app.models.company import Company
from app.models.project import Project

"""Comprobantes / vouchers (orden maestra §71, §120-125). PDF vectorial/textual
real generado con reportlab (nunca captura de pantalla). Cubre remesas y
pagos -- cualquier AccountingDocument con document_type_code en REM/PAY/TRF/REC
puede generar su comprobante a partir de los mismos datos que ya quedaron
posteados, así que el comprobante nunca puede divergir del asiento real.

Reglas de presentación (orden maestra Phase 2):
- Nunca se imprimen UUID: las cuentas salen como `código — nombre`, el
  proyecto como su nombre, el documento por su `document_number`.
- El tipo de cambio solo se imprime cuando es una conversión real
  (`fx_rate != 1` y la moneda del documento difiere de la funcional de la
  compañía). HNL->HNL nunca muestra "1.000000".
- Todos los importes pasan por `app.core.money.format_money` -> `L 1,250.00`.
- Bloque de firmas: preparado por / aprobado por / recibí conforme.
"""


def _account_label(account: Account | None, account_id: uuid.UUID) -> str:
    if account is None:
        return "Cuenta no encontrada"
    return f"{account.code} - {account.name}"


def generate_voucher_pdf(
    db: Session,
    *,
    accounting_document_id: uuid.UUID,
    prepared_by: str,
    approved_by: str | None,
    beneficiary: str,
    payer: str,
    payment_method: str,
) -> bytes:
    document = db.get(AccountingDocument, accounting_document_id)
    if document is None:
        raise ValueError(f"AccountingDocument {accounting_document_id} no existe")

    company = db.get(Company, document.company_id)
    project = db.get(Project, document.project_id) if document.project_id else None

    lines = list(
        db.query(JournalLine).filter(JournalLine.accounting_document_id == document.id)
    )
    account_ids = {line.account_id for line in lines}
    accounts: dict[uuid.UUID, Account] = {}
    if account_ids:
        for account in db.query(Account).filter(Account.id.in_(account_ids)):
            accounts[account.id] = account

    total = sum((line.debit_amount for line in lines), Decimal("0"))
    currency = document.currency_code
    functional_currency = (company.functional_currency_code if company else None) or currency
    is_fx_conversion = (
        Decimal(str(document.fx_rate)) != Decimal("1")
        and currency != functional_currency
    )

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    # Sin compresión de página: un comprobante es un artefacto de auditoría y
    # debe poder inspeccionarse/extraerse su texto sin herramientas externas.
    pdf.setPageCompression(0)
    width, _height = letter

    # -- Encabezado / identidad NEXORA -------------------------------------
    pdf.setFillColorRGB(0.09, 0.13, 0.24)
    pdf.rect(0, 25.6 * cm, width, 3.1 * cm, stroke=0, fill=1)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(2 * cm, 27.4 * cm, (company.name if company else "NEXORA GROUP"))
    pdf.setFont("Helvetica", 9)
    if company and company.legal_name:
        pdf.drawString(2 * cm, 26.9 * cm, company.legal_name)
    pdf.drawString(2 * cm, 26.4 * cm, "Comprobante de pago / egreso")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(width - 2 * cm, 27.4 * cm, f"No. {document.document_number}")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(
        width - 2 * cm,
        26.9 * cm,
        document.posted_at.strftime("%d/%m/%Y") if document.posted_at else "Sin postear",
    )
    pdf.setFillColorRGB(0, 0, 0)

    # -- Cuerpo -----------------------------------------------------------
    y = 24.4 * cm
    pdf.setFont("Helvetica", 10)
    fields = [
        ("Tipo de operación", document.document_type_code),
        ("Pagador", payer or (company.name if company else "")),
        ("Beneficiario", beneficiary),
        ("Concepto", document.description or "—"),
        ("Monto", format_money(total, currency)),
        ("Método de pago", payment_method),
        ("Ámbito (scope)", document.scope),
        ("Proyecto", project.name if project else "No aplica (operación central/general)"),
    ]
    if is_fx_conversion:
        fields.append(
            ("Tipo de cambio", f"1 {currency} = {document.fx_rate} {functional_currency}")
        )
    for label, value in fields:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(2 * cm, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(7 * cm, y, str(value))
        y -= 0.62 * cm

    # -- Asiento contable ------------------------------------------------
    y -= 0.5 * cm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(2 * cm, y, "Asiento contable")
    y -= 0.5 * cm
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(2 * cm, y, "Cuenta")
    pdf.drawRightString(15 * cm, y, "Débito")
    pdf.drawRightString(18.5 * cm, y, "Crédito")
    y -= 0.12 * cm
    pdf.line(2 * cm, y, 18.5 * cm, y)
    y -= 0.4 * cm
    pdf.setFont("Helvetica", 9)
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for line in lines:
        total_debit += line.debit_amount
        total_credit += line.credit_amount
        pdf.drawString(2 * cm, y, _account_label(accounts.get(line.account_id), line.account_id))
        if line.debit_amount:
            pdf.drawRightString(15 * cm, y, format_money(line.debit_amount, currency))
        if line.credit_amount:
            pdf.drawRightString(18.5 * cm, y, format_money(line.credit_amount, currency))
        y -= 0.5 * cm
    y -= 0.05 * cm
    pdf.line(2 * cm, y, 18.5 * cm, y)
    y -= 0.4 * cm
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(2 * cm, y, "Totales")
    pdf.drawRightString(15 * cm, y, format_money(total_debit, currency))
    pdf.drawRightString(18.5 * cm, y, format_money(total_credit, currency))

    # -- Firmas ---------------------------------------------------------
    sign_y = 4.5 * cm
    pdf.setFont("Helvetica", 9)
    for idx, (label, name) in enumerate(
        [
            ("Preparado por", prepared_by),
            ("Aprobado por", approved_by or "Pendiente de aprobación"),
            ("Recibí conforme", beneficiary),
        ]
    ):
        x = (2 + idx * 6) * cm
        pdf.line(x, sign_y, x + 5 * cm, sign_y)
        pdf.drawString(x, sign_y - 0.5 * cm, label)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x, sign_y - 1.0 * cm, name[:40])
        pdf.setFont("Helvetica", 9)

    pdf.setFont("Helvetica-Oblique", 7)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawString(
        2 * cm,
        1.6 * cm,
        "Documento generado por NEXORA GROUP a partir del asiento contable posteado. "
        "TOTAL DÉBITO = TOTAL CRÉDITO (doble partida).",
    )

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
