import pytest
from sqlalchemy.exc import IntegrityError

from app.models.treasury import TreasuryAccount
from tests.helpers import create_account, create_company, create_treasury_account, login_admin


def _setup(client):
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET"
    )
    cash_gl = create_account(
        client, company_id=company["id"], code="1110", name="Caja", account_type="ASSET"
    )
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes de socios", account_type="EQUITY"
    )
    expense = create_account(
        client, company_id=company["id"], code="5100", name="Gastos administrativos", account_type="EXPENSE"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    cash = create_treasury_account(
        client, company_id=company["id"], gl_account_id=cash_gl["id"], name="Caja Central", kind="CASH"
    )
    return company, bank, cash, contributions, expense



def test_treasury_account_rejects_grouping_gl_account(client):
    login_admin(client)
    company = create_company(client)
    grouping = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "1000",
            "name": "ACTIVOS",
            "accountType": "ASSET",
            "isPostable": False,
        },
    )
    assert grouping.status_code == 201, grouping.text

    response = client.post(
        "/api/treasury/accounts",
        json={
            "companyId": company["id"],
            "name": "Cuenta inválida",
            "kind": "BANK",
            "currencyCode": "HNL",
            "glAccountId": grouping.json()["id"],
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_treasury_account_rejects_non_asset_gl_account(client):
    login_admin(client)
    company = create_company(client)
    expense = create_account(
        client,
        company_id=company["id"],
        code="6101",
        name="Gastos administrativos generales",
        account_type="EXPENSE",
    )

    response = client.post(
        "/api/treasury/accounts",
        json={
            "companyId": company["id"],
            "name": "Cuenta inválida",
            "kind": "OTHER",
            "currencyCode": "HNL",
            "glAccountId": expense["id"],
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"

def test_remittance_rejects_counter_account_equal_to_treasury_gl_account(client):
    """Un remesa cuya cuenta contrapartida es la misma cuenta GL de la
    cuenta de tesorería anularía el movimiento neto (debit y credit al
    mismo account_id se cancelan) mientras el documento sigue "balanceado"
    -- INV-TRE bug real encontrado vía Critical Journey E2E."""
    login_admin(client)
    company, bank, _cash, _contributions, _expense = _setup(client)

    response = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": bank["glAccountId"],
            "sender": "Constructora Matriz",
            "currencyCode": "HNL",
            "originalAmount": "50000.00",
            "remittanceDate": "2026-01-15",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_general_expense_rejects_expense_account_equal_to_treasury_gl_account(client):
    login_admin(client)
    company, bank, _cash, _contributions, _expense = _setup(client)

    response = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "expenseAccountId": bank["glAccountId"],
            "category": "papeleria",
            "amount": "150.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-01-16",
            "description": "Papelería administrativa",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_remittance_is_always_central_scope_and_increases_treasury_balance(client):
    """Orden maestra §27 / INV-OPS-001."""
    login_admin(client)
    company, bank, _cash, contributions, _expense = _setup(client)

    response = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Constructora Matriz",
            "currencyCode": "HNL",
            "originalAmount": "50000.00",
            "remittanceDate": "2026-01-15",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["accountingDocumentId"]

    updated = client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
    bank_account = next(a for a in updated if a["id"] == bank["id"])
    assert float(bank_account["balance"]) == 50000.0


def test_general_expense_never_carries_project_id(client):
    """Orden maestra §28: scope=GENERAL, project_id=NULL, no consume budget."""
    login_admin(client)
    company, bank, _cash, contributions, expense = _setup(client)

    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "originType": "CAPITAL_CONTRIBUTION",
            "sender": "Aporte inicial",
            "currencyCode": "HNL",
            "originalAmount": "10000.00",
            "remittanceDate": "2026-01-01",
        },
    )

    response = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "expenseAccountId": expense["id"],
            "category": "papeleria",
            "amount": "150.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-01-16",
            "description": "Papelería administrativa",
        },
    )
    assert response.status_code == 201, response.text

    document = client.get(
        f"/api/accounting/journal-entries/{response.json()['accountingDocumentId']}"
    ).json()
    assert document["scope"] == "GENERAL"
    assert document["projectId"] is None

    updated = client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
    bank_account = next(a for a in updated if a["id"] == bank["id"])
    assert float(bank_account["balance"]) == 9850.0


def test_transfer_moves_balance_between_treasury_accounts_without_revenue_or_expense(client):
    """Orden maestra §30."""
    login_admin(client)
    company, bank, cash, contributions, _expense = _setup(client)
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Aporte",
            "currencyCode": "HNL",
            "originalAmount": "5000.00",
            "remittanceDate": "2026-01-01",
        },
    )

    response = client.post(
        "/api/treasury/transfers",
        json={
            "companyId": company["id"],
            "sourceTreasuryAccountId": bank["id"],
            "destinationTreasuryAccountId": cash["id"],
            "amount": "1000.00",
            "currencyCode": "HNL",
            "transferDate": "2026-01-05",
        },
    )
    assert response.status_code == 201, response.text

    accounts = {
        a["id"]: a for a in client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
    }
    assert float(accounts[bank["id"]]["balance"]) == 4000.0
    assert float(accounts[cash["id"]]["balance"]) == 1000.0


