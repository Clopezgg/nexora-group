import io
import uuid
from decimal import Decimal

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument, JournalLine

"""Comprobantes / vouchers (orden maestra §71). PDF vectorial/textual real
generado con reportlab (nunca captura de pantalla). Cubre remesas y pagos
-- cualquier AccountingDocument con document_type_code en REM/PAY/TRF/REC
puede generar su comprobante a partir de los mismos datos que ya quedaron
posteados, así que el comprobante nunca puede divergir del asiento real."""


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

    lines = list(
        db.query(JournalLine).filter(JournalLine.accounting_document_id == document.id)
    )
    total = sum((line.debit_amount for line in lines), Decimal("0"))

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, _height = letter

    y = 27 * cm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, y, "NEXORA GROUP")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(2 * cm, y - 0.5 * cm, "Gestión Empresarial y Control de Construcción")

    y -= 1.5 * cm
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(2 * cm, y, f"Comprobante {document.document_number}")

    y -= 1 * cm
    pdf.setFont("Helvetica", 10)
    fields = [
        ("Tipo de operación", document.document_type_code),
        ("Fecha", document.posted_at.strftime("%Y-%m-%d") if document.posted_at else "-"),
        ("Pagador", payer),
        ("Beneficiario", beneficiary),
        ("Concepto", document.description or ""),
        ("Monto", f"{document.currency_code} {total:,.2f}"),
        ("Tipo de cambio", str(document.fx_rate)),
        ("Método de pago", payment_method),
        ("Ámbito (scope)", document.scope),
        ("Centro de costo / Proyecto", str(document.project_id) if document.project_id else "N/A"),
        ("Preparado por", prepared_by),
        ("Aprobado por", approved_by or "Pendiente"),
    ]
    for label, value in fields:
        pdf.drawString(2 * cm, y, f"{label}:")
        pdf.drawString(8 * cm, y, str(value))
        y -= 0.6 * cm

    y -= 0.5 * cm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(2 * cm, y, "Cuenta")
    pdf.drawString(10 * cm, y, "Débito")
    pdf.drawString(14 * cm, y, "Crédito")
    y -= 0.4 * cm
    pdf.setFont("Helvetica", 9)
    for line in lines:
        pdf.drawString(2 * cm, y, str(line.account_id))
        pdf.drawRightString(12.5 * cm, y, f"{line.debit_amount:,.2f}")
        pdf.drawRightString(16.5 * cm, y, f"{line.credit_amount:,.2f}")
        y -= 0.5 * cm

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
