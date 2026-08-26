import logging

from app.core.logging import _JsonFormatter, get_correlation_id, set_correlation_id
from tests.helpers import login_admin, login_as


def test_correlation_id_is_echoed_back_in_response_header(client):
    response = client.get("/api/auth/me")
    assert "x-correlation-id" in response.headers
    assert response.headers["x-correlation-id"]


def test_client_supplied_correlation_id_is_reused_not_replaced(client):
    """NXR-REQ-0108: distributed tracing -- if the caller already has a
    correlation id (e.g. a gateway/another service), the backend reuses
    it instead of minting a new, disconnected one."""
    response = client.get("/api/auth/me", headers={"X-Correlation-Id": "test-trace-12345"})
    assert response.headers["x-correlation-id"] == "test-trace-12345"


def test_error_response_correlation_id_matches_the_response_header(client, db_session):
    """Before this fix, error_handlers.py minted its own random
    uuid.uuid4() for the error body's correlationId, disconnected from
    whatever the response header / logs used for the same request. Now
    both come from the same request-scoped source."""
    from app.models.permission import UserCompanyAccess
    from tests.helpers import create_company, create_user_with_role

    login_admin(client)
    company_a = create_company(client, name="Correlation A")
    company_b = create_company(client, name="Correlation B")
    user = create_user_with_role(db_session, email="corr-user@nexora.group", role_name="Finance Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="corr-user@nexora.group")

    response = client.get(
        f"/api/reports/trial-balance?companyId={company_a['id']}",
        headers={"X-Correlation-Id": "test-trace-error-1"},
    )
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["error"]["correlationId"] == "test-trace-error-1"
    assert response.headers["x-correlation-id"] == "test-trace-error-1"


def test_csrf_rejection_correlation_id_matches_the_response_header(client):
    response = client.post(
        "/api/master-data/companies",
        json={"name": "x"},
        headers={"Origin": "https://attacker.example", "X-Correlation-Id": "test-trace-csrf-1"},
    )
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["error"]["code"] == "NXR-AUTH-001"
    assert body["error"]["correlationId"] == "test-trace-csrf-1"


def test_audit_log_persists_the_same_correlation_id_as_the_request(client, db_session):
    """The 5 routes that already accepted Depends(get_correlation_id) for
    audit logging now get it from the same shared source as the response
    header and any error body, instead of independently re-parsing the
    header (which could previously disagree if a route's own Depends()
    call minted a fresh random uuid when the client sent none)."""
    from sqlalchemy import select

    from app.models.audit import AuditLog
    from tests.helpers import create_account, create_company, create_treasury_account

    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])

    response = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"], "counterAccountId": contributions["id"],
            "sender": "Socio", "currencyCode": "HNL", "originalAmount": "500.00", "remittanceDate": "2026-01-01",
        },
        headers={"X-Correlation-Id": "test-trace-audit-1"},
    )
    assert response.status_code == 201, response.text
    assert response.headers["x-correlation-id"] == "test-trace-audit-1"

    log = db_session.execute(
        select(AuditLog).where(AuditLog.action == "treasury.remittance.create")
    ).scalars().one()
    assert log.correlation_id == "test-trace-audit-1"


def test_json_formatter_includes_correlation_id_and_message():
    set_correlation_id("format-test-id")
    record = logging.LogRecord(
        name="app.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    record.correlation_id = get_correlation_id()
    formatted = _JsonFormatter().format(record)
    assert '"correlationId": "format-test-id"' in formatted
    assert '"message": "hello world"' in formatted
