from app.models.project import Project
from tests.helpers import create_account, create_company, login_admin


def test_central_operation_never_mutates_active_ui_context(client, db_session):
    """INV-CTX-001: una operación con scope=CENTRAL/GENERAL (project_id=None)
    nunca debe tocar el ActiveUIContext del usuario -- son conceptos
    independientes (CLAUDE.md §7)."""
    login_admin(client)
    company = create_company(client)
    project = Project(company_id=company["id"], name="Torre Nexora II", status="ACTIVE")
    db_session.add(project)
    db_session.commit()

    set_context = client.put("/api/context", json={"activeProjectId": str(project.id)})
    assert set_context.status_code == 200
    assert set_context.json()["activeProjectId"] == str(project.id)

    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY"
    )

    posted = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "CENTRAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "500.00"},
                {"accountId": credit_account["id"], "creditAmount": "500.00"},
            ],
        },
    )
    assert posted.status_code == 201, posted.text
    assert posted.json()["scope"] == "CENTRAL"
    assert posted.json()["projectId"] is None

    context_after = client.get("/api/context")
    assert context_after.status_code == 200
    assert context_after.json()["activeProjectId"] == str(project.id)
