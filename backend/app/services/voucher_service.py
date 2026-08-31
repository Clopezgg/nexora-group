"""Comprobante de pago NEXORA — documento empresarial (orden maestra
correctiva §26-§53).

Generado con reportlab **Platypus** (Table/Paragraph/Image, no coordenadas
absolutas): soporta nombres largos, acentos/ñ, conceptos largos, planes de
pago, evidencia embebida y multipágina sin desbordar la hoja.

Fuente: familia Helvetica (Type-1 estándar de reportlab, WinAnsi cubre el
español; no es un archivo de fuente propietario). Los importes pasan por
`app.core.money.format_money`. Nunca se imprimen UUID, blob keys ni URLs
privadas. El QR codifica `<FRONTEND_URL>/verificar/comprobante/<token>`.
"""

import hashlib
import io
import uuid
from datetime import date
from decimal import Decimal

from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.money import format_money
from app.models.accounting import AccountingDocument, JournalLine
from app.models.ap import (
    SupplierInvoice,
    SupplierInvoicePaymentPlanItem,
    SupplierPayment,
)
from app.models.chart_of_accounts import Account
from app.models.company import Company
from app.models.evidence import Evidence
from app.models.project import Project
from app.services import evidence_service, voucher_verification_service

_NAVY = colors.HexColor("#0b274a")
_ACCENT = colors.HexColor("#1769d2")
_MUTED = colors.HexColor("#4f6176")
_LINE = colors.HexColor("#dce5ef")

_ACCOUNTING_DOCUMENT_EVIDENCE_TYPES = {"ACCOUNTING_DOCUMENT", "PAYMENT_DOCUMENT", "VOUCHER"}
_EMBEDDABLE_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}

_STATUS_LABEL = {
    "posted": "Contabilizado",
    "draft": "Borrador",
    "reversed": "Reversado",
    "reversal": "Reverso",
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "nx-body", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=12
    )
    return {
        "title": ParagraphStyle(
            "nx-title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=16, leading=19, textColor=_NAVY, spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "nx-h2", parent=body, fontName="Helvetica-Bold", fontSize=10.5,
            leading=13, textColor=_NAVY, spaceBefore=10, spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "nx-label", parent=body, fontName="Helvetica-Bold", fontSize=8,
            textColor=_MUTED, leading=10,
        ),
        "body": body,
        "value": ParagraphStyle("nx-value", parent=body, fontSize=9.5, leading=12),
        "small": ParagraphStyle(
            "nx-small", parent=body, fontSize=7.5, leading=10, textColor=_MUTED
        ),
        "total": ParagraphStyle(
            "nx-total", parent=body, fontName="Helvetica-Bold", fontSize=13,
            leading=16, textColor=_NAVY,
        ),
    }


def _account_label(account: Account | None) -> str:
    if account is None:
        return "Cuenta no encontrada"
    return f"{account.code} - {account.name}"


def _mask_reference(reference: str | None) -> str | None:
    if not reference:
        return None
    tail = reference[-4:]
    return f"{'*' * max(len(reference) - 4, 0)}{tail}"


def approval_verification_code(
    *, document_number: str, approved_by: str | None, issued_on: date
) -> str:
    """Código legible de integridad. NO es una firma criptográfica con clave;
    permite re-derivar y contrastar (documento, aprobador, emisión)."""
    raw = f"{document_number}|{(approved_by or '').strip().upper()}|{issued_on.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def _qr_flowable(url: str, size: float = 2.6 * cm) -> Drawing:
    widget = qr.QrCodeWidget(url)
    bounds = widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    drawing = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    drawing.add(widget)
    return drawing


