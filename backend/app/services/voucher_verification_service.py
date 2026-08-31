"""Verificación pública de comprobantes (orden maestra correctiva §39-§42).

El PDF incluye un QR que codifica `<PUBLIC_BASE>/verificar/comprobante/<token>`.
`token` es aleatorio opaco (secrets), persistido por AccountingDocument. El
endpoint público resuelve el token a un conjunto MÍNIMO de datos —
nunca cuenta bancaria completa, evidencia, IDs técnicos, blob keys ni secretos.
"""

import secrets
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.voucher_verification import VoucherVerification


def get_or_create_token(
    db: Session,
    *,
    accounting_document_id: uuid.UUID,
    document_number: str,
    company_name: str,
    beneficiary: str,
    approved_by: str | None,
    issued_on: date,
    amount: Decimal,
    currency_code: str,
    document_status: str,
    verification_code: str,
) -> str:
    row = db.execute(
        select(VoucherVerification).where(
            VoucherVerification.accounting_document_id == accounting_document_id
        )
    ).scalar_one_or_none()

    if row is None:
        row = VoucherVerification(
            accounting_document_id=accounting_document_id,
            token=secrets.token_urlsafe(24),
            document_number=document_number,
            company_name=company_name,
            beneficiary=beneficiary,
            approved_by=approved_by,
            issued_on=issued_on,
            amount=amount,
            currency_code=currency_code,
            document_status=document_status,
            verification_code=verification_code,
        )
        db.add(row)
        db.flush()
    else:
        # Mantener el snapshot al día si el comprobante se regenera (p. ej.
        # cambió el aprobador configurado). El token no cambia.
        row.document_number = document_number
        row.company_name = company_name
        row.beneficiary = beneficiary
        row.approved_by = approved_by
        row.issued_on = issued_on
        row.amount = amount
        row.currency_code = currency_code
        row.document_status = document_status
        row.verification_code = verification_code
        db.flush()

    return row.token


def verify(db: Session, *, token: str) -> dict | None:
    row = db.execute(
        select(VoucherVerification).where(VoucherVerification.token == token)
    ).scalar_one_or_none()
    if row is None:
        return None
    return {
        "verified": True,
        "documentNumber": row.document_number,
        "company": row.company_name,
        "beneficiary": row.beneficiary,
        "issuedOn": row.issued_on.isoformat(),
        "amount": str(row.amount),
        "currency": row.currency_code,
        "status": row.document_status,
        "verificationCode": row.verification_code,
    }
