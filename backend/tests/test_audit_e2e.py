import uuid

from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, login_admin


def test_company_create_emits_audit_entry_via_api(client, db_session):
    """E2E (NXR-REQ-0090): create a company through the real API, then
    query the audit log API and verify the entry exists with correct
    action, entity_type, entity_id, and after snapshot."""
    login_admin(client)
    company = create_company(client, name="Audit E2E Company")

    response = client.get(f"/api/audit?companyId={company['id']}")
    assert response.status_code == 200, response.text
    entries = response.json()
    assert len(entries) >= 1

    entry = entries[-1]
    assert entry["action"] == "core.company.create"
    assert entry["entityType"] == "core.company"
    assert entry["entityId"] == company["id"]
    assert entry["companyId"] == company["id"]
    assert entry["after"] is not None
    assert entry["after"]["name"] == "Audit E2E Company"
    assert entry["before"] is None
    assert entry["correlationId"] is not None


def test_company_update_emits_audit_entry_with_before_snapshot(client, db_session):
    """E2E (NXR-REQ-0090): update a company and verify the audit log
    captures both before and after snapshots."""
    login_admin(client)
    company = create_company(client, name="Before Update Co")

    response = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"legalName": "After Update Co"},
    )
    assert response.status_code == 200, response.text

    response = client.get(f"/api/audit?companyId={company['id']}")
    entries = response.json()
    update_entries = [e for e in entries if e["action"] == "core.company.update"]
    assert len(update_entries) == 1

    entry = update_entries[0]
    assert entry["before"] is not None
    assert entry["after"] is not None
    assert entry["after"]["legalName"] == "After Update Co"


def test_account_create_emits_audit_entry_via_api(client, db_session):
    """E2E (NXR-REQ-0090): create an account through the real API and
    verify the audit log entry via the audit API."""
    login_admin(client)
    company = create_company(client, name="Account Audit Co")

    from tests.helpers import create_account

    account = create_account(
        client,
        company_id=company["id"],
        code="AUD-1001",
        name="Banco Audit",
        account_type="ASSET",
    )

    response = client.get(
        f"/api/audit?companyId={company['id']}&entityType=accounting.account"
    )
    entries = response.json()
    create_entries = [e for e in entries if e["action"] == "accounting.account.create"]
    assert len(create_entries) == 1

    entry = create_entries[0]
    assert entry["entityId"] == account["id"]
    assert entry["after"]["code"] == "AUD-1001"
    assert entry["before"] is None


def test_audit_api_filters_by_entity_type(client, db_session):
    """E2E (NXR-REQ-0090): verify the audit API entity_type filter works
    correctly — only returns entries matching the requested entity type."""
    login_admin(client)
    company = create_company(client, name="Filter Audit Co")

    from tests.helpers import create_account

    create_account(
        client,
        company_id=company["id"],
        code="FILT-2001",
        name="Filtro Cuenta",
        account_type="LIABILITY",
    )

    all_entries = client.get(f"/api/audit?companyId={company['id']}").json()
    company_entries = [
        e for e in all_entries if e["entityType"] == "core.company"
    ]
    account_entries = [
        e for e in all_entries if e["entityType"] == "accounting.account"
    ]

    assert len(company_entries) >= 1
    assert len(account_entries) >= 1

    filtered = client.get(
        f"/api/audit?companyId={company['id']}&entityType=accounting.account"
    ).json()
    assert all(e["entityType"] == "accounting.account" for e in filtered)


def test_audit_entry_records_actor_user_id(client, db_session):
    """E2E (NXR-REQ-0090): verify the audit entry records the real actor
    user ID (the admin who performed the mutation)."""
    from app.models.user import User
    from sqlalchemy import select

    login_admin(client)
    company = create_company(client, name="Actor Audit Co")

    admin = db_session.execute(
        select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
    ).scalar_one()

    entries = client.get(f"/api/audit?companyId={company['id']}").json()
    assert len(entries) >= 1
    assert entries[-1]["actorUserId"] == str(admin.id)


def test_audit_entry_records_correlation_id(client, db_session):
    """E2E (NXR-REQ-0090): verify the audit entry records the correlation
    ID from the request header."""
    login_admin(client)

    response = client.post(
        "/api/master-data/companies",
        json={
            "name": "Correlation Audit Co",
            "functionalCurrencyCode": "HNL",
        },
        headers={"X-Correlation-Id": "e2e-correlation-test-001"},
    )
    assert response.status_code == 201, response.text
    company = response.json()

    entries = client.get(f"/api/audit?companyId={company['id']}").json()
    assert len(entries) >= 1
    assert entries[-1]["correlationId"] == "e2e-correlation-test-001"


def test_audit_rolls_back_on_write_failure(client, db_session, monkeypatch):
    """E2E (NXR-REQ-0090): when audit_service.record raises, the entire
    mutation must roll back — no partial state persists."""
    import pytest

    login_admin(client)

    def fail_record(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        "app.api.routes.master_data.audit_service.record", fail_record
    )

    payload = {
        "name": "Should Rollback Co",
        "functionalCurrencyCode": "HNL",
    }
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post("/api/master-data/companies", json=payload)

    from app.models.company import Company
    from sqlalchemy import select

    db_session.expire_all()
    rows = db_session.execute(
        select(Company).where(Company.name == "Should Rollback Co")
    ).scalars().all()
    assert len(rows) == 0, "Company should not exist after audit failure"
