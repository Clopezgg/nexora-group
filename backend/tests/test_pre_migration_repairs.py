import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models.company import Company
from app.models.currency import Currency
from app.models.equipment import FuelLog
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


def _drop_alembic_version(db_session):
    db_session.execute(text("DROP TABLE IF EXISTS alembic_version"))
    db_session.commit()


def test_preflight_is_a_noop_on_a_fresh_database(db_session):
    """A clean DB (Docker Compose smoke, first bootstrap) has no
    alembic_version table yet; the preflight must return quietly instead of
    crashing before ``alembic upgrade head`` can build the schema."""

    _drop_alembic_version(db_session)

    # Must not raise psycopg.errors.UndefinedTable.
    run_authorized_project_reset_preflight()


def test_preflight_detaches_nullable_reference_and_records_audit(db_session):
    project_id, contract_id = _seed_target_with_nullable_contract(db_session)

    try:
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
    finally:
        _drop_alembic_version(db_session)


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

    try:
        with pytest.raises(RuntimeError, match="mandatory references"):
            run_authorized_project_reset_preflight()

        db_session.expire_all()
        contract = db_session.get(SupplierContract, contract_id)
        assert contract is not None
        assert contract.project_id == project_id
    finally:
        db_session.execute(text("DROP TABLE IF EXISTS project_reset_blocker"))
        _drop_alembic_version(db_session)

def test_preflight_converts_project_scoped_history_to_general(db_session):
    project_id, _contract_id = _seed_target_with_nullable_contract(db_session)
    company_id = db_session.execute(
        text("SELECT company_id FROM projects WHERE id=:project_id"),
        {"project_id": project_id},
    ).scalar_one()
    fuel_log = FuelLog(
        company_id=company_id,
        vehicle_description="Equipo histórico",
        log_date=date(2026, 8, 5),
        quantity=Decimal("5.000"),
        unit_cost=Decimal("102.9500"),
        total_cost=Decimal("514.75"),
        scope="PROJECT",
        project_id=project_id,
    )
    db_session.add(fuel_log)
    db_session.commit()
    fuel_log_id = fuel_log.id

    try:
        run_authorized_project_reset_preflight()

        db_session.expire_all()
        preserved = db_session.get(FuelLog, fuel_log_id)
        assert preserved is not None
        assert preserved.project_id is None
        assert preserved.scope == "GENERAL"
    finally:
        _drop_alembic_version(db_session)
