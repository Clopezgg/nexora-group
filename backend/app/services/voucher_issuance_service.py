"""Emisión inmutable de comprobantes (orden maestra final §27/§28).

`get_or_create` congela, en la PRIMERA emisión de un AccountingDocument, todo
lo que se imprime. Reemisiones posteriores leen de este snapshot — si cambia
la dirección de NEXORA, el aprobador, el nombre comercial, etc., el
comprobante de agosto sigue mostrando los datos de agosto.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.voucher_issuance import VoucherIssuance


def _join(*parts) -> str | None:
    joined = " · ".join(str(p).strip() for p in parts if p and str(p).strip())
    return joined or None


def get_or_create(
    db: Session,
    *,
    accounting_document_id: uuid.UUID,
    company,
    project,
    document_number: str,
    issued_on: date,
    beneficiary_name: str,
    beneficiary_address: str | None,
    beneficiary_tax_id: str | None,
    payer_name: str,
    approver_name: str | None,
    payment_method: str,
    bank_name: str | None,
    bank_account_mask: str | None,
    bank_transaction_reference: str | None,
    payment_observations: str | None,
    amount: Decimal,
    currency_code: str,
    contract_number: str | None,
    contract_period: str | None,
    contract_value: Decimal | None,
    paid_before: Decimal | None,
    paid_accumulated: Decimal | None,
    contract_balance: Decimal | None,
    verification_token: str,
    verification_code: str,
) -> VoucherIssuance:
    existing = db.execute(
        select(VoucherIssuance).where(
            VoucherIssuance.accounting_document_id == accounting_document_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    issuance = VoucherIssuance(
        company_id=company.id,
        accounting_document_id=accounting_document_id,
        document_number=document_number,
        issued_at=datetime.now(timezone.utc),
        issued_on=issued_on,
        company_name_snapshot=company.name,
        company_legal_name_snapshot=getattr(company, "legal_name", None),
        company_trade_name_snapshot=getattr(company, "trade_name", None),
        company_fiscal_id_snapshot=getattr(company, "fiscal_id", None),
        company_address_snapshot=_join(
            getattr(company, "address_line_1", None),
            getattr(company, "address_line_2", None),
            getattr(company, "city", None),
            getattr(company, "state_department", None),
        ),
        company_phone_snapshot=getattr(company, "phone", None),
        company_email_snapshot=getattr(company, "email", None),
        company_footer_snapshot=getattr(company, "voucher_footer_text", None),
        project_name_snapshot=project.name if project else None,
        project_address_snapshot=_join(
            getattr(project, "address_line_1", None) if project else None,
            getattr(project, "city", None) if project else None,
            getattr(project, "state_department", None) if project else None,
            getattr(project, "location_reference", None) if project else None,
        ),
        contract_number_snapshot=contract_number,
        contract_period_snapshot=contract_period,
        beneficiary_name_snapshot=beneficiary_name,
        beneficiary_address_snapshot=beneficiary_address,
        beneficiary_tax_id_snapshot=beneficiary_tax_id,
        payer_name_snapshot=payer_name,
        approver_name_snapshot=approver_name,
        payment_method_snapshot=payment_method,
        bank_name_snapshot=bank_name,
        bank_account_mask_snapshot=bank_account_mask,
        bank_transaction_reference_snapshot=bank_transaction_reference,
        payment_observations_snapshot=payment_observations,
        amount_snapshot=amount,
        currency_code_snapshot=currency_code,
        contract_value_snapshot=contract_value,
        paid_before_snapshot=paid_before,
        paid_accumulated_snapshot=paid_accumulated,
        contract_balance_snapshot=contract_balance,
        verification_token=verification_token,
        verification_code=verification_code,
        status="ISSUED",
    )
    db.add(issuance)
    db.flush()
    return issuance
