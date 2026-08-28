import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models.company import Company
from app.models.currency import Currency
from app.models.project import Project
from app.models.supplier import Supplier, SupplierContract
from app.pre_migration_repairs import run_authorized_project_reset_preflight


def _seed_target_with_nullable_contract(db_session):
    db_session.add(Currency(code="HNL", name="Lempira", symbol="L"))
    company = Company(name="NEXORA GROUP", code="NX")
    db_session.add(company)
    db_session.flush()
    project = Project(company_id=company.id, code="21000", name="Cerco Perimetral", status="CANCELLED")
    supplier = Supplier(company_id=company.id, legal_name="Proveedor de prueba")
    db_session.add_all([project, supplier])
    db_session.flush()
    contract = SupplierContract(
        company_id=company.id,
        supplier_id=supplier.id,
        project_id=project.id,
        contract_number="TEST-RESET-001",
        value=Decimal("100.00"),
        currency_code="HNL",
        start_date=date(2026, 1, 1),
        status="DRAFT",
    )
    db_session.add(contract)
    db_session.execute(text("CREATE TABLE alembic_version (version_num varchar(32) NOT NULL)"))
    db_session.execute(text("INSERT INTO alembic_version(version_num) VALUES ('9c6d4b2a1e70')"))
    db_session.commit()
    return project.id, contract.id


def test_preflight_detaches_nullable_reference_and_records_audit(db_session):
    project_id, contract_id = _seed_target_with_nullable_contract(db_session)

    run_authorized_project_reset_preflight()

    db_session.expire_all()
    contract = db_session.get(SupplierContract, contract_id)
    assert contract is not None
    assert contract.project_id is None
    assert db_session.get(Project, project_id) is not None  # Alembic owns the deletion itself.

    row = db_session.execute(
        text(
            "SELECT action, entity_id, project_id, after->>'deletedByAuthorizedReset' "
            "FROM audit_logs WHERE entity_id=:project_id"
        ),
        {"project_id": project_id},
    ).one()
    assert row[0] == "project.reset.authorized"
    assert row[1] == project_id
    assert row[2] is None
    assert row[3] == "true"


def test_preflight_aborts_if_a_mandatory_reference_exists(db_session):
    project_id, contract_id = _seed_target_with_nullable_contract(db_session)
    db_session.execute(
        text(
            "CREATE TABLE project_reset_blocker ("
            "id uuid PRIMARY KEY, "
            "project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT)"
        )
    )
    db_session.execute(
        text("INSERT INTO project_reset_blocker(id, project_id) VALUES (:id, :project_id)"),
        {"id": uuid.uuid4(), "project_id": project_id},
    )
    db_session.commit()

    with pytest.raises(RuntimeError, match="mandatory references"):
        run_authorized_project_reset_preflight()

    db_session.expire_all()
    contract = db_session.get(SupplierContract, contract_id)
    assert contract is not None
    assert contract.project_id == project_id