def _resolve_payment_schedule(
    db: Session, document: AccountingDocument
) -> tuple[SupplierInvoice, list[SupplierInvoicePaymentPlanItem]] | None:
    """Best-effort: si el comprobante corresponde a un pago/acumulación de una
    factura de proveedor con plan de cuotas, se devuelve el plan real."""
    invoice: SupplierInvoice | None = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.accrual_document_id == document.id)
    ).scalar_one_or_none()
    if invoice is None:
        payment = db.execute(
            select(SupplierPayment).where(
                SupplierPayment.accounting_document_id == document.id
            )
        ).scalar_one_or_none()
        if payment is not None:
            invoice = db.get(SupplierInvoice, payment.supplier_invoice_id)
    if invoice is None:
        return None
    plan = list(
        db.execute(
            select(SupplierInvoicePaymentPlanItem)
            .where(SupplierInvoicePaymentPlanItem.supplier_invoice_id == invoice.id)
            .order_by(SupplierInvoicePaymentPlanItem.sequence)
        ).scalars()
    )
    if not plan:
        return None
    return invoice, plan


def _load_payment_evidence(db: Session, document: AccountingDocument) -> Evidence | None:
    rows = evidence_service.list_evidence(
        db,
        company_id=document.company_id,
        entity_type="ACCOUNTING_DOCUMENT",
        entity_id=document.id,
    )
    rows = [
        row
        for row in rows
        if (row.entity_type or "").upper() in _ACCOUNTING_DOCUMENT_EVIDENCE_TYPES
    ]
    if not rows:
        return None
    proofs = [r for r in rows if (r.category or "").upper() == "PAYMENT_PROOF"]
    candidates = proofs or rows
    images = [r for r in candidates if (r.mime_type or "").lower() in _EMBEDDABLE_IMAGE_MIME]
    return (images or candidates)[0]


def _evidence_image(evidence: Evidence, *, max_width: float, max_height: float) -> Image | None:
    if (evidence.mime_type or "").lower() not in _EMBEDDABLE_IMAGE_MIME:
        return None
    try:
        raw = b"".join(evidence_service.download_evidence(evidence))
    except Exception:  # pragma: no cover - depende de storage real
        return None
    try:
        from PIL import Image as PILImage

        with PILImage.open(io.BytesIO(raw)) as probe:
            iw, ih = probe.size
        if iw <= 0 or ih <= 0:
            return None
        scale = min(max_width / iw, max_height / ih, 1.0)
        return Image(io.BytesIO(raw), width=iw * scale, height=ih * scale)
    except Exception:  # pragma: no cover
        return None


def _kv_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [Paragraph(label, styles["label"]), Paragraph(value or "-", styles["value"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=[5 * cm, 11.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, _LINE),
            ]
        )
    )
    return table