def test_transfer_to_same_account_is_rejected(client):
    login_admin(client)
    company, bank, _cash, _contributions, _expense = _setup(client)

    response = client.post(
        "/api/treasury/transfers",
        json={
            "companyId": company["id"],
            "sourceTreasuryAccountId": bank["id"],
            "destinationTreasuryAccountId": bank["id"],
            "amount": "100.00",
            "currencyCode": "HNL",
            "transferDate": "2026-01-05",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-TREASURY-001"


def test_remittance_idempotency_key_replay_does_not_duplicate(client):
    """INV-IDEM-001: misma key + mismo payload -> mismo resultado, sin
    duplicar el movimiento de tesorería."""
    login_admin(client)
    company, bank, _cash, contributions, _expense = _setup(client)
    payload = {
        "companyId": company["id"],
        "treasuryAccountId": bank["id"],
        "counterAccountId": contributions["id"],
        "sender": "Aporte idempotente",
        "currencyCode": "HNL",
        "originalAmount": "2000.00",
        "remittanceDate": "2026-01-10",
    }

    first = client.post(
        "/api/treasury/remittances", json=payload, headers={"Idempotency-Key": "rem-key-1"}
    )
    second = client.post(
        "/api/treasury/remittances", json=payload, headers={"Idempotency-Key": "rem-key-1"}
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    accounts = {
        a["id"]: a for a in client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
    }
    assert float(accounts[bank["id"]]["balance"]) == 2000.0


def test_remittance_idempotency_key_conflict_on_different_payload(client):
    """INV-IDEM-002."""
    login_admin(client)
    company, bank, _cash, contributions, _expense = _setup(client)
    base_payload = {
        "companyId": company["id"],
        "treasuryAccountId": bank["id"],
        "counterAccountId": contributions["id"],
        "sender": "Aporte A",
        "currencyCode": "HNL",
        "originalAmount": "500.00",
        "remittanceDate": "2026-01-10",
    }

    first = client.post(
        "/api/treasury/remittances", json=base_payload, headers={"Idempotency-Key": "rem-key-2"}
    )
    assert first.status_code == 201, first.text

    conflicting_payload = dict(base_payload, originalAmount="999.00")
    second = client.post(
        "/api/treasury/remittances",
        json=conflicting_payload,
        headers={"Idempotency-Key": "rem-key-2"},
    )
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "NXR-IDEMPOTENCY-001"


def test_treasury_account_gl_account_must_belong_to_owning_company(client):
    login_admin(client)
    company_a = create_company(client, name="Compañía A")
    company_b = create_company(client, name="Compañía B")
    foreign_gl = create_account(
        client,
        company_id=company_b["id"],
        code="1100",
        name="Banco B",
        account_type="ASSET",
    )

    response = client.post(
        "/api/treasury/accounts",
        json={
            "companyId": company_a["id"],
            "name": "Cuenta inválida",
            "kind": "BANK",
            "currencyCode": "HNL",
            "glAccountId": foreign_gl["id"],
        },
    )

    assert response.status_code == 422, response.text


def test_zero_and_negative_treasury_movements_are_rejected(client):
    login_admin(client)
    company, bank, _cash, contributions, _expense = _setup(client)
    for index, amount in enumerate(("0", "-1"), start=1):
        response = client.post(
            "/api/treasury/remittances",
            json={
                "companyId": company["id"],
                "treasuryAccountId": bank["id"],
                "counterAccountId": contributions["id"],
                "sender": f"Inválido {index}",
                "currencyCode": "HNL",
                "originalAmount": amount,
                "remittanceDate": "2026-01-15",
            },
        )
        assert response.status_code == 422, response.text


def test_two_companies_can_use_their_own_document_number_sequence(client):
    login_admin(client)
    company_a, bank_a, _cash_a, counter_a, _expense_a = _setup(client)
    company_b, bank_b, _cash_b, counter_b, _expense_b = _setup(client)

    first = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company_a["id"],
            "treasuryAccountId": bank_a["id"],
            "counterAccountId": counter_a["id"],
            "sender": "Aporte A",
            "currencyCode": "HNL",
            "originalAmount": "10.00",
            "remittanceDate": "2026-01-01",
        },
    )
    second = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company_b["id"],
            "treasuryAccountId": bank_b["id"],
            "counterAccountId": counter_b["id"],
            "sender": "Aporte B",
            "currencyCode": "HNL",
            "originalAmount": "10.00",
            "remittanceDate": "2026-01-01",
        },
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text


def test_treasury_account_rejects_duplicate_gl_mapping_at_api(client):
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(
        client,
        company_id=company["id"],
        code="1100",
        name="Single Treasury GL",
        account_type="ASSET",
    )
    create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"]
    )

    duplicate = client.post(
        "/api/treasury/accounts",
        json={
            "companyId": company["id"],
            "name": "Duplicate balance view",
            "kind": "BANK",
            "currencyCode": "HNL",
            "glAccountId": bank_gl["id"],
        },
    )

    assert duplicate.status_code == 422, duplicate.text
    assert duplicate.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_database_rejects_duplicate_treasury_gl_mapping(client, db_session):
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(
        client,
        company_id=company["id"],
        code="1100",
        name="Unique Treasury GL",
        account_type="ASSET",
    )
    create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"]
    )
    db_session.add(
        TreasuryAccount(
            company_id=company["id"],
            name="Direct duplicate",
            kind="CASH",
            currency_code="HNL",
            gl_account_id=bank_gl["id"],
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_remittances_can_be_listed_for_their_company(client):
    login_admin(client)
    company, bank, _cash, contributions, _expense = _setup(client)
    created = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Cliente real",
            "provider": "Banco",
            "channel": "TRANSFER",
            "reference": "REM-TEST-001",
            "currencyCode": "HNL",
            "originalAmount": "1250.00",
            "remittanceDate": "2026-08-27",
        },
    )
    assert created.status_code == 201, created.text

    response = client.get(f"/api/treasury/remittances?companyId={company['id']}")
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["reference"] == "REM-TEST-001"
    assert response.json()[0]["sender"] == "Cliente real"
