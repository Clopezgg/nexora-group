import io
import uuid

from PIL import Image as PILImage
from sqlalchemy import select

from app.models.evidence import Evidence
from app.models.user import User
from app.models.voucher_issuance import VoucherIssuance
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_account, create_company, create_treasury_account, login_admin


def _png() -> bytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", (40, 20), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _evidence(db, *, company_id, uploaded_by, suffix: str) -> Evidence:
    row = Evidence(
        company_id=uuid.UUID(str(company_id)),
        blob_key=f"branding/{suffix}.png",
        original_filename=f"{suffix}.png",
        mime_type="image/png",
        size_bytes=len(_png()),
        category="COMPANY_BRANDING",
        uploaded_by=uploaded_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _outflow(client, company_id: str) -> str:
    cash_gl = create_account(client, company_id=company_id, code="1110", name="Caja branding", account_type="ASSET")
    equity = create_account(client, company_id=company_id, code="3100", name="Aportes branding", account_type="EQUITY")
    expense = create_account(client, company_id=company_id, code="5200", name="Gasto branding", account_type="EXPENSE")
    cash = create_treasury_account(client, company_id=company_id, gl_account_id=cash_gl["id"], name="Caja Branding", kind="CASH")
    funding = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company_id,
            "treasuryAccountId": cash["id"],
            "counterAccountId": equity["id"],
            "sender": "Fondeo",
            "currencyCode": "HNL",
            "originalAmount": "1000.00",
            "remittanceDate": "2026-01-01",
        },
    )
    assert funding.status_code == 201, funding.text
    outflow = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company_id,
            "treasuryAccountId": cash["id"],
            "expenseAccountId": expense["id"],
            "category": "Branding QA",
            "amount": "100.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-01-02",
            "description": "Pago para comprobar identidad documental",
        },
    )
    assert outflow.status_code == 201, outflow.text
    return outflow.json()["accountingDocumentId"]


def test_company_branding_rejects_cross_company_evidence(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Brand A")
    company_b = create_company(client, name="Brand B")
    admin = db_session.execute(select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)).scalar_one()
    foreign_logo = _evidence(db_session, company_id=company_b["id"], uploaded_by=admin.id, suffix="foreign-logo")

    response = client.patch(
        f"/api/master-data/companies/{company_a['id']}/profile",
        json={"logoEvidenceId": str(foreign_logo.id)},
    )
    assert response.status_code == 422, response.text


def test_voucher_freezes_and_renders_company_logo_and_signature(client, db_session, monkeypatch):
    """Branding is verified independently from payment-method evidence rules.

    Transfer/deposit/cheque evidence is covered by treasury tests; using cash
    here keeps this regression focused on immutable logo/signature snapshots.
    """
    login_admin(client)
    company = create_company(client, name="Brand Snapshot Co")
    admin = db_session.execute(select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)).scalar_one()
    logo_v1 = _evidence(db_session, company_id=company["id"], uploaded_by=admin.id, suffix="logo-v1")
    signature_v1 = _evidence(db_session, company_id=company["id"], uploaded_by=admin.id, suffix="signature-v1")
    logo_v2 = _evidence(db_session, company_id=company["id"], uploaded_by=admin.id, suffix="logo-v2")

    profile = client.patch(
        f"/api/master-data/companies/{company['id']}/profile",
        json={"logoEvidenceId": str(logo_v1.id), "signatureEvidenceId": str(signature_v1.id)},
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["logoEvidenceId"] == str(logo_v1.id)
    assert profile.json()["signatureEvidenceId"] == str(signature_v1.id)

    document_id = _outflow(client, company["id"])
    requested: list[uuid.UUID] = []

    def _download(evidence):
        requested.append(evidence.id)
        return [_png()]

    monkeypatch.setattr("app.services.voucher_service.evidence_service.download_render", _download)
    pdf = client.get(
        f"/api/treasury/vouchers/{document_id}?beneficiary=Proveedor%20Brand&paymentMethod=Efectivo"
    )
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")
    assert logo_v1.id in requested
    assert signature_v1.id in requested

    issuance = db_session.execute(
        select(VoucherIssuance).where(VoucherIssuance.accounting_document_id == uuid.UUID(document_id))
    ).scalar_one()
    assert issuance.company_logo_evidence_id_snapshot == logo_v1.id
    assert issuance.company_signature_evidence_id_snapshot == signature_v1.id

    updated = client.patch(
        f"/api/master-data/companies/{company['id']}/profile",
        json={"logoEvidenceId": str(logo_v2.id)},
    )
    assert updated.status_code == 200, updated.text

    requested.clear()
    reprint = client.get(
        f"/api/treasury/vouchers/{document_id}?beneficiary=Proveedor%20Brand&paymentMethod=Efectivo"
    )
    assert reprint.status_code == 200, reprint.text
    assert logo_v1.id in requested
    assert logo_v2.id not in requested