def generate_voucher_pdf(
    db: Session,
    *,
    accounting_document_id: uuid.UUID,
    prepared_by: str,
    approved_by: str | None,
    beneficiary: str,
    payer: str,
    payment_method: str,
    bank_label: str | None = None,
    bank_reference: str | None = None,
    issued_on: date | None = None,
) -> bytes:
    document = db.get(AccountingDocument, accounting_document_id)
    if document is None:
        raise ValueError(f"AccountingDocument {accounting_document_id} no existe")

    company = db.get(Company, document.company_id)
    project = db.get(Project, document.project_id) if document.project_id else None
    settings = get_settings()
    styles = _styles()

    lines = list(
        db.query(JournalLine).filter(JournalLine.accounting_document_id == document.id)
    )
    account_ids = {line.account_id for line in lines}
    accounts: dict[uuid.UUID, Account] = {}
    if account_ids:
        for account in db.query(Account).filter(Account.id.in_(account_ids)):
            accounts[account.id] = account

    issued_on = issued_on or date.today()
    total = sum((line.debit_amount for line in lines), Decimal("0"))
    currency = document.currency_code
    functional_currency = (company.functional_currency_code if company else None) or currency
    is_fx_conversion = (
        Decimal(str(document.fx_rate)) != Decimal("1") and currency != functional_currency
    )

    verification_code = approval_verification_code(
        document_number=document.document_number,
        approved_by=approved_by,
        issued_on=issued_on,
    )
    company_name = company.name if company else "NEXORA GROUP"
    token = voucher_verification_service.get_or_create_token(
        db,
        accounting_document_id=document.id,
        document_number=document.document_number,
        company_name=company_name,
        beneficiary=beneficiary,
        approved_by=approved_by,
        issued_on=issued_on,
        amount=total,
        currency_code=currency,
        document_status=document.status,
        verification_code=verification_code,
    )
    verify_url = f"{settings.frontend_url.rstrip('/')}/verificar/comprobante/{token}"

    status_label = _STATUS_LABEL.get((document.status or "").lower(), document.status or "—")
    posted = document.posted_at.strftime("%d/%m/%Y") if document.posted_at else "Sin postear"

    story: list = []

    # -- Encabezado -----------------------------------------------------
    header = Table(
        [
            [
                [
                    Paragraph("NEXORA GROUP", styles["title"]),
                    Paragraph("COMPROBANTE DE PAGO", styles["h2"]),
                    Paragraph(
                        f"N.º {document.document_number}<br/>"
                        f"Fecha {issued_on.strftime('%d/%m/%Y')} · Contabilizado {posted}<br/>"
                        f"Estado {status_label}",
                        styles["small"],
                    ),
                ],
                _qr_flowable(verify_url),
            ]
        ],
        colWidths=[13 * cm, 3.5 * cm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.4, _NAVY),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(header)
    story.append(Paragraph("Escanea el QR para verificar este comprobante.", styles["small"]))
    story.append(Spacer(1, 10))

    # -- Emisor / Beneficiario ---------------------------------------
    emisor = [
        Paragraph("EMISOR", styles["label"]),
        Paragraph(company_name, styles["value"]),
        Paragraph(
            company.legal_name or "Gestión empresarial y control de construcción",
            styles["small"],
        ),
        Paragraph(f"Pagador: {payer}", styles["small"]),
    ]
    benef = [
        Paragraph("BENEFICIARIO", styles["label"]),
        Paragraph(beneficiary, styles["value"]),
    ]
    two_col = Table([[emisor, benef]], colWidths=[8.25 * cm, 8.25 * cm])
    two_col.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(two_col)

    # -- Información del pago ---------------------------------------
    story.append(Paragraph("Información del pago", styles["h2"]))
    scope_label = (
        project.name
        if project
        else ("Operación general" if document.scope in {"CENTRAL", "GENERAL"} else document.scope)
    )
    info_rows: list[tuple[str, str]] = [
        ("Concepto", document.description or "—"),
        ("Ámbito", scope_label if project is None else f"Proyecto · {project.name}"),
        ("Método de pago", payment_method),
    ]
    if bank_label:
        masked = _mask_reference(bank_reference)
        info_rows.append(("Banco / cuenta", f"{bank_label}{f' · {masked}' if masked else ''}"))
    if is_fx_conversion:
        info_rows.append(
            ("Tipo de cambio", f"1 {currency} = {document.fx_rate} {functional_currency}")
        )
    story.append(_kv_table(info_rows, styles))
    story.append(Spacer(1, 6))
    story.append(Paragraph("TOTAL PAGADO", styles["label"]))
    story.append(Paragraph(format_money(total, currency), styles["total"]))

    # -- Pagos / vencimientos (si aplica) ------------------------
    schedule = _resolve_payment_schedule(db, document)
    if schedule is not None:
        invoice, plan = schedule
        story.append(Paragraph("Pagos / vencimientos", styles["h2"]))
        header_row = ["Período", "Importe", "Estado"]
        rows = [header_row]
        invoice_total = invoice.amount + invoice.tax_amount
        for item in plan:
            rows.append(
                [
                    item.due_date.strftime("%b %Y"),
                    format_money(item.amount, invoice.currency_code),
                    item.note or "Programada",
                ]
            )
        plan_table = Table(rows, colWidths=[5 * cm, 5 * cm, 6.5 * cm])
        plan_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, _LINE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(plan_table)
        story.append(Spacer(1, 4))
        story.append(
            Paragraph(
                f"Total acordado {format_money(invoice_total, invoice.currency_code)} · "
                f"Pagado acumulado {format_money(invoice.amount_paid, invoice.currency_code)} · "
                f"Saldo pendiente "
                f"{format_money(invoice_total - invoice.amount_paid, invoice.currency_code)}",
                styles["small"],
            )
        )

    # -- Asiento contable -----------------------------------------
    story.append(Paragraph("Asiento contable", styles["h2"]))
    acc_rows = [["Código / Cuenta", "Débito", "Crédito"]]
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for line in lines:
        total_debit += line.debit_amount
        total_credit += line.credit_amount
        acc_rows.append(
            [
                _account_label(accounts.get(line.account_id)),
                format_money(line.debit_amount, currency) if line.debit_amount else "",
                format_money(line.credit_amount, currency) if line.credit_amount else "",
            ]
        )
    acc_rows.append(
        ["Totales", format_money(total_debit, currency), format_money(total_credit, currency)]
    )
    acc_table = Table(acc_rows, colWidths=[9.5 * cm, 3.5 * cm, 3.5 * cm])
    acc_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, _LINE),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, _LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(acc_table)
    story.append(
        Paragraph(
            "Doble partida: TOTAL DÉBITO = TOTAL CRÉDITO. El comprobante no puede "
            "alterar el asiento contabilizado.",
            styles["small"],
        )
    )

    # -- Evidencia (página 1) -----------------------------------
    evidence = _load_payment_evidence(db, document)
    story.append(Paragraph("Evidencia de pago", styles["h2"]))
    if evidence is None:
        story.append(
            Paragraph(
                "Sin evidencia adjunta (no requerida para este método de pago).",
                styles["body"],
            )
        )
    else:
        digest = (evidence.content_hash or "").upper()
        short = f"{digest[:8]}...{digest[-4:]}" if digest else "no registrado"
        story.append(
            Paragraph(
                f"Evidencia adjunta: {evidence.original_filename} - "
                f"{round(evidence.size_bytes / 1024)} KB · SHA-256 {short}",
                styles["body"],
            )
        )
        thumb = _evidence_image(evidence, max_width=6 * cm, max_height=4.5 * cm)
        if thumb is not None:
            story.append(Spacer(1, 4))
            story.append(thumb)

    # -- Firmas -------------------------------------------------
    story.append(Spacer(1, 14))
    sign_cells = []
    for label, name in [
        ("Preparado por", prepared_by),
        ("Aprobado por", approved_by or "Pendiente de aprobación"),
        ("Recibí conforme", beneficiary),
    ]:
        sign_cells.append(
            [
                Paragraph("<br/><br/>_____________________________", styles["small"]),
                Paragraph(label, styles["label"]),
                Paragraph(name, styles["value"]),
            ]
        )
    sign_table = Table([sign_cells], colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
    sign_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(KeepTogether(sign_table))

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            f"Aprobación: {approved_by or 'PENDIENTE'} · emitido "
            f"{issued_on.strftime('%d/%m/%Y')} · código de verificación {verification_code}. "
            f"Verificable en {verify_url}",
            styles["small"],
        )
    )

    # -- Página 2: evidencia a tamaño completo -----------------
    full_image = (
        _evidence_image(evidence, max_width=17 * cm, max_height=20 * cm)
        if evidence is not None
        else None
    )
    if full_image is not None:
        story.append(PageBreak())
        story.append(Paragraph("Evidencia de pago", styles["h2"]))
        digest = (evidence.content_hash or "").upper()
        story.append(
            _kv_table(
                [
                    ("Comprobante", document.document_number),
                    ("Beneficiario", beneficiary),
                    ("Banco", bank_label or "—"),
                    ("Fecha", issued_on.strftime("%d/%m/%Y")),
                    ("Archivo", evidence.original_filename),
                    ("SHA-256", digest or "no registrado"),
                ],
                styles,
            )
        )
        story.append(Spacer(1, 8))
        story.append(full_image)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Comprobante {document.document_number}",
    )
    # Sin compresión de página: un comprobante es un artefacto de auditoría y
    # su texto debe poder inspeccionarse/extraerse sin herramientas externas.
    doc.pageCompression = 0
    doc.build(story)
    return buffer.getvalue()
