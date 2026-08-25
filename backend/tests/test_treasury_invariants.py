"""INV-TRE-001/002 (docs/ACCOUNTING.md): el dinero real pertenece a
Treasury; un Project nunca posee saldo."""

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.project import Project
from app.models.treasury import Remittance
from app.schemas.ap import SupplierPaymentCreateRequest
from app.schemas.ar import CustomerReceiptCreateRequest
from app.schemas.treasury import TreasuryTransferCreateRequest

from tests.helpers import create_account, create_company, create_treasury_account, login_admin


def test_project_model_has_no_balance_column_or_field():
    """INV-TRE-002: un Project no tiene ningún campo de saldo/efectivo -- la
    única forma de tener dinero real en NEXORA es un TreasuryAccount."""
    project_columns = {column.name for column in Project.__table__.columns}
    forbidden = {"balance", "cash_balance", "amount", "treasury_balance", "funds"}
    assert project_columns.isdisjoint(forbidden), (
        f"Project no debe tener columnas de saldo, encontradas: {project_columns & forbidden}"
    )


def test_only_treasury_accounts_can_hold_real_money_balance(client):
    """INV-TRE-001: el saldo real vive únicamente en TreasuryAccount.balance
    (derivado del GL vía treasury_service.account_balance) -- un Project
    consultado por la misma vía no expone ningún saldo."""
    login_admin(client)
    company = create_company(client)
    gl_account = create_account(
        client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET"
    )
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    treasury_account = create_treasury_account(client, company_id=company["id"], gl_account_id=gl_account["id"])

    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": treasury_account["id"],
            "counterAccountId": contributions["id"],
            "sender": "Aporte",
            "currencyCode": "HNL",
            "originalAmount": "1000.00",
            "remittanceDate": "2026-01-01",
        },
    )

    accounts = client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
    assert float(accounts[0]["balance"]) == 1000.0

    # No existe ningún endpoint de "project balance" -- confirmar que la ruta
    # ni siquiera existe (404), reforzando que Project nunca posee dinero.
    response = client.get("/api/projects/00000000-0000-0000-0000-000000000001/balance")
    assert response.status_code == 404


def test_database_rejects_non_positive_cash_movement(client, db_session):
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Banco", account_type="ASSET"
    )
    counter = create_account(
        client, company_id=company["id"], code="3100", name="Capital", account_type="EQUITY"
    )
    bank = create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"]
    )
    created = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": counter["id"],
            "sender": "Movimiento válido inicial",
            "currencyCode": "HNL",
            "originalAmount": "10.00",
            "remittanceDate": "2026-01-01",
        },
    ).json()
    remittance = db_session.get(Remittance, uuid.UUID(created["id"]))
    remittance.original_amount = Decimal("0")

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (
            TreasuryTransferCreateRequest,
            {
                "companyId": uuid.uuid4(),
                "sourceTreasuryAccountId": uuid.uuid4(),
                "destinationTreasuryAccountId": uuid.uuid4(),
                "amount": "0",
                "currencyCode": "HNL",
                "transferDate": "2026-01-01",
            },
        ),
        (
            SupplierPaymentCreateRequest,
            {
                "treasuryAccountId": uuid.uuid4(),
                "amount": "0",
                "paymentDate": "2026-01-01",
            },
        ),
        (
            CustomerReceiptCreateRequest,
            {
                "treasuryAccountId": uuid.uuid4(),
                "amount": "-1",
                "receiptDate": "2026-01-01",
            },
        ),
    ],
)
def test_cash_movement_schemas_reject_non_positive_amounts(schema, payload):
    with pytest.raises(ValidationError):
        schema.model_validate(payload)
