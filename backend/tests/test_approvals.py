import uuid

import pytest
from sqlalchemy import select

from app.domain.errors import (
    InvalidApprovalDecisionError,
    InvalidApprovalStateError,
    SegregationOfDutiesError,
)
from app.models.approval_policy import ApprovalPolicy
from app.models.permission import UserCompanyAccess
from app.models.user import User
from app.services import approval_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _get_admin_user(db_session) -> User:
    return db_session.execute(select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)).scalar_one()


def test_approval_policy_has_entity_type_and_requires_third_role(client, db_session):
    login_admin(client)
    company = create_company(client)

    policy = ApprovalPolicy(
        company_id=uuid.UUID(company["id"]),
        name="AP Payment Approval",
        entity_type="ap.supplier_payment",
        requires_third_role=True,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    assert policy.entity_type == "ap.supplier_payment"
    assert policy.requires_third_role is True


def test_requester_cannot_decide_their_own_approval_request(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    with pytest.raises(SegregationOfDutiesError):
        approval_service.decide(
            db_session,
            request_id=request.id,
            decided_by=admin_user.id,
            decision="APPROVED",
        )


def test_deciding_an_already_decided_request_is_rejected(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)

    approver = create_user_with_role(
        db_session, email="approver-g1@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    approval_service.decide(
        db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
    )
    db_session.commit()

    with pytest.raises(InvalidApprovalStateError):
        approval_service.decide(
            db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
        )


def test_third_role_required_rejects_executor_matching_requester_or_approver(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)

    approver = create_user_with_role(
        db_session, email="approver-g2@nexora.group", role_name="Finance Manager"
    )
    executor = create_user_with_role(
        db_session, email="executor-g2@nexora.group", role_name="Finance Manager"
    )
    db_session.commit()

    policy = ApprovalPolicy(
        company_id=uuid.UUID(company["id"]),
        name="Three-role payment policy",
        entity_type="test.entity",
        requires_third_role=True,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    request = approval_service.create_request(
        db_session,
        policy_id=policy.id,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    with pytest.raises(SegregationOfDutiesError):
        approval_service.decide(
            db_session,
            request_id=request.id,
            decided_by=approver.id,
            decision="APPROVED",
            executed_by=admin_user.id,
        )

    request2 = approval_service.create_request(
        db_session,
        policy_id=policy.id,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    result = approval_service.decide(
        db_session,
        request_id=request2.id,
        decided_by=approver.id,
        decision="APPROVED",
        executed_by=executor.id,
    )
    assert result.status == "APPROVED"


def test_deciding_ap_approval_request_transitions_the_real_invoice(client, db_session):
    from app.models.ap import SupplierInvoice
    from tests.test_ap_ar import _setup_ap  # reuse the existing fixture-builder

    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    admin_user = _get_admin_user(db_session)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-APR-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    approver = create_user_with_role(
        db_session, email="approver-g3@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="ap.supplier_invoice",
        entity_id=uuid.UUID(invoice["id"]),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="ap",
    )
    db_session.commit()

    approval_service.decide(
        db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
    )
    db_session.commit()

    refreshed = db_session.get(SupplierInvoice, uuid.UUID(invoice["id"]))
    assert refreshed.status == "APPROVED"


def test_company_access_blocks_cross_company_approval_list(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Aprobaciones A")
    company_b = create_company(client, name="Aprobaciones B")

    # Same reasoning as test_audit.py::test_company_access_blocks_cross_company_audit_log:
    # Auditor is SCOPE_ANY for workflow.approval/read by house convention, so
    # it cannot exercise company isolation meaningfully. Finance Manager is
    # genuinely SCOPE_OWN.
    user = create_user_with_role(
        db_session, email="finance-approvals-b@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=uuid.UUID(company_b["id"])))
    db_session.commit()
    login_as(client, email="finance-approvals-b@nexora.group")

    response = client.get(f"/api/approvals?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_read_only_role_cannot_decide_approval(client, db_session):
    login_admin(client)
    company = create_company(client)

    # Auditor is granted workflow.approval/read but deliberately not
    # workflow.approval/decide (see permission_repository.py) -- Auditors
    # observe, they never decide.
    user = create_user_with_role(
        db_session, email="auditor-approvals@nexora.group", role_name="Auditor"
    )
    db_session.commit()
    login_as(client, email="auditor-approvals@nexora.group")

    list_response = client.get(f"/api/approvals?companyId={company['id']}")
    assert list_response.status_code == 200, list_response.text

    decide_response = client.post(
        f"/api/approvals/{uuid.uuid4()}/decide", json={"decision": "APPROVED"}
    )
    assert decide_response.status_code == 403, decide_response.text
    assert decide_response.json()["error"]["code"] == "NXR-PERM-001"


def test_decide_rejects_invalid_decision_value_at_service_layer(client, db_session):
    """approval_service.decide() is also called directly by other code
    (Task 3, tests) -- it must not rely solely on the route's Pydantic
    Literal to reject a garbage decision value."""
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)

    approver = create_user_with_role(
        db_session, email="approver-g4@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    with pytest.raises(InvalidApprovalDecisionError):
        approval_service.decide(
            db_session, request_id=request.id, decided_by=approver.id, decision="WHATEVER"
        )

    # The invalid decision must be rejected BEFORE anything is persisted --
    # the ApprovalRequest.status must still be PENDING, not corrupted with
    # the bogus value.
    from app.repositories import approval_repository

    reloaded = approval_repository.get_for_update(db_session, request_id=request.id)
    assert reloaded.status == "PENDING"


def test_api_rejects_invalid_decision_value_with_clean_4xx(client, db_session):
    """The route-level Literal["APPROVED", "REJECTED"] must turn a garbage
    decision value into a clean 4xx, not a raw 500, and must not desync
    ApprovalRequest.status from the real domain entity it governs."""
    from app.models.ap import SupplierInvoice
    from tests.test_ap_ar import _setup_ap

    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    admin_user = _get_admin_user(db_session)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-APR-2",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    approver = create_user_with_role(
        db_session, email="approver-g5@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="ap.supplier_invoice",
        entity_id=uuid.UUID(invoice["id"]),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="ap",
    )
    db_session.commit()

    login_as(client, email="approver-g5@nexora.group")
    response = client.post(f"/api/approvals/{request.id}/decide", json={"decision": "WHATEVER"})
    assert response.status_code == 422, response.text

    # Neither the ApprovalRequest nor the real SupplierInvoice moved.
    db_session.expire_all()
    from app.repositories import approval_repository

    reloaded_request = approval_repository.get_for_update(db_session, request_id=request.id)
    assert reloaded_request.status == "PENDING"
    reloaded_invoice = db_session.get(SupplierInvoice, uuid.UUID(invoice["id"]))
    assert reloaded_invoice.status == "DRAFT"
